from pathlib import Path
import sys
import time

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# =============================================================================
# CONFIGURACAO DE PATH
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARMAZEM_DIR = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# CONFIGURACAO DE AMBIENTE
# =============================================================================

load_dotenv(PROJECT_ROOT / "env_armazem.conf")


# =============================================================================
# PARAMETROS AJUSTAVEIS
# =============================================================================

ARMAZEM_SCHEMA = "public"
ARMAZEM_TABLE = "aftosa_eventos"

IF_EXISTS = "append"
CHUNKSIZE = 5000

CSV_EVENTOS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "05_eventos"
    / "ESTABELECIMENTOS_EVENTOS_2025.csv"
)

CSV_SEP = ","
CSV_ENCODING = "utf-8"

TARGET_COLUMNS = [
    "cod_estab_evento",
    "ds_estab_evento_tipo",
    "proprietario_recinto",
    "nm_pessoa",
    "ds_municipio",
    "latitude",
    "longitude",
    "n_eventos_realizados",
    "n_gta",
    "n_animais",
]

TEXT_COLUMNS = [
    "cod_estab_evento",
    "ds_estab_evento_tipo",
    "proprietario_recinto",
    "nm_pessoa",
    "ds_municipio",
]

NUMERIC_COLUMNS = [
    "latitude",
    "longitude",
    "n_eventos_realizados",
    "n_gta",
    "n_animais",
]


# =============================================================================
# CONEXAO
# =============================================================================

def get_armazem_engine():
    """
    Cria engine SQLAlchemy para o Armazem.
    """

    import os

    database_url = os.getenv("ARMAZEM_DATABASE_URL")

    if not database_url:
        raise ValueError("ARMAZEM_DATABASE_URL nao encontrada no env_armazem.conf")

    return create_engine(database_url)


# =============================================================================
# EXTRACAO
# =============================================================================

def extract_from_csv() -> pd.DataFrame:
    """
    Extrai os dados de eventos a partir do arquivo CSV.
    """

    if not CSV_EVENTOS_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo CSV nao encontrado: {CSV_EVENTOS_PATH}"
        )

    return pd.read_csv(
        CSV_EVENTOS_PATH,
        sep=CSV_SEP,
        encoding=CSV_ENCODING,
        dtype=str,
    )


# =============================================================================
# TRANSFORMACAO
# =============================================================================

def transform_eventos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza a base de eventos antes da carga no Armazem.
    """

    df = df.copy()

    rename_columns = {
        "LATITUDE": "latitude",
        "LONGITUDE": "longitude",
    }

    df = df.rename(columns=rename_columns)

    missing_cols = [col for col in TARGET_COLUMNS if col not in df.columns]

    if missing_cols:
        raise ValueError(
            f"Colunas ausentes apos renomeacao: {missing_cols}\n"
            f"Colunas disponiveis: {list(df.columns)}"
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
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .str.strip()
            )

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    for col in ["n_eventos_realizados", "n_gta", "n_animais"]:
        if col in df.columns:
            df[col] = df[col].astype("Int64")

    return df


# =============================================================================
# VALIDACAO
# =============================================================================

def validate_eventos(df: pd.DataFrame) -> None:
    """
    Executa validacoes minimas antes da carga.
    """

    if df.empty:
        raise ValueError("O CSV retornou zero linhas. Carga abortada.")

    missing_cols = [col for col in TARGET_COLUMNS if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Colunas ausentes no DataFrame: {missing_cols}")

    for col in ["cod_estab_evento", "proprietario_recinto", "nm_pessoa", "ds_municipio"]:
        nulos = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(["", "nan", "none", "null"])
            .sum()
        )

        if nulos > 0:
            raise ValueError(f"Existem {nulos} linhas com {col} nulo.")

    for col in ["latitude", "longitude", "n_eventos_realizados", "n_gta", "n_animais"]:
        nulos = df[col].isna().sum()

        if nulos > 0:
            raise ValueError(f"Existem {nulos} linhas com {col} nulo.")

    duplicados = df["cod_estab_evento"].duplicated().sum()

    if duplicados > 0:
        raise ValueError(f"Existem {duplicados} cod_estab_evento duplicados.")

    tipos_vazios = (
        df["ds_estab_evento_tipo"]
        .fillna("")
        .astype(str)
        .str.strip()
        .isin(["", "nan", "none", "null"])
        .sum()
    )

    if tipos_vazios > 0:
        print(
            f"Aviso: existem {tipos_vazios} linhas com ds_estab_evento_tipo vazio."
        )

    print("Validacao concluida.")
    print(f"Total de linhas: {len(df)}")
    print(f"Total de municipios: {df['ds_municipio'].nunique()}")
    print(f"Total de estabelecimentos: {df['cod_estab_evento'].nunique()}")
    print(f"Total de GTAs: {df['n_gta'].sum()}")
    print(f"Total de animais: {df['n_animais'].sum()}")
    print("\nDistribuicao por tipo de estabelecimento:")
    print(df["ds_estab_evento_tipo"].value_counts(dropna=False))


# =============================================================================
# CARGA
# =============================================================================

def load_to_armazem(df: pd.DataFrame) -> None:
    """
    Insere o DataFrame na tabela aftosa_eventos do Armazem.
    """

    engine = get_armazem_engine()

    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao Armazem: {info}")

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
# EXECUCAO
# =============================================================================

def main():
    inicio = time.time()

    print("Iniciando carga de eventos CSV -> Armazem")

    print("Extraindo dados do CSV...")
    df = extract_from_csv()

    print(f"Linhas extraidas: {len(df)}")
    print(f"Colunas extraidas: {list(df.columns)}")

    print("Transformando dados...")
    df = transform_eventos(df)

    print("Validando dados...")
    validate_eventos(df)

    print("Carregando dados no Armazem...")
    load_to_armazem(df)

    fim = time.time()
    print(f"Carga finalizada em {fim - inicio:.2f} segundos.")


if __name__ == "__main__":
    main()
