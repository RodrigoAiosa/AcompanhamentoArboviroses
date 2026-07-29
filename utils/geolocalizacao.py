"""
Carrega coordenadas geográficas de municípios e estados a partir de arquivos
CSV locais (bundled no projeto), evitando depender de APIs externas apenas
para geolocalização.

Fonte original dos dados: https://github.com/kelvins/Municipios-Brasileiros
(dataset público, MIT license, 5.570 municípios do Brasil)
"""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent.parent / "data"


@st.cache_data(ttl=60 * 60 * 24)
def carregar_coordenadas_municipios() -> pd.DataFrame:
    """
    Retorna DataFrame com colunas: codigo_ibge, nome, latitude, longitude,
    capital, codigo_uf.
    """
    df = pd.read_csv(DATA_DIR / "municipios.csv")
    return df[["codigo_ibge", "nome", "latitude", "longitude", "capital", "codigo_uf"]]


@st.cache_data(ttl=60 * 60 * 24)
def carregar_coordenadas_estados() -> pd.DataFrame:
    """
    Retorna DataFrame com colunas: codigo_uf, uf, nome, latitude, longitude, regiao.
    """
    df = pd.read_csv(DATA_DIR / "estados.csv")
    return df


def lista_estados() -> list[dict]:
    """
    Retorna lista de dicts {uf, nome, codigo_uf, latitude, longitude} ordenada
    por nome, para popular selectbox e centralizar o mapa no estado escolhido.
    """
    df = carregar_coordenadas_estados().sort_values("nome")
    return df[["uf", "nome", "codigo_uf", "latitude", "longitude"]].to_dict("records")


def cidades_do_estado(codigo_uf: int) -> pd.DataFrame:
    """Retorna todos os municípios (com coordenadas) de um estado específico."""
    df = carregar_coordenadas_municipios()
    return df[df["codigo_uf"] == codigo_uf].sort_values("nome").reset_index(drop=True)
