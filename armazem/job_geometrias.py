from pathlib import Path
import sys
import time

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

QUERY_UPDATE_GEOMETRIA_PATH = (
    ARMAZEM_DIR
    / "geometria.sql"
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
        raise ValueError("ARMAZEM_DATABASE_URL não encontrada no env_armazem.conf")

    return create_engine(database_url)


# =============================================================================
# QUERY
# =============================================================================

def load_update_geometria_query() -> str:
    """
    Carrega a query de atualização de geometria.
    """

    if not QUERY_UPDATE_GEOMETRIA_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo SQL não encontrado: {QUERY_UPDATE_GEOMETRIA_PATH}"
        )

    return QUERY_UPDATE_GEOMETRIA_PATH.read_text(encoding="utf-8")


# =============================================================================
# VALIDAÇÕES
# =============================================================================

def show_before_update(engine) -> None:
    """
    Exibe o estado da tabela antes da atualização.
    """

    query = text(
        f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE geometry IS NOT NULL) AS com_geometry,
            COUNT(*) FILTER (
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ) AS com_lat_long,
            COUNT(*) FILTER (WHERE geometry IS NULL) AS sem_geometry
        FROM {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE};
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    print("\nAntes da atualização:")
    print(f"Total: {result.total}")
    print(f"Com geometry: {result.com_geometry}")
    print(f"Com latitude/longitude: {result.com_lat_long}")
    print(f"Sem geometry: {result.sem_geometry}")


def show_available_geometries(engine) -> None:
    """
    Exibe quantas linhas possuem geometria disponível via locais/geometrias.
    """

    query = text(
        f"""
        SELECT COUNT(*) AS total_com_geometria_disponivel
        FROM {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE} ape
        INNER JOIN {ARMAZEM_SCHEMA}.locais l
            ON l.codigo = ape.codigo_da_propriedade
        INNER JOIN {ARMAZEM_SCHEMA}.geometrias g
            ON g.id = l.id_geometria
        WHERE g.geom IS NOT NULL;
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    print(
        "Linhas com geometria disponível via locais/geometrias: "
        f"{result.total_com_geometria_disponivel}"
    )


def show_estimated_geometry_size(engine) -> None:
    """
    Estima o tamanho dos multipolígonos que serão usados.
    """

    query = text(
        f"""
        SELECT
            COUNT(*) AS total_linhas,
            pg_size_pretty(SUM(pg_column_size(g.geom))::bigint) AS tamanho_estimado,
            pg_size_pretty(AVG(pg_column_size(g.geom))::bigint) AS media_por_linha,
            pg_size_pretty(MAX(pg_column_size(g.geom))::bigint) AS maior_geometria
        FROM {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE} ape
        INNER JOIN {ARMAZEM_SCHEMA}.locais l
            ON l.codigo = ape.codigo_da_propriedade
        INNER JOIN {ARMAZEM_SCHEMA}.geometrias g
            ON g.id = l.id_geometria
        WHERE g.geom IS NOT NULL;
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    print("\nEstimativa de espaço caso copie os multipolígonos:")
    print(f"Total de linhas: {result.total_linhas}")
    print(f"Tamanho estimado: {result.tamanho_estimado}")
    print(f"Média por linha: {result.media_por_linha}")
    print(f"Maior geometria: {result.maior_geometria}")


def show_after_update(engine) -> None:
    """
    Exibe o estado da tabela depois da atualização.
    """

    query = text(
        f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE geometry IS NOT NULL) AS com_geometry,
            COUNT(*) FILTER (
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ) AS com_lat_long,
            COUNT(*) FILTER (WHERE geometry IS NULL) AS sem_geometry
        FROM {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE};
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    print("\nDepois da atualização:")
    print(f"Total: {result.total}")
    print(f"Com geometry: {result.com_geometry}")
    print(f"Com latitude/longitude: {result.com_lat_long}")
    print(f"Sem geometry: {result.sem_geometry}")


# =============================================================================
# ATUALIZAÇÃO
# =============================================================================

def update_geometria(engine) -> None:
    """
    Executa a query que atualiza geometry, latitude e longitude.
    """

    update_sql = load_update_geometria_query()

    with engine.begin() as conn:
        result = conn.execute(text(update_sql))

    print(
        f"\nLinhas atualizadas em {ARMAZEM_SCHEMA}.{ARMAZEM_TABLE}: "
        f"{result.rowcount}"
    )


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main():
    inicio = time.time()

    print("Iniciando atualização de geometria em aftosa_propriedade_exploracao")

    engine = get_armazem_engine()

    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao Armazém: {info}")

    show_before_update(engine)
    show_available_geometries(engine)
    show_estimated_geometry_size(engine)

    print("\nExecutando atualização de geometry, latitude e longitude...")
    update_geometria(engine)

    show_after_update(engine)

    fim = time.time()
    print(f"\nJob finalizado em {fim - inicio:.2f} segundos.")


if __name__ == "__main__":
    main()