# jobs/aftosa/job_extract_aftosa_propriedade_exploracao.py

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
ARMAZEM_TABLE = "aftosa_propriedade_exploracao"

IF_EXISTS = "append"
CHUNKSIZE = 5000

QUERY_AFTOSA_PATH = (
    PROJECT_ROOT
    / "armazem"
    / "aftosa_propriedade_exploracao.sql"
)


# =============================================================================
# CONEXÃO
# =============================================================================

def get_armazem_engine():
    """
    Cria engine SQLAlchemy para o Armazém.

    Neste job, o Armazém é usado tanto como origem quanto como destino.
    """

    import os

    database_url = os.getenv("ARMAZEM_DATABASE_URL")

    if not database_url:
        raise ValueError("ARMAZEM_DATABASE_URL não encontrada no env_armazem.conf")

    return create_engine(database_url)


# =============================================================================
# QUERY ARMAZÉM
# =============================================================================

def load_query_aftosa() -> str:
    """
    Carrega a query de aftosa a partir do arquivo .sql.
    """

    if not QUERY_AFTOSA_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de query não encontrado: {QUERY_AFTOSA_PATH}"
        )

    return QUERY_AFTOSA_PATH.read_text(encoding="utf-8")


# =============================================================================
# EXTRAÇÃO
# =============================================================================

def extract_from_armazem(query: str) -> pd.DataFrame:
    """
    Extrai os dados do próprio Armazém.
    """

    engine = get_armazem_engine()

    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao Armazém para extração: {info}")

        df = pd.read_sql_query(
            sql=text(query),
            con=conn,
        )

    return df


# =============================================================================
# TRANSFORMAÇÃO
# =============================================================================

def transform_aftosa_propriedade_exploracao(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza a base de aftosa antes da carga no Armazém.

    Este job preenche apenas parte das colunas da tabela final.
    As demais colunas serão preenchidas por outros jobs.
    """

    df = df.copy()

    df.columns = [col.strip().lower() for col in df.columns]

    text_cols = [
        "codigo_do_municipio",
        "descricao_do_municipio",
        "codigo_da_propriedade",
        "nome_da_propriedade",
        "nome_do_produtor_responsavel",
        "cpf_cnpj_do_produtor",
    ]

    for col in text_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    if "data_da_atualizacao_cadastral" in df.columns:
        df["data_da_atualizacao_cadastral"] = pd.to_datetime(
            df["data_da_atualizacao_cadastral"],
            errors="coerce",
        )

    return df


# =============================================================================
# VALIDAÇÃO
# =============================================================================

def validate_aftosa_propriedade_exploracao(df: pd.DataFrame) -> None:
    """
    Executa validações mínimas antes da carga.

    A validação considera apenas as colunas preenchidas por este job.
    """

    if df.empty:
        raise ValueError("A consulta retornou zero linhas. Carga abortada.")

    required_cols = [
        "codigo_do_municipio",
        "descricao_do_municipio",
        "codigo_da_propriedade",
        "nome_da_propriedade",
        "nome_do_produtor_responsavel",
        "cpf_cnpj_do_produtor",
        "data_da_atualizacao_cadastral",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Colunas ausentes no DataFrame: {missing_cols}")

    nulos_codigo_propriedade = (
        df["codigo_da_propriedade"]
        .fillna("")
        .astype(str)
        .str.strip()
        .isin(["", "nan", "none", "null"])
        .sum()
    )

    if nulos_codigo_propriedade > 0:
        raise ValueError(
            f"Existem {nulos_codigo_propriedade} linhas sem codigo_da_propriedade."
        )

    print("Validação concluída.")
    print(f"Total de linhas: {len(df)}")
    print(f"Total de municípios: {df['codigo_do_municipio'].nunique()}")
    print(f"Total de propriedades: {df['codigo_da_propriedade'].nunique()}")


# =============================================================================
# CARGA
# =============================================================================

def load_to_armazem(df: pd.DataFrame) -> None:
    """
    Insere o DataFrame na tabela aftosa_propriedade_exploracao.

    Apenas as colunas presentes no DataFrame serão inseridas.
    As demais colunas da tabela devem aceitar NULL ou possuir valor padrão.
    """

    engine = get_armazem_engine()

    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao Armazém para carga: {info}")

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

    print("Iniciando carga de aftosa Armazém -> Armazém")

    print("Carregando query de aftosa...")
    query_aftosa = load_query_aftosa()

    print("Extraindo dados do Armazém...")
    df = extract_from_armazem(query_aftosa)

    print(f"Linhas extraídas: {len(df)}")

    print("Transformando dados...")
    df = transform_aftosa_propriedade_exploracao(df)

    print("Validando dados...")
    validate_aftosa_propriedade_exploracao(df)

    print("Carregando dados no Armazém...")
    load_to_armazem(df)

    fim = time.time()
    print(f"Carga finalizada em {fim - inicio:.2f} segundos.")


if __name__ == "__main__":
    main()