##
"""
data_io.py

Funções de entrada e saída de dados do projeto.
"""

from pathlib import Path
import pandas as pd
import json
import geopandas as gpd
from datetime import datetime

# =========================
# PATHS DO PROJETO
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / 'processed'
RESULTS_DIR = PROJECT_ROOT / 'results'
QUERIES_RESULTS_DIR = RESULTS_DIR / "queries"

# =========================
# FUNÇÕES AUXILIARES
# =========================

def ensure_exists(path: str | Path) -> Path:
    """
    Garante que o caminho (arquivo ou diretório) exista.
    Retorna o Path normalizado.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Caminho não encontrado: {path}")

    return path


def ensure_parent_dir(path: str | Path) -> Path:
    """
    Garante que o diretório pai exista antes de salvar um arquivo.
    Retorna o Path normalizado.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\n", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
    )
    return df

def strip_string_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()

    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


def cast_columns_to_str(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Converte colunas existentes para string e aplica strip.
    Ignora colunas que não existirem.
    """
    df = df.copy()

    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


# =========================
# LEITURA GENÉRICA
# =========================

def read_table(
    path: str | Path,
    dtype_map: dict | None = None,
    sep: str = ",",
    skiprows: int | None = None,
    encoding: str | None = None,
) -> pd.DataFrame:
    import pandas as pd
    from pathlib import Path
    """
    Lê arquivos CSV, Excel ou JSON com tratamento padrão do projeto.
    """

    path = ensure_exists(path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(
            path,
            dtype=dtype_map,
            sep=sep,
            skiprows=skiprows,
            encoding=encoding,
        )

    elif suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(
            path,
            dtype=dtype_map,
        )

    elif suffix == ".json":
        with open(path, "r", encoding=encoding or "utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)

        if dtype_map:
            for col, dtype in dtype_map.items():
                if col in df.columns:
                    df[col] = df[col].astype(dtype)

    else:
        raise ValueError(f"Formato de arquivo não suportado: {suffix}")

    # Padroniza nomes de colunas
    df = standardize_columns(df)

    return df


def read_text_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")

# =========================
# LEITURA DE RAW DATA
# =========================

def load_exploracao_pecuaria_raw():
    path = RAW_DIR / "Extracao_17_10_2025_Dados_Exploracao_Pecuaria.json"

    dtype_map = {
        # coloque aqui as colunas-chave que devem ser string
        "Código do Município": str,
        "Código da Propriedade": str,
        "Código da Exploracao": str,
        "CPF/CNPJ do Produtor": str,
        "Código da Exploracao": str,
    }

    df = read_table(path, dtype_map=dtype_map)
    return df


def load_exploracoes_com_coordenadas() -> pd.DataFrame:
    """
    Carrega base de propriedades com coordenadas dentro de MG.
    """

    path = RAW_DIR / "PROPRIEDADES_IMA_COM_COORDENADAS_DENTRO_MG.csv"

    dtype_map = {
        "Cód. Município": str,
        "Cód. Propriedade": str,
        "CPF/CNPJ do Proprietário": str,
    }

    df = read_table(path, dtype_map=dtype_map)

    return df


def load_propriedades_consideradas_final() -> pd.DataFrame:
    path = PROCESSED_DIR / "Propriedades_consideradas_FINAL.csv"

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    return pd.read_csv(path)



def load_coordenadorias_dict(raw_dir: Path) -> dict[str, pd.DataFrame]:
    coordenadorias_dir = raw_dir / "coordenadorias"

    arquivos = list(coordenadorias_dir.glob("*.csv"))

    if not arquivos:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {coordenadorias_dir}")

    dtype_map = {
        "codigo_do_municipio": str,
        "codigo_da_propriedade": str,
        "codigo_da_exploracao": str,
        "cpf/cnpj_do_produtor": str,
    }

    return {
        arq.stem: pd.read_csv(arq, sep=",", dtype=dtype_map)
        for arq in arquivos
    }


def read_coordenadoria_csv(path: Path) -> pd.DataFrame:
    dtype_map = {
        "codigo_do_municipio": str,
        "codigo_da_propriedade": str,
        "codigo_da_exploracao": str,
        "cpf/cnpj_do_produtor": str,
    }

    return pd.read_csv(path, sep=",", dtype=dtype_map)



def build_coordenadoria_mappings(
    coordenadorias_dict: dict[str, pd.DataFrame]
) -> tuple[dict, dict]:
    """
    Cria:
    - coordenadoria -> lista de ESECs
    - ESEC -> coordenadoria
    """

    coordenadoria_para_esecs = {}
    esec_para_coordenadoria = {}

    for nome, df in coordenadorias_dict.items():
        esecs = df["ESEC"].dropna().unique().tolist()

        coordenadoria_para_esecs[nome] = esecs

        for esec in esecs:
            esec_para_coordenadoria[esec] = nome

    return coordenadoria_para_esecs, esec_para_coordenadoria



def build_esec_municipio_mappings(
    coordenadorias_dict: dict[str, pd.DataFrame]
) -> tuple[dict, dict]:
    """
    Cria:
    - ESEC -> lista de códigos de município
    - código de município -> ESEC
    """

    esec_para_codigo_municipio = {}
    codigo_municipio_para_esec = {}

    for nome, df in coordenadorias_dict.items():

        # garantir limpeza básica
        df = df.copy()
        df["ESEC"] = df["ESEC"].astype(str).str.strip()
        df["CD_MUN"] = df["CD_MUN"].astype(str).str.strip()

        # ESEC → municípios
        agrupado = df.groupby("ESEC")["CD_MUN"].unique()

        for esec, codigos in agrupado.items():
            esec_para_codigo_municipio[esec] = codigos.tolist()

        # município → ESEC
        codigo_municipio_para_esec.update(dict(zip(df["CD_MUN"], df["ESEC"])))

    return esec_para_codigo_municipio, codigo_municipio_para_esec



def load_area_imovel(raw_dir: Path, filename: str = "AREA_IMOVEL_1.shp") -> gpd.GeoDataFrame:
    """
    Carrega o shapefile de área de imóveis a partir de data/raw.

    Parâmetros:
    - raw_dir: diretório base de dados brutos
    - filename: nome do shapefile (.shp)

    Retorna:
    - GeoDataFrame com os dados carregados
    """

    shapefile_path = raw_dir / filename

    if not shapefile_path.exists():
        raise FileNotFoundError(f"Shapefile não encontrado em: {shapefile_path}")

    gdf = gpd.read_file(shapefile_path)

    return gdf



def load_propriedade_car(raw_dir: Path, filename: str = "propriedade_car_2025_reconstructed.csv") -> pd.DataFrame:
    """
    Carrega o arquivo de correspondência propriedade ↔ CAR.
    """

    path = raw_dir / filename

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado em: {path}")

    df = pd.read_csv(path)

    return df



def load_portaria_estrutura_territorial_ima(
    path: str | Path = RAW_DIR / "Portaria 2438_12 fevereiro 2026_estrutura_territorial_IMA.xlsx",
) -> pd.DataFrame:
    """
    Lê a planilha da Portaria 2438/2026 com a estrutura territorial do IMA,
    garantindo tipos corretos para colunas-chave.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    df = pd.read_excel(
        path,
        dtype={
            "Nº": str,
            "IBGE": str,
        },
        engine="openpyxl",
    )

    return df



def load_relatorio_suinos(raw_dir: Path) -> pd.DataFrame:
    """
    Carrega o relatório de suínos.
    """

    path = raw_dir / "03_suinos" / "relatorio_suinos.xlsx"

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    dtype_map = {
        "Cod. Propriedade": str,
        "Cod. Municipio": str,
        "Cod. Produtor": str,
    }

    df = pd.read_excel(path, dtype=dtype_map)

    return df



def load_lixoes(raw_dir: Path) -> pd.DataFrame:
    """
    Carrega e padroniza base de lixões por município.
    """

    path = raw_dir / "04_lixoes" / "lixoes_municipio_MG_v2.csv"

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    df = pd.read_csv(path)

    # ------------------------------------------------------
    # Padronizar nome da coluna de município
    # ------------------------------------------------------
    rename_map = {
        "Cod. Municipio": "codigo_do_municipio",
        "CD_MUN": "codigo_do_municipio",
        "cod_ibge": "codigo_do_municipio",
    }

    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # ------------------------------------------------------
    # Garantir tipo consistente
    # ------------------------------------------------------
    if "codigo_do_municipio" not in df.columns:
        raise KeyError("Coluna de município não encontrada no dataset de lixões")

    df["codigo_do_municipio"] = (
        df["codigo_do_municipio"]
        .astype(str)
        .str.strip()
    )

    return df



def load_eventos(raw_dir: Path) -> pd.DataFrame:
    path = raw_dir / "05_eventos" / "ESTABELECIMENTOS_EVENTOS_2025.csv"

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    return pd.read_csv(path)



def load_gta_csv(
    raw_dir: Path,
    filename: str,
    dtype_col: str,
    sep: str = ";",
) -> pd.DataFrame:
    """
    Carrega um CSV de GTA e padroniza a coluna-chave informada.
    """

    path = raw_dir / "01_gta" / filename

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    df = pd.read_csv(
        path,
        sep=sep,
        dtype={dtype_col: str},
    )

    df[dtype_col] = (
        df[dtype_col]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )

    return df



def load_gtas_entrada_origem_qualquer_MG_destino_prop_MG(
    raw_dir: Path,
) -> pd.DataFrame:
    return load_gta_csv(
        raw_dir=raw_dir,
        filename="gtas_entrada_origem_qualquer_MG_destino_prop_MG_20251127.csv",
        dtype_col="cod_propriedade_destino",
    )


def load_gtas_entrada_origem_qualquer_OE_destino_prop_MG(
    raw_dir: Path,
) -> pd.DataFrame:
    return load_gta_csv(
        raw_dir=raw_dir,
        filename="gtas_entrada_origem_qualquer_OE_destino_prop_MG_20251128.csv",
        dtype_col="cod_propriedade_destino",
    )


def load_gtas_saida_origem_prop_MG_destino_qualquer(
    raw_dir: Path,
) -> pd.DataFrame:
    return load_gta_csv(
        raw_dir=raw_dir,
        filename="gtas_saida_origem_prop_MG_destino_qualquer_20251128.csv",
        dtype_col="cod_propriedade_origem",
    )


# =========================
# LEITURA DE INTERIM DATA
# =========================

def load_propriedades_consideradas_interim(
    path: str | Path = INTERIM_DIR / "propriedades_consideradas_interim.csv",
) -> pd.DataFrame:
    """
    Lê o arquivo intermediário de propriedades consideradas,
    garantindo tipos corretos para chaves.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    dtype_map = {
        "codigo_do_municipio": str,
        "codigo_da_propriedade": str,
        "cpf/cnpj_do_produtor": str,
        "codigo_da_exploracao": str,
    }

    df = pd.read_csv(path, dtype=dtype_map)

    return df



# =========================
# LEITURA DE PROCESSED DATA
# =========================

def load_propriedades_processed(
    path: str | Path = PROCESSED_DIR / "propriedades_processed.csv",
) -> pd.DataFrame:
    """
    Lê o arquivo propriedades_processed.csv garantindo tipos corretos
    para colunas-chave.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    dtype_map = {
        "codigo_do_municipio": str,
        "codigo_da_propriedade": str,
        "cpf/cnpj_do_produtor": str,
    }

    df = pd.read_csv(
        path,
        dtype=dtype_map,
    )

    # Sanitização leve (caso algum .0 tenha escapado)
    for col in dtype_map.keys():
        if col in df.columns:
            df[col] = df[col].str.replace(".0", "", regex=False)

    return df



def salvar_propriedades_por_esec(
    df: pd.DataFrame,
    processed_dir: Path,
    filename_prefix: str = "propriedades_por_esec",
) -> Path:
    """
    Salva o DataFrame de propriedades por ESEC em processed com timestamp.
    """
    processed_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"

    path = processed_dir / filename
    df.to_csv(path, index=False)

    return path


DATA_SOURCE_CSV = "csv"
DATA_SOURCE_ARMAZEM = "armazem"

def load_propriedades_risco_sanitario(
    processed_dir: Path = PROCESSED_DIR,
    source: str = DATA_SOURCE_CSV,
) -> pd.DataFrame:
    """
    Carrega o dataframe consolidado de propriedades com riscos sanitários.
    """

    if source == DATA_SOURCE_CSV:
        path = processed_dir / "propriedades_risco_sanitario.csv"

        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        return pd.read_csv(
            path,
            dtype={
                "codigo_do_municipio": str,
                "codigo_da_propriedade": str,
                "codigo_da_exploracao": str,
                "cpf/cnpj_do_produtor": str,
            },
        )

    if source == DATA_SOURCE_ARMAZEM:
        from src.armazem_io import load_propriedades_risco_sanitario_from_armazem

        return load_propriedades_risco_sanitario_from_armazem()

    raise ValueError(
        f"Fonte de dados inválida: {source}. "
        f"Use '{DATA_SOURCE_CSV}' ou '{DATA_SOURCE_ARMAZEM}'."
    )


# =========================
# ESCRITA
# =========================
from datetime import datetime


def salvar_propriedades_por_esec(df: pd.DataFrame, results_dir: Path) -> Path:
    """it push --set-upstream origin refactor/run_sim
    Salva o DataFrame de propriedades por ESEC em CSV com timestamp.
    """

    # 🔥 cria a pasta se não existir
    results_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"propriedades_por_esec_{timestamp}.csv"

    path = results_dir / filename

    df.to_csv(path, index=False)

    return path



def save_csv(
    df: pd.DataFrame,
    path: str | Path,
    index: bool = False,
    encoding: str = "utf-8-sig",
    ) -> None:
    path = Path(path)
    ensure_parent_dir(path)
    df.to_csv(path, index=index, encoding=encoding)



def salvar_df_final_interim(
    df: pd.DataFrame,
    interim_dir: Path,
    filename: str = "propriedades_com_geometria_interim.csv",
) -> Path:
    """
    Salva o DataFrame final enriquecido com geometria na pasta interim.
    """

    interim_dir.mkdir(parents=True, exist_ok=True)

    path = interim_dir / filename

    df.to_csv(path, index=False)

    return path



def salvar_propriedades_processed(
    df: pd.DataFrame,
    processed_dir: Path,
    filename: str = "propriedades_processed.csv",
) -> Path:
    processed_dir.mkdir(parents=True, exist_ok=True)

    path = processed_dir / filename

    df.to_csv(path, index=False)

    return path



def save_propriedades_risco_sanitario(
    propriedades_df: pd.DataFrame,
    processed_dir: Path,
    filename: str = "propriedades_risco_sanitario.csv",
) -> Path:
    """
    Salva o dataframe consolidado de risco sanitário.
    """

    output_path = processed_dir / filename

    propriedades_df.to_csv(
        output_path,
        index=False,
    )

    return output_path




def save_json(data: dict, path: str | Path) -> None:
    path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)