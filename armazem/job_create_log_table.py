from pathlib import Path
import sys
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# =============================================================================
# CONFIGURAÇÃO DE PATH
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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
ARMAZEM_TABLE = "aftosa_logs_execucao"

QUERY_CREATE_LOGS_PATH = (
    PROJECT_ROOT
    / "armazem"
    / "create_log_table.sql"
)


# =============================================================================
# CONEXÃO
# =============================================================================

def get_armazem_engine():
    """
    Cria engine SQLAlchemy para o Armazém ima-dev.
    """

    import os

    database_url = os.getenv("ARMAZEM_DATABASE_URL")

    if not database_url:
        raise ValueError("ARMAZEM_DATABASE_URL não encontrada no env.properties")

    return create_engine(database_url)


# =============================================================================
# QUERY
# =============================================================================

def load_create_logs_query() -> str:
    """
    Carrega a query de criação da tabela de logs a partir do arquivo .sql.
    """

    if not QUERY_CREATE_LOGS_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de query não encontrado: {QUERY_CREATE_LOGS_PATH}"
        )

    return QUERY_CREATE_LOGS_PATH.read_text(encoding="utf-8")


# =============================================================================
# EXECUÇÃO DA QUERY
# =============================================================================

def create_logs_table() -> None:
    """
    Executa a query de criação da tabela de logs no Armazém.
    """

    engine = get_armazem_engine()
    query = load_create_logs_query()

    with engine.begin() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao Armazém: {info}")

        conn.execute(text(query))

    print(f"Tabela {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE} criada/verificada com sucesso.")


def validate_table() -> None:
    """
    Valida se a tabela existe no Armazém.
    """

    engine = get_armazem_engine()

    query = text(
        """
        SELECT
            table_schema,
            table_name
        FROM information_schema.tables
        WHERE table_schema = :schema
          AND table_name = :table;
        """
    )

    with engine.connect() as conn:
        result = conn.execute(
            query,
            {
                "schema": ARMAZEM_SCHEMA,
                "table": ARMAZEM_TABLE,
            },
        ).fetchone()

    if not result:
        raise ValueError(
            f"Tabela {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE} não encontrada após execução."
        )

    print(f"Validação concluída: {result.table_schema}.{result.table_name}")


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main():
    inicio = time.time()

    print("Iniciando criação da tabela de logs de execução de cenário")

    create_logs_table()
    validate_table()

    fim = time.time()
    print(f"Job finalizado em {fim - inicio:.2f} segundos.")


if __name__ == "__main__":
    main()