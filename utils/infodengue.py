"""
Utilitários para consultar a API pública do InfoDengue (Fiocruz).
Documentação: https://info.dengue.mat.br/services/api/doc
"""
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://info.dengue.mat.br/api/alertcity"

# Alguns servidores bloqueiam requisições sem um User-Agent "de navegador".
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PainelArboviroses/1.0; "
        "+https://acompanhamentoarboviroses.streamlit.app)"
    )
}

# Mapeamento do nível de alerta retornado pela API para cor/rótulo em português
NIVEL_ALERTA = {
    1: {"cor": "🟢", "label": "Verde - baixo risco"},
    2: {"cor": "🟡", "label": "Amarelo - risco de epidemia"},
    3: {"cor": "🟠", "label": "Laranja - epidemia em curso"},
    4: {"cor": "🔴", "label": "Vermelho - alerta de epidemia"},
}

# Cor RGBA (formato pydeck) para cada nível de alerta, usada nos mapas
NIVEL_COR_RGBA = {
    1: [34, 139, 34, 160],    # verde
    2: [255, 215, 0, 180],    # amarelo
    3: [255, 140, 0, 190],    # laranja
    4: [220, 20, 60, 210],    # vermelho
    0: [130, 130, 130, 120],  # sem dado / desconhecido
}


@st.cache_data(ttl=60 * 60 * 6)  # cache de 6h, dados semanais não mudam com frequência
def buscar_dados(
    geocode: int,
    doenca: str = "dengue",
    ano_inicio: int = 2022,
    ano_fim: int | None = None,
) -> pd.DataFrame:
    """
    Busca a série histórica semanal de casos para um município.

    Parâmetros:
        geocode: código IBGE do município (7 dígitos)
        doenca: 'dengue' | 'chikungunya' | 'zika'
        ano_inicio: primeiro ano da série
        ano_fim: último ano da série (default: ano atual)
    """
    if ano_fim is None:
        ano_fim = date.today().year

    params = {
        "geocode": geocode,
        "disease": doenca,
        "format": "json",
        "ew_start": 1,
        "ew_end": 52,
        "ey_start": ano_inicio,
        "ey_end": ano_fim,
    }

    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    dados = resp.json()

    if not dados:
        return pd.DataFrame()

    df = pd.DataFrame(dados)

    # A API retorna a coluna de data em milissegundos (epoch) no formato JSON
    if "data_iniSE" in df.columns:
        df["data"] = pd.to_datetime(df["data_iniSE"], unit="ms")
    elif "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], unit="ms")

    df = df.sort_values("data").reset_index(drop=True)
    return df


def nivel_atual(df: pd.DataFrame) -> dict:
    """Retorna o nível de alerta mais recente disponível na série."""
    if df.empty or "nivel" not in df.columns:
        return {"cor": "⚪", "label": "Sem dados disponíveis"}

    ultimo_nivel = int(df.iloc[-1]["nivel"])
    return NIVEL_ALERTA.get(ultimo_nivel, {"cor": "⚪", "label": "Nível desconhecido"})


def _buscar_snapshot_cidade(geocode: int, doenca: str, tentativas: int = 2) -> tuple[dict | None, str | None]:
    """
    Busca apenas o snapshot mais recente (última semana disponível) de uma
    cidade. Usado internamente pela busca em lote para montar o mapa.
    Consulta os últimos ~2 anos para garantir que sempre haja algum dado,
    mesmo perto da virada do ano.

    Retorna (resultado, erro): 'erro' é None em caso de sucesso, ou uma
    string curta descrevendo a falha (usada para diagnóstico agregado).
    """
    ano_atual = date.today().year
    ultimo_erro = None

    for tentativa in range(tentativas):
        try:
            df = buscar_dados(geocode, doenca=doenca, ano_inicio=ano_atual - 1, ano_fim=ano_atual)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            ultimo_erro = f"HTTP {status}"
        except requests.exceptions.Timeout:
            ultimo_erro = "timeout"
        except requests.exceptions.ConnectionError:
            ultimo_erro = "erro de conexão"
        except Exception as e:
            ultimo_erro = type(e).__name__
        else:
            if df.empty or "nivel" not in df.columns:
                return None, "sem_dado"

            casos_col = "casos_est" if "casos_est" in df.columns else "casos"
            ultima = df.iloc[-1]
            return {
                "geocode": geocode,
                "nivel": int(ultima["nivel"]),
                "casos": float(ultima.get(casos_col, 0) or 0),
                "data": ultima["data"],
            }, None

        time.sleep(0.5 * (tentativa + 1))  # pequeno backoff antes de tentar de novo

    return None, ultimo_erro


def buscar_dados_em_lote(
    geocodes: list[int],
    doenca: str = "dengue",
    max_workers: int = 8,
    progresso_callback=None,
) -> tuple[pd.DataFrame, dict]:
    """
    Busca o snapshot mais recente de várias cidades em paralelo (usado no
    mapa por estado). Cidades sem dado disponível ou com erro na consulta
    são omitidas do resultado, mas o motivo é contabilizado no diagnóstico.

    Parâmetros:
        geocodes: lista de códigos IBGE dos municípios
        doenca: 'dengue' | 'chikungunya' | 'zika'
        max_workers: número de requisições simultâneas (mantido moderado
            para evitar bloqueio por limite de requisições da própria API)
        progresso_callback: função opcional chamada a cada cidade processada,
            recebe (concluidos, total) — usada para exibir uma barra de progresso

    Retorna:
        (DataFrame com os dados obtidos, dict com contagem de erros por tipo)
    """
    resultados = []
    erros = Counter()
    total = len(geocodes)
    concluidos = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = {
            executor.submit(_buscar_snapshot_cidade, gc, doenca): gc for gc in geocodes
        }
        for futuro in as_completed(futuros):
            concluidos += 1
            resultado, erro = futuro.result()
            if resultado is not None:
                resultados.append(resultado)
            elif erro:
                erros[erro] += 1
            if progresso_callback:
                progresso_callback(concluidos, total)

    return pd.DataFrame(resultados), dict(erros)
