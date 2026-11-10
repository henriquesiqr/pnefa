from pathlib import Path
import sys
import time
import re

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# =============================================================================
# CONFIGURAÇÃO DE PATH
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARMAZEM_DIR = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# CONFIGURAÇÃO DE AMBIENTE
# =============================================================================

load_dotenv(PROJECT_ROOT / "env_armazem.conf")


# =============================================================================
# PARÂMETROS AJUSTÁVEIS
# =============================================================================

ARMAZEM_SCHEMA = "public"
ARMAZEM_TABLE = "aftosa_suinos"

IF_EXISTS = "append"
CHUNKSIZE = 5000

XLSX_SUINOS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "03_suinos"
    / "relatorio_suinos.xlsx"
)

XLSX_SHEET_NAME = "Planilha1"

TARGET_COLUMNS = [
    "risco",
    "coordenadoria_regional",
    "escritorio_seccional",
    "cod_propriedade",
    "nome_propriedade",
    "cod_produtor",
    "nome_do_produtor",
    "situacao_fundiaria",
    "cod_geodsa",
    "nome_fantasia",
    "status_propriedade",
    "sub_status_propriedade",
    "cod_municipio",
    "municipio",
    "latitude",
    "longitude",
    "status_risco",
    "sub_status_risco",
    "nome_da_especie",
    "acesso_ao_mercado",
    "integradora_cooperativa",
    "m_vet_habilitado",
    "m_vet_nao_habilitado",
    "origem_animais",
    "origem_reproducao",
    "certificada_grsc",
    "numero_grsc",
    "sistema_de_criacao",
    "tipo_de_producao",
    "tipo_producao_tec",
    "tipo_de_manejo",
    "finalidade_producao",
    "vulnerabilidade",
    "macho_leitao",
    "femea_leitao",
    "macho_reprodutor_cachaco",
    "femea_matriz",
    "sexo_e_idade_nao_relevantes",
    "total",
]

TEXT_COLUMNS = [
    "risco",
    "coordenadoria_regional",
    "escritorio_seccional",
    "cod_propriedade",
    "nome_propriedade",
    "cod_produtor",
    "nome_do_produtor",
    "situacao_fundiaria",
    "cod_geodsa",
    "nome_fantasia",
    "status_propriedade",
    "sub_status_propriedade",
    "cod_municipio",
    "municipio",
    "status_risco",
    "sub_status_risco",
    "nome_da_especie",
    "acesso_ao_mercado",
    "integradora_cooperativa",
    "m_vet_habilitado",
    "m_vet_nao_habilitado",
    "origem_animais",
    "origem_reproducao",
    "certificada_grsc",
    "numero_grsc",
    "sistema_de_criacao",
    "tipo_de_producao",
    "tipo_producao_tec",
    "tipo_de_manejo",
    "finalidade_producao",
    "vulnerabilidade",
]

NUMERIC_COLUMNS = [
    "latitude",
    "longitude",
    "macho_leitao",
    "femea_leitao",
    "macho_reprodutor_cachaco",
    "femea_matriz",
    "sexo_e_idade_nao_relevantes",
    "total",
]


# =============================================================================
# CONEXÃO
# =============================================================================

def get_armazem_engine():
    """
    Cria engine SQLAlchemy para o Armazém.
    """

    import os

    database_url = os.getenv("ARMAZEM_DATABASE_URL")

    if not database_url:
        raise ValueError("ARMAZEM_DATABASE_URL não encontrada no env_armazem.conf")

    return create_engine(database_url)


# =============================================================================
# EXTRAÇÃO
# =============================================================================

def extract_from_xlsx() -> pd.DataFrame:
    """
    Extrai os dados de suínos a partir do arquivo XLSX.
    """

    if not XLSX_SUINOS_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo XLSX não encontrado: {XLSX_SUINOS_PATH}"
        )

    df = pd.read_excel(
        XLSX_SUINOS_PATH,
        sheet_name=XLSX_SHEET_NAME,
        dtype=str,
    )

    return df


# =============================================================================
# TRANSFORMAÇÃO
# =============================================================================

def dms_to_decimal(value):
    """
    Converte coordenadas em graus, minutos e segundos para decimal.

    Exemplo:
    -16° 47' 53.59500" -> -16.798221
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    try:
        return float(value.replace(",", "."))
    except ValueError:
        pass

    pattern = r"(-?\d+)[°\s]+(\d+)'?\s+([\d.,]+)"
    match = re.search(pattern, value)

    if not match:
        return None

    degrees = float(match.group(1))
    minutes = float(match.group(2))
    seconds = float(match.group(3).replace(",", "."))

    sign = -1 if degrees < 0 else 1

    decimal = abs(degrees) + (minutes / 60) + (seconds / 3600)

    return sign * decimal


def transform_suinos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza a base de suínos antes da carga no Armazém.
    """

    df = df.copy()

    rename_columns = {
        "risco": "risco",
        "Coordenadoria Regional": "coordenadoria_regional",
        "Escritório Seccional": "escritorio_seccional",
        "Cod. Propriedade": "cod_propriedade",
        "Nome Propriedade": "nome_propriedade",
        "Cod. Produtor": "cod_produtor",
        "Nome do Produtor": "nome_do_produtor",
        "Situação Fundiária": "situacao_fundiaria",
        "Cod. GEODSA": "cod_geodsa",
        "Nome Fantasia": "nome_fantasia",

        # Primeira dupla Status/Sub-status
        "Status": "status_propriedade",
        "Sub-status": "sub_status_propriedade",

        "Cod. Municipio": "cod_municipio",
        "Municipio": "municipio",
        "Latitude": "latitude",
        "Longitude": "longitude",

        # Segunda dupla Status/Sub-status
        "Status.1": "status_risco",
        "Sub-status.1": "sub_status_risco",

        "Nome da Espécie": "nome_da_especie",
        "Acesso ao Mercado": "acesso_ao_mercado",
        "Integradora / Cooperativa": "integradora_cooperativa",
        "M.Vet. Habilitado": "m_vet_habilitado",
        "M.Vet. Não Habilitado": "m_vet_nao_habilitado",
        "ORIGEM ANIMAIS": "origem_animais",
        "ORIGEM  REPRODUÇÃO": "origem_reproducao",
        "CERTIFICADA GRSC": "certificada_grsc",
        "Nº GRSC": "numero_grsc",
        "SISTEMA DE CRIAÇÃO": "sistema_de_criacao",
        "TIPO DE PRODUÇÃO": "tipo_de_producao",
        "TIPO PRODUÇÃO TEC.": "tipo_producao_tec",
        "TIPO DE MANEJO": "tipo_de_manejo",
        "FINALIDADE PRODUÇÃO": "finalidade_producao",
        "VULNERABILIDADE": "vulnerabilidade",
        "Macho Leitão": "macho_leitao",
        "Fêmea Leitão": "femea_leitao",
        "Macho Reprodutor (Cachaço)": "macho_reprodutor_cachaco",
        "Fêmea Matriz": "femea_matriz",
        "Sexo e idade não relevantes": "sexo_e_idade_nao_relevantes",
        "TOTAL": "total",
    }

    df = df.rename(columns=rename_columns)

    missing_cols = [col for col in TARGET_COLUMNS if col not in df.columns]

    if missing_cols:
        raise ValueError(
            f"Colunas ausentes após renomeação: {missing_cols}\n"
            f"Colunas disponíveis: {list(df.columns)}"
        )

    df = df[TARGET_COLUMNS]

    for col in TEXT_COLUMNS:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    for col in ["latitude", "longitude"]:
        if col in df.columns:
            df[col] = df[col].apply(dms_to_decimal)

    quantidade_cols = [
        "macho_leitao",
        "femea_leitao",
        "macho_reprodutor_cachaco",
        "femea_matriz",
        "sexo_e_idade_nao_relevantes",
        "total",
    ]

    for col in quantidade_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            ).fillna(0).astype("Int64")

    for col in ["latitude", "longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    return df


# =============================================================================
# VALIDAÇÃO
# =============================================================================

def validate_suinos(df: pd.DataFrame) -> None:
    """
    Executa validações mínimas antes da carga.
    """

    if df.empty:
        raise ValueError("O XLSX retornou zero linhas. Carga abortada.")

    missing_cols = [col for col in TARGET_COLUMNS if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Colunas ausentes no DataFrame: {missing_cols}")

    nulos_cod_propriedade = (
        df["cod_propriedade"]
        .fillna("")
        .astype(str)
        .str.strip()
        .isin(["", "nan", "none", "null"])
        .sum()
    )

    if nulos_cod_propriedade > 0:
        raise ValueError(
            f"Existem {nulos_cod_propriedade} linhas com cod_propriedade nulo."
        )

    nulos_cod_produtor = (
        df["cod_produtor"]
        .fillna("")
        .astype(str)
        .str.strip()
        .isin(["", "nan", "none", "null"])
        .sum()
    )

    if nulos_cod_produtor > 0:
        raise ValueError(
            f"Existem {nulos_cod_produtor} linhas com cod_produtor nulo."
        )

    nulos_cod_municipio = (
        df["cod_municipio"]
        .fillna("")
        .astype(str)
        .str.strip()
        .isin(["", "nan", "none", "null"])
        .sum()
    )

    if nulos_cod_municipio > 0:
        raise ValueError(
            f"Existem {nulos_cod_municipio} linhas com cod_municipio nulo."
        )

    nulos_municipio = (
        df["municipio"]
        .fillna("")
        .astype(str)
        .str.strip()
        .isin(["", "nan", "none", "null"])
        .sum()
    )

    if nulos_municipio > 0:
        raise ValueError(
            f"Existem {nulos_municipio} linhas com municipio nulo."
        )

    nulos_coordenadas = df[
        df["latitude"].isna() | df["longitude"].isna()
    ]

    if not nulos_coordenadas.empty:
        print(
            f"Aviso: existem {len(nulos_coordenadas)} linhas "
            "com latitude/longitude nula."
        )

        print(
            nulos_coordenadas[
                [
                    "cod_propriedade",
                    "nome_propriedade",
                    "cod_produtor",
                    "nome_do_produtor",
                    "cod_municipio",
                    "municipio",
                    "latitude",
                    "longitude",
                ]
            ]
        )

    print("Validação concluída.")
    print(f"Total de linhas: {len(df)}")
    print(f"Total de municípios: {df['cod_municipio'].nunique()}")
    print(f"Total de propriedades: {df['cod_propriedade'].nunique()}")
    print(f"Total de produtores: {df['cod_produtor'].nunique()}")
    print(f"Total de animais: {df['total'].sum()}")

    print("\nDistribuição por risco:")
    print(df["risco"].value_counts(dropna=False))

    print("\nDistribuição por sistema de criação:")
    print(df["sistema_de_criacao"].value_counts(dropna=False))


# =============================================================================
# CARGA
# =============================================================================

def load_to_armazem(df: pd.DataFrame) -> None:
    """
    Insere o DataFrame na tabela aftosa_suinos do Armazém.
    """

    engine = get_armazem_engine()

    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao Armazém: {info}")

    df.to_sql(
        name=ARMAZEM_TABLE,
        con=engine,
        schema=ARMAZEM_SCHEMA,
        if_exists=IF_EXISTS,
        index=False,
        method="multi",
        chunksize=CHUNKSIZE,
    )

    with engine.connect() as conn:
        qtd = conn.execute(
            text(f"SELECT COUNT(*) FROM {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE};")
        ).fetchone()[0]

        print(f"Total atual na tabela {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE}: {qtd}")


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main():
    inicio = time.time()

    print("Iniciando carga de suínos XLSX -> Armazém")

    print("Extraindo dados do XLSX...")
    df = extract_from_xlsx()

    print(f"Linhas extraídas: {len(df)}")
    print(f"Colunas extraídas: {list(df.columns)}")

    print("Transformando dados...")
    df = transform_suinos(df)

    print("Validando dados...")
    validate_suinos(df)

    print("Carregando dados no Armazém...")
    load_to_armazem(df)

    fim = time.time()
    print(f"Carga finalizada em {fim - inicio:.2f} segundos.")


if __name__ == "__main__":
    main()