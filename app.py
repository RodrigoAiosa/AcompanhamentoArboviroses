"""
Painel de Acompanhamento de Arboviroses (Dengue, Zika, Chikungunya)
Fonte dos dados: InfoDengue (Fiocruz) + IBGE (localidades)
"""
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from utils.geolocalizacao import cidades_do_estado, lista_estados
from utils.infodengue import (
    NIVEL_ALERTA,
    NIVEL_COR_RGBA,
    buscar_dados,
    buscar_dados_em_lote,
    nivel_atual,
)

st.set_page_config(
    page_title="Painel de Arboviroses - Brasil",
    page_icon="🦟",
    layout="wide",
)

st.title("🦟 Painel de Acompanhamento de Arboviroses")
st.caption(
    "Dados oficiais do **InfoDengue** (Fiocruz) e **IBGE**. "
    "Acompanhe o risco de dengue, zika e chikungunya no Brasil."
)

tab_cidade, tab_mapa = st.tabs(["🔎 Consulta por Cidade", "🗺️ Mapa por Estado"])

# =============================================================================
# ABA 1 — CONSULTA DETALHADA POR CIDADE (funcionalidade original)
# =============================================================================
with tab_cidade:
    estados_cidade = lista_estados()

    col1, col2, col3 = st.columns([1.3, 1.7, 1])

    with col1:
        estado_consulta = st.selectbox(
            "Estado (UF)",
            options=estados_cidade,
            format_func=lambda e: f"{e['nome']} ({e['uf']})",
            index=None,
            placeholder="Escolha um estado...",
            key="select_estado_cidade",
        )

    with col2:
        if estado_consulta is not None:
            cidades_opcoes = cidades_do_estado(estado_consulta["codigo_uf"]).to_dict("records")
            placeholder_cidade = "Escolha um município..."
        else:
            cidades_opcoes = []
            placeholder_cidade = "Primeiro escolha um estado..."

        municipio_selecionado = st.selectbox(
            "Município",
            options=cidades_opcoes,
            format_func=lambda c: c["nome"],
            index=None,
            placeholder=placeholder_cidade,
            disabled=estado_consulta is None,
            key="select_cidade",
        )

    with col3:
        doenca_cidade = st.selectbox(
            "Doença",
            options=["dengue", "chikungunya", "zika"],
            format_func=lambda d: d.capitalize(),
            key="doenca_cidade",
        )

    anos = st.slider(
        "Período da série histórica (anos)",
        min_value=2015,
        max_value=2026,
        value=(2023, 2026),
        key="slider_anos",
    )

    if estado_consulta is None:
        st.info("👆 Selecione um estado e depois um município para visualizar os dados.")
    elif municipio_selecionado is None:
        st.info("👆 Selecione um município para visualizar os dados.")
    else:
        with st.spinner(f"Buscando dados de {doenca_cidade} para {municipio_selecionado['nome']}..."):
            try:
                df = buscar_dados(
                    geocode=municipio_selecionado["codigo_ibge"],
                    doenca=doenca_cidade,
                    ano_inicio=anos[0],
                    ano_fim=anos[1],
                )
            except Exception as e:
                st.error(f"Erro ao consultar a API do InfoDengue: {e}")
                df = pd.DataFrame()

        if df.empty:
            st.warning(
                "Nenhum dado encontrado para esse município/período. "
                "Tente outro município ou amplie o período."
            )
        else:
            nivel = nivel_atual(df)
            st.subheader(f"{nivel['cor']} Nível de alerta atual: {nivel['label']}")

            ultima_semana = df.iloc[-1]
            casos_col = "casos_est" if "casos_est" in df.columns else "casos"

            m1, m2, m3 = st.columns(3)
            m1.metric(
                "Última semana epidemiológica",
                str(int(ultima_semana.get("SE", ultima_semana.get("se", 0)))),
            )
            m2.metric("Casos estimados (última semana)", int(ultima_semana.get(casos_col, 0)))
            m3.metric("Total de casos no período", int(df[casos_col].sum()))

            st.subheader("📈 Evolução de casos ao longo do tempo")
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df["data"], y=df[casos_col], mode="lines",
                    name="Casos estimados", line=dict(color="#d62728", width=2),
                )
            )
            if "casos_estmin" in df.columns and "casos_estmax" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["data"], y=df["casos_estmax"], mode="lines",
                        line=dict(width=0), showlegend=False,
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=df["data"], y=df["casos_estmin"], mode="lines",
                        line=dict(width=0), fill="tonexty",
                        fillcolor="rgba(214, 39, 40, 0.15)",
                        name="Intervalo de confiança",
                    )
                )
            fig.update_layout(
                xaxis_title="Data", yaxis_title="Número de casos",
                hovermode="x unified", height=450,
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📊 Comparação de casos por ano")
            df["ano"] = df["data"].dt.year
            casos_por_ano = df.groupby("ano")[casos_col].sum().reset_index()
            fig_barras = go.Figure(
                data=[go.Bar(x=casos_por_ano["ano"], y=casos_por_ano[casos_col], marker_color="#1f77b4")]
            )
            fig_barras.update_layout(
                xaxis_title="Ano", yaxis_title="Total de casos estimados", height=350
            )
            st.plotly_chart(fig_barras, use_container_width=True)

            with st.expander("Ver dados brutos"):
                st.dataframe(df, use_container_width=True)

# =============================================================================
# ABA 2 — MAPA INTERATIVO POR ESTADO (drill-down até a cidade)
# =============================================================================
with tab_mapa:
    st.subheader("Mapa de risco por município")
    st.caption(
        "Escolha um estado para ver o nível de alerta de cada cidade num mapa interativo. "
        "Estados maiores podem levar alguns segundos para carregar (uma consulta por município)."
    )

    estados = lista_estados()

    col_a, col_b = st.columns([2, 1])
    with col_a:
        estado_selecionado = st.selectbox(
            "Estado (UF)",
            options=estados,
            format_func=lambda e: f"{e['nome']} ({e['uf']})",
            index=None,
            placeholder="Escolha um estado...",
            key="select_estado",
        )
    with col_b:
        doenca_mapa = st.selectbox(
            "Doença",
            options=["dengue", "chikungunya", "zika"],
            format_func=lambda d: d.capitalize(),
            key="doenca_mapa",
        )

    if estado_selecionado is None:
        st.info("👆 Selecione um estado para carregar o mapa.")
    else:
        cidades = cidades_do_estado(estado_selecionado["codigo_uf"])
        total_cidades = len(cidades)

        carregar = st.button(
            f"Carregar mapa de {estado_selecionado['nome']} ({total_cidades} municípios)",
            type="primary",
        )

        cache_key = f"mapa_dados_{estado_selecionado['uf']}_{doenca_mapa}"

        if carregar or cache_key in st.session_state:
            if carregar:
                barra = st.progress(0.0, text="Consultando InfoDengue para cada município...")

                def _atualizar_barra(concluidos: int, total: int):
                    barra.progress(concluidos / total, text=f"Consultando municípios... {concluidos}/{total}")

                dados_lote, erros_lote = buscar_dados_em_lote(
                    geocodes=cidades["codigo_ibge"].tolist(),
                    doenca=doenca_mapa,
                    progresso_callback=_atualizar_barra,
                )
                barra.empty()
                st.session_state[cache_key] = dados_lote
                st.session_state[f"{cache_key}_erros"] = erros_lote

            dados_lote = st.session_state[cache_key]
            erros_lote = st.session_state.get(f"{cache_key}_erros", {})

            if dados_lote.empty:
                total_erros = sum(erros_lote.values()) if erros_lote else 0
                sem_dado_count = erros_lote.get("sem_dado", 0)
                maioria_sem_dado = total_erros > 0 and sem_dado_count / total_erros >= 0.9

                if doenca_mapa != "dengue" and maioria_sem_dado:
                    st.info(
                        f"📭 Nenhum município de {estado_selecionado['nome']} tem série de "
                        f"dados recente o suficiente para calcular o nível de alerta de "
                        f"**{doenca_mapa}**. Isso é esperado: como os casos de "
                        f"{doenca_mapa} são bem menos numerosos que os de dengue nos últimos "
                        f"anos, o InfoDengue frequentemente não tem dado suficiente para "
                        f"gerar o indicador semanal na maioria dos municípios. Tente "
                        f"selecionar **Dengue**, que tem cobertura de dados muito mais ampla."
                    )
                else:
                    st.warning("Não foi possível obter dados para nenhum município deste estado.")

                if erros_lote:
                    with st.expander("🔧 Detalhes técnicos (diagnóstico)"):
                        st.write(
                            "Resumo dos motivos pelos quais nenhuma cidade retornou dado:"
                        )
                        st.json(erros_lote)
                        st.caption(
                            "'sem_dado' significa que a API respondeu normalmente, mas não "
                            "tem série histórica para essa doença nessa cidade (comum em "
                            "cidades pequenas para zika/chikungunya). Erros como 'HTTP 429' "
                            "ou 'timeout' indicam bloqueio/limite de requisições da API."
                        )
            else:
                mapa_df = cidades.merge(
                    dados_lote, left_on="codigo_ibge", right_on="geocode", how="inner"
                )
                mapa_df["cor"] = mapa_df["nivel"].map(NIVEL_COR_RGBA)
                mapa_df["raio"] = (mapa_df["casos"].clip(lower=1) ** 0.5) * 400 + 1500

                cobertura = len(mapa_df) / total_cidades if total_cidades else 0
                st.caption(
                    f"{len(mapa_df)} de {total_cidades} municípios com dado disponível "
                    f"para {doenca_mapa}."
                )
                if doenca_mapa != "dengue" and cobertura < 0.5:
                    st.caption(
                        f"ℹ️ Cobertura de dados mais baixa é esperada para {doenca_mapa}, "
                        f"já que essa doença tem bem menos casos notificados que dengue "
                        f"nos últimos anos."
                    )

                # --- Resumo por nível de alerta ------------------------------
                resumo = mapa_df["nivel"].value_counts().sort_index()
                cols_resumo = st.columns(4)
                for i, nivel_id in enumerate([1, 2, 3, 4]):
                    qtd = int(resumo.get(nivel_id, 0))
                    info = NIVEL_ALERTA[nivel_id]
                    cols_resumo[i].metric(f"{info['cor']} {info['label'].split(' - ')[0]}", qtd)

                # --- Mapa (pydeck) --------------------------------------------
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=mapa_df,
                    get_position="[longitude, latitude]",
                    get_fill_color="cor",
                    get_radius="raio",
                    pickable=True,
                    opacity=0.8,
                )
                view_state = pdk.ViewState(
                    latitude=estado_selecionado["latitude"],
                    longitude=estado_selecionado["longitude"],
                    zoom=5.5,
                )
                st.pydeck_chart(
                    pdk.Deck(
                        layers=[layer],
                        initial_view_state=view_state,
                        tooltip={"text": "{nome}\nCasos estimados: {casos}\nNível: {nivel}"},
                    )
                )

                # --- Ranking das cidades em maior risco -------------------------
                st.subheader("📋 Ranking de municípios por casos estimados")
                ranking = (
                    mapa_df[["nome", "nivel", "casos"]]
                    .sort_values("casos", ascending=False)
                    .reset_index(drop=True)
                )
                ranking["Alerta"] = ranking["nivel"].map(lambda n: NIVEL_ALERTA.get(n, {}).get("cor", "⚪"))
                ranking = ranking.rename(columns={"nome": "Município", "casos": "Casos estimados"})
                st.dataframe(
                    ranking[["Alerta", "Município", "Casos estimados"]].head(30),
                    use_container_width=True,
                    hide_index=True,
                )

st.caption(
    "Fonte: InfoDengue (Fiocruz/EMAp-FGV) — info.dengue.mat.br | "
    "IBGE — servicodados.ibge.gov.br | "
    "Coordenadas: kelvins/Municipios-Brasileiros (github.com/kelvins). "
    "Dados das semanas mais recentes são preliminares."
)
