from pathlib import Path
import sys
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# =============================================================================
# CONFIGURAÇÃO DE PATH
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
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
TARGET_COLUMN = "situacao_da_exploracao"

DRY_RUN = False


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
# VALIDAÇÃO
# =============================================================================

def count_records(engine) -> None:
    """
    Conta registros totais e registros sem situacao_da_exploracao válida.
    """

    query = text(
        f"""
        SELECT
            COUNT(*) AS total_linhas,
            COUNT(*) FILTER (
                WHERE {TARGET_COLUMN} IS NULL
                   OR TRIM({TARGET_COLUMN}::text) = ''
                   OR LOWER(TRIM({TARGET_COLUMN}::text)) IN ('nan', 'none', 'null')
            ) AS linhas_sem_situacao_da_exploracao,
            COUNT(*) FILTER (
                WHERE {TARGET_COLUMN} IS NOT NULL
                  AND TRIM({TARGET_COLUMN}::text) <> ''
                  AND LOWER(TRIM({TARGET_COLUMN}::text)) NOT IN ('nan', 'none', 'null')
            ) AS linhas_com_situacao_da_exploracao
        FROM {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE};
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    print(f"Total de linhas: {result.total_linhas}")
    print(
        "Linhas sem situacao_da_exploracao: "
        f"{result.linhas_sem_situacao_da_exploracao}"
    )
    print(
        "Linhas com situacao_da_exploracao: "
        f"{result.linhas_com_situacao_da_exploracao}"
    )


def show_sample_to_delete(engine) -> None:
    """
    Mostra uma amostra das linhas que serão apagadas.
    """

    query = text(
        f"""
        SELECT
            id,
            codigo_do_municipio,
            descricao_do_municipio,
            codigo_da_propriedade,
            nome_da_propriedade,
            codigo_da_exploracao,
            {TARGET_COLUMN}
        FROM {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE}
        WHERE {TARGET_COLUMN} IS NULL
           OR TRIM({TARGET_COLUMN}::text) = ''
           OR LOWER(TRIM({TARGET_COLUMN}::text)) IN ('nan', 'none', 'null')
        LIMIT 20;
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    if not rows:
        print("\nNenhuma linha sem situacao_da_exploracao encontrada.")
        return

    print("\nAmostra de linhas que serão apagadas:")
    for row in rows:
        print(
            f"{row.id} | "
            f"{row.codigo_do_municipio} | "
            f"{row.descricao_do_municipio} | "
            f"{row.codigo_da_propriedade} | "
            f"{row.nome_da_propriedade} | "
            f"{row.codigo_da_exploracao} | "
            f"{row.situacao_da_exploracao}"
        )


# =============================================================================
# DELETE
# =============================================================================

def delete_records_without_situacao(engine) -> int:
    """
    Apaga registros sem situacao_da_exploracao válida.
    """

    query = text(
        f"""
        DELETE FROM {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE}
        WHERE {TARGET_COLUMN} IS NULL
           OR TRIM({TARGET_COLUMN}::text) = ''
           OR LOWER(TRIM({TARGET_COLUMN}::text)) IN ('nan', 'none', 'null');
        """
    )

    with engine.begin() as conn:
        result = conn.execute(query)

    return result.rowcount


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main():
    inicio = time.time()

    print("Iniciando limpeza da aftosa_propriedade_exploracao")
    print("Critério: apagar linhas sem situacao_da_exploracao")

    engine = get_armazem_engine()

    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao Armazém: {info}")

    print("\nValidação antes do delete:")
    count_records(engine)
    show_sample_to_delete(engine)

    if DRY_RUN:
        print("\nDRY_RUN=True. Nenhuma linha foi apagada.")
        return

    print("\nExecutando delete...")
    linhas_deletadas = delete_records_without_situacao(engine)

    print(f"Linhas apagadas: {linhas_deletadas}")

    print("\nValidação depois do delete:")
    count_records(engine)

    fim = time.time()
    print(f"\nLimpeza finalizada em {fim - inicio:.2f} segundos.")


if __name__ == "__main__":
    main()
