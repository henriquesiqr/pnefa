from pathlib import Path
from time import perf_counter
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# =============================================================================
# CONFIGURAÇÕES AJUSTÁVEIS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "public"

TABELA_DESTINO = "aftosa_propriedade_exploracao"
TABELA_ORIGEM = "aftosa_gta"

COLUNA_CHAVE = "codigo_da_propriedade"

COLUNA_ESTOQUE_ORIGEM = "estoque_destino"
COLUNA_AREA_ORIGEM_HA = "area_ha"

COLUNA_ESTOQUE_DESTINO = "quantidade_de_bovinos"
COLUNA_AREA_DESTINO_KM2 = "num_area"


# =============================================================================
# CONEXÃO
# =============================================================================

def get_engine():
    load_dotenv(PROJECT_ROOT / "env_armazem.conf")

    database_url = os.getenv("ARMAZEM_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "Variável ARMAZEM_DATABASE_URL não encontrada em env_armazem.conf"
        )

    return create_engine(database_url)


# =============================================================================
# DIAGNÓSTICO
# =============================================================================

def print_status(conn, titulo):
    print(f"\n{titulo}")

    query = text(f"""
        SELECT
            COUNT(*) AS total_linhas,

            COUNT(*) FILTER (
                WHERE {COLUNA_ESTOQUE_DESTINO} IS NOT NULL
            ) AS com_quantidade_de_bovinos,

            COUNT(*) FILTER (
                WHERE {COLUNA_AREA_DESTINO_KM2} IS NOT NULL
            ) AS com_num_area,

            COUNT(*) FILTER (
                WHERE {COLUNA_ESTOQUE_DESTINO} IS NULL
            ) AS sem_quantidade_de_bovinos,

            COUNT(*) FILTER (
                WHERE {COLUNA_AREA_DESTINO_KM2} IS NULL
            ) AS sem_num_area

        FROM {SCHEMA}.{TABELA_DESTINO};
    """)

    result = conn.execute(query).mappings().one()

    print(f"Total: {result['total_linhas']}")
    print(f"Com quantidade_de_bovinos: {result['com_quantidade_de_bovinos']}")
    print(f"Com num_area: {result['com_num_area']}")
    print(f"Sem quantidade_de_bovinos: {result['sem_quantidade_de_bovinos']}")
    print(f"Sem num_area: {result['sem_num_area']}")


def print_origem_status(conn):
    print("\nDados disponíveis em aftosa_gta para atualização:")

    query = text(f"""
        WITH gta_agregado AS (
            SELECT
                CAST({COLUNA_CHAVE} AS TEXT) AS {COLUNA_CHAVE},
                MAX({COLUNA_ESTOQUE_ORIGEM}) AS estoque_destino,
                MAX({COLUNA_AREA_ORIGEM_HA}) AS area_ha
            FROM {SCHEMA}.{TABELA_ORIGEM}
            WHERE {COLUNA_CHAVE} IS NOT NULL
            GROUP BY CAST({COLUNA_CHAVE} AS TEXT)
        )

        SELECT
            COUNT(*) AS propriedades_na_gta,

            COUNT(*) FILTER (
                WHERE estoque_destino IS NOT NULL
            ) AS propriedades_com_estoque,

            COUNT(*) FILTER (
                WHERE area_ha IS NOT NULL
            ) AS propriedades_com_area_ha

        FROM gta_agregado;
    """)

    result = conn.execute(query).mappings().one()

    print(f"Propriedades únicas em aftosa_gta: {result['propriedades_na_gta']}")
    print(f"Com estoque_destino: {result['propriedades_com_estoque']}")
    print(f"Com area_ha: {result['propriedades_com_area_ha']}")


def print_match_status(conn):
    print("\nEstimativa de propriedades que serão atualizadas:")

    query = text(f"""
        WITH gta_agregado AS (
            SELECT
                CAST({COLUNA_CHAVE} AS TEXT) AS {COLUNA_CHAVE},
                MAX({COLUNA_ESTOQUE_ORIGEM}) AS estoque_destino,
                MAX({COLUNA_AREA_ORIGEM_HA}) AS area_ha
            FROM {SCHEMA}.{TABELA_ORIGEM}
            WHERE {COLUNA_CHAVE} IS NOT NULL
            GROUP BY CAST({COLUNA_CHAVE} AS TEXT)
        )

        SELECT
            COUNT(*) AS linhas_destino_com_match,

            COUNT(*) FILTER (
                WHERE gta.estoque_destino IS NOT NULL
            ) AS linhas_com_estoque_para_atualizar,

            COUNT(*) FILTER (
                WHERE gta.area_ha IS NOT NULL
            ) AS linhas_com_area_para_atualizar

        FROM {SCHEMA}.{TABELA_DESTINO} AS ape

        JOIN gta_agregado AS gta
            ON CAST(ape.{COLUNA_CHAVE} AS TEXT) = gta.{COLUNA_CHAVE};
    """)

    result = conn.execute(query).mappings().one()

    print(f"Linhas com match por codigo_da_propriedade: {result['linhas_destino_com_match']}")
    print(f"Linhas com estoque para atualizar: {result['linhas_com_estoque_para_atualizar']}")
    print(f"Linhas com área para atualizar: {result['linhas_com_area_para_atualizar']}")


# =============================================================================
# ATUALIZAÇÃO
# =============================================================================

def update_bovinos_area(conn):
    print("\nAtualizando quantidade_de_bovinos e num_area...")

    query = text(f"""
        WITH gta_agregado AS (
            SELECT
                CAST({COLUNA_CHAVE} AS TEXT) AS {COLUNA_CHAVE},

                MAX({COLUNA_ESTOQUE_ORIGEM}) AS estoque_destino,

                MAX({COLUNA_AREA_ORIGEM_HA}) AS area_ha

            FROM {SCHEMA}.{TABELA_ORIGEM}

            WHERE {COLUNA_CHAVE} IS NOT NULL

            GROUP BY
                CAST({COLUNA_CHAVE} AS TEXT)
        )

        UPDATE {SCHEMA}.{TABELA_DESTINO} AS ape

        SET
            {COLUNA_ESTOQUE_DESTINO} = gta.estoque_destino,

            -- aftosa_gta.area_ha está em hectares.
            -- aftosa_propriedade_exploracao.num_area deve ficar em km².
            -- Conversão: 1 km² = 100 ha.
            {COLUNA_AREA_DESTINO_KM2} = gta.area_ha / 100.0

        FROM gta_agregado AS gta

        WHERE CAST(ape.{COLUNA_CHAVE} AS TEXT) = gta.{COLUNA_CHAVE}
          AND (
                gta.estoque_destino IS NOT NULL
             OR gta.area_ha IS NOT NULL
          );
    """)

    result = conn.execute(query)

    print(f"Linhas atualizadas: {result.rowcount}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    start = perf_counter()

    print("Iniciando atualização de bovinos e área em aftosa_propriedade_exploracao")
    print(f"Tabela destino: {SCHEMA}.{TABELA_DESTINO}")
    print(f"Tabela origem: {SCHEMA}.{TABELA_ORIGEM}")

    engine = get_engine()

    with engine.begin() as conn:
        db_info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao Armazém: {db_info}")

        print_status(conn, "Antes da atualização:")
        print_origem_status(conn)
        print_match_status(conn)

        update_bovinos_area(conn)

        print_status(conn, "Depois da atualização:")

    elapsed = perf_counter() - start

    print(f"\nProcesso concluído em {elapsed:.2f} segundos.")


if __name__ == "__main__":
    main()