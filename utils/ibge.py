"""
Utilitários para consultar a API pública do IBGE de localidades.
Documentação: https://servicodados.ibge.gov.br/api/docs/localidades
"""
import requests
import streamlit as st

IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


@st.cache_data(ttl=60 * 60 * 24)  # cache de 24h, a lista de municípios não muda
def carregar_municipios() -> list[dict]:
    """
    Retorna a lista completa de municípios do Brasil, com nome, geocode (id)
    e UF. Usado para popular o seletor de cidades do app.
    """
    resp = requests.get(IBGE_MUNICIPIOS_URL, timeout=15)
    resp.raise_for_status()
    dados = resp.json()

    municipios = []
    for m in dados:
        municipios.append(
            {
                "geocode": m["id"],
                "nome": m["nome"],
                "uf": m["microrregiao"]["mesorregiao"]["UF"]["sigla"],
            }
        )
    # Ordena por nome para facilitar a busca no selectbox
    municipios.sort(key=lambda x: x["nome"])
    return municipios


def formatar_opcao(municipio: dict) -> str:
    """Formata a exibição no selectbox: 'Nome da Cidade - UF'."""
    return f"{municipio['nome']} - {municipio['uf']}"
