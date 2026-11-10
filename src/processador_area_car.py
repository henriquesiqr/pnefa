"""
Módulo responsável por relacionar propriedades com geometrias de área do CAR.
"""

import pandas as pd
import geopandas as gpd


def load_property_car_mapping(csv_path: str) -> pd.DataFrame:
    """
    Lê o CSV de mapeamento entre código da propriedade e código CAR.

    Parameters
    ----------
    csv_path : str
        Caminho do arquivo CSV contendo as colunas de mapeamento.

    Returns
    -------
    pd.DataFrame
        DataFrame com o mapeamento entre propriedade e CAR.
    """
    mapping_df = pd.read_csv(csv_path)

    return mapping_df


def load_car_shapefile(shapefile_path: str) -> gpd.GeoDataFrame:
    """
    Lê o shapefile do CAR.

    Parameters
    ----------
    shapefile_path : str
        Caminho do arquivo .shp.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame contendo os dados geográficos do CAR.
    """
    car_gdf = gpd.read_file(shapefile_path)

    return car_gdf

def extract_area_dataframe(car_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Extrai do GeoDataFrame do CAR apenas as colunas necessárias
    para relacionar o imóvel à sua geometria de área.

    Parameters
    ----------
    car_gdf : gpd.GeoDataFrame
        GeoDataFrame carregado a partir do shapefile do CAR.

    Returns
    -------
    pd.DataFrame
        DataFrame contendo as colunas 'cod_imovel' e 'area'.

    Raises
    ------
    ValueError
        Caso as colunas necessárias não estejam presentes no shapefile.
    """
    required_columns = ["cod_imovel", "geometry"]
    missing_columns = [col for col in required_columns if col not in car_gdf.columns]

    if missing_columns:
        raise ValueError(
            f"As seguintes colunas obrigatórias não foram encontradas no shapefile: {missing_columns}"
        )

    area_df = car_gdf[["cod_imovel", "geometry"]].copy()
    area_df = area_df.rename(columns={"geometry": "area"})

    return area_df

def update_area_from_car(
    df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    area_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Insere a coluna 'area' no DataFrame principal utilizando dados do CAR.
    """
    updated_df = df.copy()

    # 1. Merge com mapping (codigo_local -> car)
    # Traz a coluna 'car' para o df
    updated_df = updated_df.merge(
        mapping_df[['cod_propriedade', 'car']],
        left_on="codigo_local",
        right_on="cod_propriedade",
        how="left"
    )

    # 2. Merge com area_df (car -> cod_imovel)
    # Traz a coluna 'area' calculada do shapefile
    updated_df = updated_df.merge(
        area_df[['cod_imovel', 'area']],
        left_on="car",
        right_on="cod_imovel",
        how="left"
    )

    # 3. Remove as colunas de ligação que sobraram
    updated_df = updated_df.drop(
        columns=["cod_propriedade", "car", "cod_imovel"],
        errors="ignore"
    )

    return updated_df