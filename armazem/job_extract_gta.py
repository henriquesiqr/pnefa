from pathlib import Path
import sys
import time

import pandas as pd
from dotenv import dotenv_values
from sqlalchemy import create_engine, text


# =============================================================================
# CONFIGURAÇÃO DE PATH
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARMAZEM_DIR = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# PARÂMETROS AJUSTÁVEIS
# =============================================================================

SOURCE_ENV_PATH = PROJECT_ROOT / "env_homolog.conf"
TARGET_ENV_PATH = PROJECT_ROOT / "env_armazem.conf"

DATABASE_URL_KEY = "ARMAZEM_DATABASE_URL"

SOURCE_SCHEMA = "public"
SOURCE_TABLE = "gta_deteccao_fraude"

TARGET_SCHEMA = "public"
TARGET_TABLE = "aftosa_gta"

IF_EXISTS = "replace"
CHUNKSIZE = 5000

QUERY_ARMAZEM_GTA_PATH = (
    ARMAZEM_DIR
    / "armazem_gta.sql"
)

TARGET_COLUMNS = [
    "codigo_da_propriedade",
    "estoque_destino",
    "area_ha",
    "data_atualizacao_destino",
]


# =============================================================================
# CONEXÕES
# =============================================================================

def get_engine_from_env(env_path: Path):
    """
    Cria engine SQLAlchemy a partir de um arquivo .conf específico.
    """

    if not env_path.exists():
        raise FileNotFoundError(f"Arquivo de ambiente não encontrado: {env_path}")

    env_values = dotenv_values(env_path)
    database_url = env_values.get(DATABASE_URL_KEY)

    if not database_url:
        raise ValueError(f"{DATABASE_URL_KEY} não encontrada em {env_path}")

    return create_engine(database_url)


def get_source_engine():
    """
    Cria engine para o Armazém ima-homolog.
    """

    return get_engine_from_env(SOURCE_ENV_PATH)


def get_target_engine():
    """
    Cria engine para o Armazém ima-dev.
    """

    return get_engine_from_env(TARGET_ENV_PATH)


# =============================================================================
# QUERY
# =============================================================================

def load_query_armazem_gta() -> str:
    """
    Carrega a query armazem_gta.sql.
    """

    if not QUERY_ARMAZEM_GTA_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo SQL não encontrado: {QUERY_ARMAZEM_GTA_PATH}"
        )

    return QUERY_ARMAZEM_GTA_PATH.read_text(encoding="utf-8")


# =============================================================================
# EXTRAÇÃO
# =============================================================================

def extract_from_homolog() -> pd.DataFrame:
    """
    Extrai dados da tabela gta_deteccao_fraude no ima-homolog.
    """

    engine = get_source_engine()
    query = load_query_armazem_gta()

    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado à origem ima-homolog: {info}")

        df = pd.read_sql(query, conn)

    return df


# =============================================================================
# TRANSFORMAÇÃO
# =============================================================================

def transform_aftosa_gta(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza os dados antes da carga no ima-dev.
    """

    df = df.copy()

    df.columns = [col.strip().lower() for col in df.columns]

    missing_cols = [col for col in TARGET_COLUMNS if col not in df.columns]

    if missing_cols:
        raise ValueError(
            f"Colunas ausentes após extração: {missing_cols}\n"
            f"Colunas disponíveis: {list(df.columns)}"
        )

    df = df[TARGET_COLUMNS]

    df["codigo_da_propriedade"] = (
        df["codigo_da_propriedade"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["estoque_destino"] = pd.to_numeric(
        df["estoque_destino"],
        errors="coerce",
    ).astype("Int64")

    df["area_ha"] = pd.to_numeric(
        df["area_ha"],
        errors="coerce",
    )

    df["data_atualizacao_destino"] = pd.to_datetime(
        df["data_atualizacao_destino"],
        errors="coerce",
    )

    df = df[
        ~df["codigo_da_propriedade"]
        .fillna("")
        .astype(str)
        .str.strip()
        .isin(["", "nan", "none", "null"])
    ]

    df = df.drop_duplicates(
        subset=["codigo_da_propriedade"],
        keep="first",
    )

    return df


# =============================================================================
# VALIDAÇÃO
# =============================================================================

def validate_aftosa_gta(df: pd.DataFrame) -> None:
    """
    Valida os dados antes da carga no ima-dev.
    """

    if df.empty:
        raise ValueError("A extração retornou zero linhas válidas. Carga abortada.")

    nulos_codigo = (
        df["codigo_da_propriedade"]
        .fillna("")
        .astype(str)
        .str.strip()
        .isin(["", "nan", "none", "null"])
        .sum()
    )

    if nulos_codigo > 0:
        raise ValueError(
            f"Existem {nulos_codigo} linhas com codigo_da_propriedade nulo."
        )

    duplicados = df["codigo_da_propriedade"].duplicated().sum()

    if duplicados > 0:
        raise ValueError(
            f"Existem {duplicados} códigos de propriedade duplicados."
        )

    print("Validação concluída.")
    print(f"Total de linhas: {len(df)}")
    print(f"Total de propriedades: {df['codigo_da_propriedade'].nunique()}")
    print(f"Estoque destino preenchido: {df['estoque_destino'].notna().sum()}")
    print(f"Área ha preenchida: {df['area_ha'].notna().sum()}")
    print(
        "Data atualização destino preenchida: "
        f"{df['data_atualizacao_destino'].notna().sum()}"
    )


# =============================================================================
# CARGA
# =============================================================================

def load_to_dev(df: pd.DataFrame) -> None:
    """
    Carrega a tabela intermediária aftosa_gta no ima-dev.
    """

    engine = get_target_engine()

    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao destino ima-dev: {info}")

    df.to_sql(
        name=TARGET_TABLE,
        con=engine,
        schema=TARGET_SCHEMA,
        if_exists=IF_EXISTS,
        index=False,
        method="multi",
        chunksize=CHUNKSIZE,
    )

    with engine.connect() as conn:
        qtd = conn.execute(
            text(f"SELECT COUNT(*) FROM {TARGET_SCHEMA}.{TARGET_TABLE};")
        ).fetchone()[0]

        print(f"Total carregado em {TARGET_SCHEMA}.{TARGET_TABLE}: {qtd}")


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main():
    inicio = time.time()

    print("Iniciando carga da tabela aftosa_gta")
    print(f"Origem: ima-homolog.{SOURCE_SCHEMA}.{SOURCE_TABLE}")
    print(f"Destino: ima-dev.{TARGET_SCHEMA}.{TARGET_TABLE}")

    print("\nExtraindo dados do ima-homolog...")
    df = extract_from_homolog()

    print(f"Linhas extraídas: {len(df)}")
    print(f"Colunas extraídas: {list(df.columns)}")

    print("\nTransformando dados...")
    df = transform_aftosa_gta(df)

    print("\nValidando dados...")
    validate_aftosa_gta(df)

    print("\nCarregando dados no ima-dev...")
    load_to_dev(df)

    fim = time.time()
    print(f"\nCarga finalizada em {fim - inicio:.2f} segundos.")


if __name__ == "__main__":
    main()