from pathlib import Path
import sys
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# =============================================================================
# CONFIGURAÇÃO DE PATH
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

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
TARGET_COLUMN = "quantidade_de_bovinos"

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
    Conta registros totais, nulos e já preenchidos da coluna alvo.
    """

    query = text(
        f"""
        SELECT
            COUNT(*) AS total_linhas,
            COUNT(*) FILTER (
                WHERE {TARGET_COLUMN} IS NULL
            ) AS linhas_nulas,
            COUNT(*) FILTER (
                WHERE {TARGET_COLUMN} IS NOT NULL
            ) AS linhas_preenchidas
        FROM {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE};
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    print(f"Total de linhas: {result.total_linhas}")
    print(f"Linhas com {TARGET_COLUMN} nulo: {result.linhas_nulas}")
    print(f"Linhas com {TARGET_COLUMN} preenchido: {result.linhas_preenchidas}")


def show_sample_to_update(engine) -> None:
    """
    Mostra uma amostra das linhas que serão atualizadas.
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
        LIMIT 20;
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    if not rows:
        print(f"\nNenhuma linha com {TARGET_COLUMN} nulo encontrada.")
        return

    print(f"\nAmostra de linhas que serão atualizadas em {TARGET_COLUMN}:")
    for row in rows:
        print(
            f"{row.id} | "
            f"{row.codigo_do_municipio} | "
            f"{row.descricao_do_municipio} | "
            f"{row.codigo_da_propriedade} | "
            f"{row.nome_da_propriedade} | "
            f"{row.codigo_da_exploracao} | "
            f"{row.quantidade_de_bovinos}"
        )


# =============================================================================
# UPDATE
# =============================================================================

def fill_null_quantidade_de_bovinos(engine) -> int:
    """
    Preenche com zero as linhas em que quantidade_de_bovinos está nula.
    """

    query = text(
        f"""
        UPDATE {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE}
        SET {TARGET_COLUMN} = 0
        WHERE {TARGET_COLUMN} IS NULL;
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

    print(f"Iniciando preenchimento de nulos em {TARGET_COLUMN}")
    print(f"Tabela alvo: {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE}")
    print("Critério: preencher valores NULL com 0")

    engine = get_armazem_engine()

    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao Armazém: {info}")

    print("\nValidação antes do update:")
    count_records(engine)
    show_sample_to_update(engine)

    if DRY_RUN:
        print("\nDRY_RUN=True. Nenhuma linha foi atualizada.")
        return

    print("\nExecutando update...")
    linhas_atualizadas = fill_null_quantidade_de_bovinos(engine)

    print(f"Linhas atualizadas: {linhas_atualizadas}")

    print("\nValidação depois do update:")
    count_records(engine)

    fim = time.time()
    print(f"\nJob finalizado em {fim - inicio:.2f} segundos.")


if __name__ == "__main__":
    main()
