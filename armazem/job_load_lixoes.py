from pathlib import Path
import sys
import time

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
ARMAZEM_TABLE = "aftosa_lixao"

IF_EXISTS = "append"
CHUNKSIZE = 5000

CSV_LIXOES_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "04_lixoes"
    / "lixoes_municipio_MG_v2.csv"
)

CSV_SEP = ","
CSV_ENCODING = "utf-8"

TARGET_COLUMNS = [
    "id",
    "municipio",
    "latitude",
    "longitude",
    "compart",
    "cod_municipio",
    "area_km2",
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

def extract_from_csv() -> pd.DataFrame:
    """
    Extrai os dados de lixões a partir do arquivo CSV.
    """

    if not CSV_LIXOES_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo CSV não encontrado: {CSV_LIXOES_PATH}"
        )

    df = pd.read_csv(
        CSV_LIXOES_PATH,
        sep=CSV_SEP,
        encoding=CSV_ENCODING,
        dtype=str,
    )

    return df


# =============================================================================
# TRANSFORMAÇÃO
# =============================================================================

def transform_lixoes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza a base de lixões antes da carga no Armazém.
    """

    df = df.copy()

    df.columns = [col.strip().lower() for col in df.columns]

    rename_columns = {
        "fid": "id",
        "lat": "latitude",
        "long": "longitude",
        "cd_mun": "cod_municipio",
        "area_km2": "area_km2",
    }

    df = df.rename(columns=rename_columns)

    text_cols = [
        "municipio",
        "compart",
        "cod_municipio",
    ]

    for col in text_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    if "id" in df.columns:
        df["id"] = pd.to_numeric(
            df["id"],
            errors="coerce",
        ).astype("Int64")

    numeric_cols = [
        "latitude",
        "longitude",
        "area_km2",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    df = df[TARGET_COLUMNS]

    return df


# =============================================================================
# VALIDAÇÃO
# =============================================================================

def validate_lixoes(df: pd.DataFrame) -> None:
    """
    Executa validações mínimas antes da carga.
    """

    if df.empty:
        raise ValueError("O CSV retornou zero linhas. Carga abortada.")

    missing_cols = [col for col in TARGET_COLUMNS if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Colunas ausentes no DataFrame: {missing_cols}")

    nulos_id = df["id"].isna().sum()

    if nulos_id > 0:
        raise ValueError(f"Existem {nulos_id} linhas com id nulo.")

    nulos_municipio = (
        df["municipio"]
        .fillna("")
        .astype(str)
        .str.strip()
        .isin(["", "nan", "none", "null"])
        .sum()
    )

    if nulos_municipio > 0:
        raise ValueError(f"Existem {nulos_municipio} linhas com municipio nulo.")

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

    nulos_latitude = df["latitude"].isna().sum()

    if nulos_latitude > 0:
        raise ValueError(f"Existem {nulos_latitude} linhas com latitude nula.")

    nulos_longitude = df["longitude"].isna().sum()

    if nulos_longitude > 0:
        raise ValueError(f"Existem {nulos_longitude} linhas com longitude nula.")

    ids_duplicados = df["id"].duplicated().sum()

    if ids_duplicados > 0:
        raise ValueError(f"Existem {ids_duplicados} ids duplicados.")

    print("Validação concluída.")
    print(f"Total de linhas: {len(df)}")
    print(f"Total de municípios: {df['cod_municipio'].nunique()}")
    print(df["compart"].value_counts(dropna=False))


# =============================================================================
# CARGA
# =============================================================================

def load_to_armazem(df: pd.DataFrame) -> None:
    """
    Insere o DataFrame na tabela aftosa_lixao do Armazém.
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

    print("Iniciando carga de lixões CSV -> Armazém")

    print("Extraindo dados do CSV...")
    df = extract_from_csv()

    print(f"Linhas extraídas: {len(df)}")

    print("Transformando dados...")
    df = transform_lixoes(df)

    print("Validando dados...")
    validate_lixoes(df)

    print("Carregando dados no Armazém...")
    load_to_armazem(df)

    fim = time.time()
    print(f"Carga finalizada em {fim - inicio:.2f} segundos.")


if __name__ == "__main__":
    main()