"""
preprocessing.py

Funções de preprocessamento dos dados do projeto.
"""

import pandas as pd
import unicodedata
import geopandas as gpd
import numpy as np



def normalize_cpf_cnpj(valor):
    """
    Normaliza CPF/CNPJ:
    - remove .0
    - remove espaços
    - retorna None para vazio
    - padroniza para 11 (CPF) ou 14 (CNPJ) dígitos
    """
    if pd.isna(valor):
        return None

    valor = str(valor).replace(".0", "").strip()

    if valor == "":
        return None

    # mantém só números (opcional mas recomendado)
    valor = "".join(filter(str.isdigit, valor))

    if len(valor) <= 11:
        return valor.zfill(11)

    return valor.zfill(14)



def preprocess_exploracoes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["CPF/CNPJ do Produtor"] = df["CPF/CNPJ do Produtor"].apply(normalize_cpf_cnpj)

    return df



def clean_identifier_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Limpa colunas de identificadores:
    - converte para string
    - remove sufixo .0
    - remove espaços
    """
    df = df.copy()

    for col in columns:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )

    return df



def clean_and_pad_identifier(series: pd.Series, size: int) -> pd.Series:
    """
    Limpa e padroniza identificadores:
    - converte para string
    - remove '.0'
    - remove espaços
    - trata valores nulos
    - preenche com zeros à esquerda
    """
    series = (
        series.astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )

    # trata strings inválidas
    series = series.replace({"nan": None, "": None})

    # aplica padding apenas onde há valor
    return series.where(series.isna(), series.str.zfill(size))



def filtrar_propriedades_com_coordenadas(
    exploracoes_df: pd.DataFrame,
    exploracoes_com_coordenadas_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Mantém apenas as explorações que possuem coordenadas.
    """
    return exploracoes_df[
        exploracoes_df["Código da Propriedade"].isin(
            exploracoes_com_coordenadas_df["Cód. Propriedade"]
        )
    ].copy()



def adicionar_coordenadas(
    exploracoes_df: pd.DataFrame,
    exploracoes_com_coordenadas_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adiciona latitude e longitude às explorações com base no código da propriedade.
    """

    coords = exploracoes_com_coordenadas_df[
        ["Cód. Propriedade", "Latitude", "Longitude"]
    ].drop_duplicates(subset=["Cód. Propriedade"])

    df = exploracoes_df.merge(
        coords,
        left_on="Código da Propriedade",
        right_on="Cód. Propriedade",
        how="left",
    )

    return df.drop(columns="Cód. Propriedade")



def adicionar_ano_atualizacao(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    col = "Data da Atualizacao Cadastral"

    # pega amostra pra detectar formato
    sample = df[col].dropna().astype(str).iloc[0]

    # detecta tipo
    if sample.isdigit() and len(sample) >= 12:
        # timestamp (ms)
        df[col] = pd.to_datetime(df[col], unit="ms", errors="coerce")

    elif "/" in sample:
        # formato brasileiro
        df[col] = pd.to_datetime(df[col], format="%d/%m/%Y", errors="coerce")

    else:
        # YYYYMMDD
        df[col] = pd.to_datetime(df[col].astype(str), format="%Y%m%d", errors="coerce")

    df["ano_atualizacao"] = df[col].dt.year.astype("Int64")

    return df



def filtrar_exploracoes_por_bovinos(
    df,
    limite_inferior: int
):
    """
    Filtra explorações com quantidade de bovinos acima do limite mínimo.
    """
    return df[df["Quantidade de Bovinos"] > limite_inferior].copy()



def filtrar_exploracoes_ativas(
    df: pd.DataFrame,
    coluna_status: str = "Situação da Exploração",
    status_ativo: str = "Ativo",
) -> pd.DataFrame:
    """
    Mantém apenas explorações com situação ativa.
    """
    df = df.copy()

    return df[
        df[coluna_status].astype(str).str.strip() == status_ativo
    ].copy()



def calcular_bovinos_por_propriedade(
    df: pd.DataFrame,
    coluna_propriedade: str = "Código da Propriedade",
    coluna_bovinos: str = "Quantidade de Bovinos",
) -> pd.Series:
    """
    Calcula o total de bovinos por propriedade.
    """
    return (
        df
        .groupby(coluna_propriedade)[coluna_bovinos]
        .sum()
    )



def selecionar_maior_exploracao_por_propriedade(df):
    idx = df.groupby("Código da Propriedade")["Quantidade de Bovinos"].idxmax()
    return df.loc[idx].copy()



def adicionar_total_bovinos(
    df: pd.DataFrame,
    base_exploracoes: pd.DataFrame,
    coluna_propriedade: str = "Código da Propriedade",
    coluna_bovinos: str = "Quantidade de Bovinos",
) -> pd.DataFrame:
    """
    Adiciona coluna de total de bovinos por propriedade.
    """
    df = df.copy()

    totais = (
        base_exploracoes
        .groupby(coluna_propriedade)[coluna_bovinos]
        .sum()
    )

    df["Total de Bovinos"] = df[coluna_propriedade].map(totais)

    return df



def inicializar_propriedades_por_esec(esec_to_mun: dict) -> dict:
    """
    Cria um dicionário com todas as ESECs inicializadas com 0 propriedades.
    """
    return {esec: 0 for esec in esec_to_mun.keys()}



def contar_propriedades_por_esec(
    propriedades_df: pd.DataFrame,
    codigo_municipio_para_esec: dict
) -> dict:
    """
    Conta quantas propriedades existem por ESEC.

    - garante que o código do município está como string
    - usa o mapping município → ESEC
    - retorna dict {ESEC: quantidade}
    """

    # garantir chave como string
    codigo_municipio_para_esec = {
        str(k): v for k, v in codigo_municipio_para_esec.items()
    }

    # inicializa com zero
    propriedades_por_esec = {
        esec: 0 for esec in set(codigo_municipio_para_esec.values())
    }

    # loop (mantendo sua lógica)
    for _, row in propriedades_df.iterrows():
        codigo_municipio = str(row["Código do Município"]).strip()

        nome_esec = codigo_municipio_para_esec.get(codigo_municipio)

        if nome_esec:
            propriedades_por_esec[nome_esec] += 1

    return propriedades_por_esec



def adicionar_esec_e_coordenadoria(
    df: pd.DataFrame,
    codigo_municipio_para_esec: dict,
    esec_para_coordenadoria: dict,
) -> pd.DataFrame:
    """
    Adiciona colunas de ESEC e Coordenadoria com base no código do município.
    """

    df = df.copy()

    # garantir chave como string
    codigo_municipio_para_esec = {
        str(k): v for k, v in codigo_municipio_para_esec.items()
    }

    df["ESEC"] = (
        df["Código do Município"]
        .astype(str)
        .str.strip()
        .map(codigo_municipio_para_esec)
    )

    df["Coordenadoria"] = (
        df["ESEC"]
        .map(esec_para_coordenadoria)
    )

    return df



def gerar_propriedades_por_esec_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera DataFrame com quantidade de propriedades por ESEC.
    """

    df_out = (
        df.groupby("ESEC")
        .size()
        .reset_index(name="Quantidade de Propriedades")
        .sort_values(by="Quantidade de Propriedades", ascending=False)
        .reset_index(drop=True)
    )

    return df_out



def padronizar_nomes_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    def normalize(col):
        col = col.lower().replace(' ', '_')
        col = unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8')
        return col

    df.columns = [normalize(c) for c in df.columns]

    return df



def selecionar_colunas_area_imovel(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Mantém apenas as colunas relevantes do shapefile de imóveis.
    """
    return gdf[["cod_imovel", "geometry", "num_area"]].copy()



def adicionar_geometria_imovel(
    df: pd.DataFrame,
    propriedades_car_df: pd.DataFrame,
    gdf_area_imovel,
) -> pd.DataFrame:
    """
    Enriquece o DataFrame de propriedades com:
    1. Código CAR via mapping propriedade → CAR
    2. Geometria e área via shapefile
    """

    df = df.copy()
    propriedades_car_df = propriedades_car_df.copy()
    gdf_area_imovel = gdf_area_imovel.copy()

    df["codigo_da_propriedade"] = (
        df["codigo_da_propriedade"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .str.zfill(11)
    )

    propriedades_car_df["cod_propriedade"] = (
        propriedades_car_df["cod_propriedade"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .str.zfill(11)
    )

    propriedades_car_df["car"] = (
        propriedades_car_df["car"]
        .astype(str)
        .str.strip()
    )

    gdf_area_imovel["cod_imovel"] = (
        gdf_area_imovel["cod_imovel"]
        .astype(str)
        .str.strip()
    )

    df_merged = df.merge(
        propriedades_car_df,
        left_on="codigo_da_propriedade",
        right_on="cod_propriedade",
        how="left",
    )

    df_final = df_merged.merge(
        gdf_area_imovel,
        left_on="car",
        right_on="cod_imovel",
        how="left",
    )

    return df_final



def preencher_area_pela_mediana_municipio(
    df: pd.DataFrame,
    coluna_municipio: str = "codigo_do_municipio",
    coluna_area: str = "num_area",
) -> pd.DataFrame:
    """
    Preenche valores ausentes de área usando a mediana da área
    das propriedades do mesmo município.
    """
    df = df.copy()

    medianas_por_municipio = df.groupby(coluna_municipio)[coluna_area].transform("median")

    df[coluna_area] = df[coluna_area].fillna(medianas_por_municipio)

    return df



def remover_colunas_auxiliares_geometria(
    df: pd.DataFrame,
    colunas: list[str] = ["cod_propriedade", "car", "cod_imovel"],
) -> pd.DataFrame:
    """
    Remove colunas auxiliares geradas durante o processo de merge geoespacial.
    """
    df = df.copy()

    return df.drop(columns=colunas, errors="ignore")



def calcular_densidade_bovinos(
    df: pd.DataFrame,
    coluna_bovinos: str = "total_de_bovinos",
    coluna_area: str = "num_area",
    coluna_saida: str = "densidade_bovinos",
) -> pd.DataFrame:
    """
    Calcula a densidade de bovinos (bovinos por área),
    tratando divisão por zero e valores infinitos.
    """

    df = df.copy()

    df[coluna_saida] = df[coluna_bovinos] / df[coluna_area]

    df[coluna_saida] = df[coluna_saida].replace(
        [np.inf, -np.inf],
        np.nan
    )

    return df



def parse_data_atualizacao(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "data_da_atualizacao_cadastral" in df.columns:
        df["data_da_atualizacao_cadastral"] = pd.to_datetime(
            df["data_da_atualizacao_cadastral"],
            errors="coerce",
        )

    return df



def converter_lat_lon_eventos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte colunas LATITUDE e LONGITUDE de string (com vírgula)
    para float.
    """

    df = df.copy()

    for col in ["LATITUDE", "LONGITUDE"]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", ".", regex=False)
        )

        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df