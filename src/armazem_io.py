# ==========================================================
# Módulo: armazem_io.py
# Objetivo:
# Centralizar a leitura de dados diretamente do Armazém.
# ==========================================================


import os

import pandas as pd
import requests
from dotenv import load_dotenv


# ==========================================================
# CONFIGURAÇÃO DE AMBIENTE
# ==========================================================


load_dotenv()


# ==========================================================
# PARÂMETROS AJUSTÁVEIS
# ==========================================================

ARMAZEM_DEFAULT_PORT = "9100"
ARMAZEM_DEFAULT_PROTOCOL = "http"
ARMAZEM_DEFAULT_GRAPHQL_PATH = "/graphql"

TABELA_PROPRIEDADES_RISCO = "aftosa_propriedade_exploracao"

COLUNAS_OBRIGATORIAS_PROPRIEDADES_RISCO = [
    "codigo_do_municipio",
    "descricao_do_municipio",
    "codigo_da_propriedade",
    "nome_da_propriedade",
    "codigo_da_exploracao",
    "nome_do_produtor_responsavel",
    "cpf_cnpj_do_produtor",
    "quantidade_de_bovinos",
    "data_da_atualizacao_cadastral",
    "situacao_da_exploracao",
    "ano_atualizacao",
    "esec",
    "coordenadoria",
    "num_area",
    "latitude",
    "longitude",
    "geometry",
]

COLUNAS_CODIGO_PROPRIEDADES_RISCO = [
    "codigo_do_municipio",
    "codigo_da_propriedade",
    "codigo_da_exploracao",
    "cpf_cnpj_do_produtor",
]


# ==========================================================
# CONFIGURAÇÃO DA API
# ==========================================================

def get_armazem_graphql_url() -> str:
    """
    Monta a URL GraphQL do Armazém a partir das variáveis de ambiente.
    """

    host = os.getenv("ARMAZEM_HOST")
    port = os.getenv("ARMAZEM_PORT", ARMAZEM_DEFAULT_PORT)
    protocol = os.getenv("ARMAZEM_PROTOCOL", ARMAZEM_DEFAULT_PROTOCOL)
    graphql_path = os.getenv("ARMAZEM_GRAPHQL_PATH", ARMAZEM_DEFAULT_GRAPHQL_PATH)

    if not host:
        raise EnvironmentError(
            "Variável de ambiente ARMAZEM_HOST não configurada."
        )

    graphql_path = graphql_path if graphql_path.startswith("/") else f"/{graphql_path}"

    return f"{protocol}://{host}:{port}{graphql_path}"


def get_armazem_headers() -> dict:
    """
    Monta os headers para autenticação na API do Armazém.
    """

    api_key = os.getenv("ARMAZEM_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "Variável de ambiente ARMAZEM_API_KEY não configurada."
        )

    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def executar_query_graphql(query: str, variables: dict | None = None) -> dict:
    """
    Executa uma query GraphQL no Armazém.
    """

    url = get_armazem_graphql_url()
    headers = get_armazem_headers()

    response = requests.post(
        url,
        json={
            "query": query,
            "variables": variables or {},
        },
        headers=headers,
        timeout=60,
    )

    response.raise_for_status()

    payload = response.json()

    if "errors" in payload:
        raise RuntimeError(
            f"Erro retornado pelo GraphQL do Armazém: {payload['errors']}"
        )

    return payload["data"]


# ==========================================================
# VALIDAÇÕES E NORMALIZAÇÕES
# ==========================================================

def validar_colunas_obrigatorias(
    df: pd.DataFrame,
    colunas_obrigatorias: list[str],
) -> None:
    """
    Valida se o dataframe possui todas as colunas obrigatórias.
    """

    colunas_ausentes = set(colunas_obrigatorias) - set(df.columns)

    if colunas_ausentes:
        raise KeyError(
            "Colunas obrigatórias ausentes no dataframe vindo do Armazém: "
            f"{sorted(colunas_ausentes)}"
        )


def normalizar_colunas_propriedades_risco(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza tipos e códigos principais do dataframe vindo do Armazém.
    """

    df = df.copy()

    for coluna in COLUNAS_CODIGO_PROPRIEDADES_RISCO:
        if coluna in df.columns:
            df[coluna] = (
                df[coluna]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )

    return df


def normalizar_registros_propriedades_risco(registros: list[dict]) -> pd.DataFrame:
    """
    Converte a resposta da API do Armazém no formato esperado pelo pipeline.
    """

    df = pd.DataFrame(registros)

    if df.empty:
        return df

    rename_map = {
        "cpf_cnpj_do_produtor": "cpf/cnpj_do_produtor",
        "seccional": "esec",
    }

    df = df.rename(columns=rename_map)

    validar_colunas_obrigatorias(
        df,
        COLUNAS_OBRIGATORIAS_PROPRIEDADES_RISCO,
    )

    df = normalizar_colunas_propriedades_risco(df)

    return df


# ==========================================================
# LOADERS
# ==========================================================

def load_propriedades_risco_sanitario_from_armazem() -> pd.DataFrame:
    """
    Carrega propriedades/explorações diretamente do Armazém via GraphQL.

    Atenção:
    O nome exato do campo raiz da query pode precisar ser ajustado conforme
    o schema exposto pela API.
    """

    query = """
        query LoadPropriedadesRiscoSanitario {
            aftosaPropriedadeExploracao {
                codigo_do_municipio
                descricao_do_municipio
                codigo_da_propriedade
                nome_da_propriedade
                codigo_da_exploracao
                nome_do_produtor_responsavel
                cpf_cnpj_do_produtor
                quantidade_de_bovinos
                data_da_atualizacao_cadastral
                situacao_da_exploracao
                ano_atualizacao
                seccional
                coordenadoria
                num_area
                latitude
                longitude
                geometry
            }
        }
    """

    data = executar_query_graphql(query)

    registros = data.get("aftosaPropriedadeExploracao", [])

    df = normalizar_registros_propriedades_risco(registros)

    return df