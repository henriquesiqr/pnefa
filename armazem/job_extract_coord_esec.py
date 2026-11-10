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

TABELA_PROPRIEDADE_EXPLORACAO = "aftosa_propriedade_exploracao"
TABELA_SECCIONAIS = "seccionais"
TABELA_COORDENADORIAS = "coordenadorias"

SQL_COORD_ESEC_PATH = (
    ARMAZEM_DIR
    / "coord_esec.sql"
)

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
# LEITURA DA QUERY
# =============================================================================

def load_sql_query(sql_path: Path) -> str:
    """
    Carrega uma query SQL a partir de um arquivo.
    """

    if not sql_path.exists():
        raise FileNotFoundError(f"Arquivo SQL não encontrado: {sql_path}")

    return sql_path.read_text(encoding="utf-8")


# =============================================================================
# VALIDAÇÃO ANTES DO UPDATE
# =============================================================================

def validate_before_update(engine) -> None:
    """
    Valida quantas linhas encontram seccional e coordenadoria antes do update.
    """

    query = text(
        f"""
        SELECT
            COUNT(*) AS total_linhas,
            COUNT(s.id) AS linhas_com_seccional,
            COUNT(c.id) AS linhas_com_coordenadoria
        FROM {ARMAZEM_SCHEMA}.{TABELA_PROPRIEDADE_EXPLORACAO} ape
        LEFT JOIN {ARMAZEM_SCHEMA}.{TABELA_SECCIONAIS} s
            ON ape.codigo_do_municipio::text = s.id_municipio::text
        LEFT JOIN {ARMAZEM_SCHEMA}.{TABELA_COORDENADORIAS} c
            ON c.id = s.id_coordenadoria;
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    print("Validação antes do update:")
    print(f"Total de linhas: {result.total_linhas}")
    print(f"Linhas com seccional encontrada: {result.linhas_com_seccional}")
    print(f"Linhas com coordenadoria encontrada: {result.linhas_com_coordenadoria}")


def show_unmatched_municipios(engine) -> None:
    """
    Mostra municípios sem correspondência na tabela de seccionais.
    """

    query = text(
        f"""
        SELECT
            ape.codigo_do_municipio,
            ape.descricao_do_municipio,
            COUNT(*) AS total_linhas
        FROM {ARMAZEM_SCHEMA}.{TABELA_PROPRIEDADE_EXPLORACAO} ape
        LEFT JOIN {ARMAZEM_SCHEMA}.{TABELA_SECCIONAIS} s
            ON ape.codigo_do_municipio::text = s.id_municipio::text
        WHERE s.id IS NULL
        GROUP BY
            ape.codigo_do_municipio,
            ape.descricao_do_municipio
        ORDER BY total_linhas DESC
        LIMIT 30;
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    if not rows:
        print("\nTodos os municípios encontraram seccional.")
        return

    print("\nMunicípios sem correspondência em seccionais:")
    for row in rows:
        print(
            f"{row.codigo_do_municipio} | "
            f"{row.descricao_do_municipio} | "
            f"{row.total_linhas} linhas"
        )


# =============================================================================
# UPDATE
# =============================================================================

def update_coord_esec(engine) -> int:
    """
    Atualiza seccional e coordenadoria na tabela aftosa_propriedade_exploracao.
    """

    sql = load_sql_query(SQL_COORD_ESEC_PATH)
    query = text(sql)

    with engine.begin() as conn:
        result = conn.execute(query)

    return result.rowcount


# =============================================================================
# VALIDAÇÃO DEPOIS DO UPDATE
# =============================================================================

def validate_after_update(engine) -> None:
    """
    Valida preenchimento final de seccional e coordenadoria.
    """

    query = text(
        f"""
        SELECT
            COUNT(*) AS total_linhas,
            COUNT(seccional) AS seccional_preenchida,
            COUNT(coordenadoria) AS coordenadoria_preenchida,
            COUNT(*) FILTER (
                WHERE seccional IS NULL OR TRIM(seccional) = ''
            ) AS seccional_vazia,
            COUNT(*) FILTER (
                WHERE coordenadoria IS NULL OR TRIM(coordenadoria) = ''
            ) AS coordenadoria_vazia
        FROM {ARMAZEM_SCHEMA}.{TABELA_PROPRIEDADE_EXPLORACAO};
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

    print("\nValidação depois do update:")
    print(f"Total de linhas: {result.total_linhas}")
    print(f"Seccional preenchida: {result.seccional_preenchida}")
    print(f"Coordenadoria preenchida: {result.coordenadoria_preenchida}")
    print(f"Seccional vazia: {result.seccional_vazia}")
    print(f"Coordenadoria vazia: {result.coordenadoria_vazia}")


def show_sample(engine) -> None:
    """
    Mostra amostra dos registros atualizados.
    """

    query = text(
        f"""
        SELECT
            codigo_do_municipio,
            descricao_do_municipio,
            seccional,
            coordenadoria
        FROM {ARMAZEM_SCHEMA}.{TABELA_PROPRIEDADE_EXPLORACAO}
        WHERE seccional IS NOT NULL
          AND TRIM(seccional) <> ''
          AND coordenadoria IS NOT NULL
          AND TRIM(coordenadoria) <> ''
        LIMIT 10;
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    print("\nAmostra atualizada:")
    for row in rows:
        print(
            f"{row.codigo_do_municipio} | "
            f"{row.descricao_do_municipio} | "
            f"{row.seccional} | "
            f"{row.coordenadoria}"
        )


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main():
    inicio = time.time()

    print("Iniciando atualização de coordenadoria e seccional")

    engine = get_armazem_engine()

    with engine.connect() as conn:
        info = conn.execute(
            text("SELECT current_database(), current_user, current_schema();")
        ).fetchone()

        print(f"Conectado ao Armazém: {info}")

    validate_before_update(engine)
    show_unmatched_municipios(engine)

    if DRY_RUN:
        print("\nDRY_RUN=True. Nenhum update foi executado.")
        return

    print("\nExecutando update via arquivo SQL...")
    linhas_atualizadas = update_coord_esec(engine)

    print(f"Linhas atualizadas: {linhas_atualizadas}")

    validate_after_update(engine)
    show_sample(engine)

    fim = time.time()
    print(f"\nAtualização finalizada em {fim - inicio:.2f} segundos.")


if __name__ == "__main__":
    main()