import pandas as pd
import numpy as np
from typing import Dict, Tuple
import re
from sklearn.metrics.pairwise import haversine_distances




def calcular_qtd_esecs_por_coordenadoria(
    coord_to_esec: dict[str, list]
) -> tuple[dict[str, int], int]:
    """
    Calcula:
    - quantidade de ESECs por coordenadoria
    - total de ESECs no sistema
    """

    qtd_esecs_por_coordenadoria = {
        coord: len(esecs)
        for coord, esecs in coord_to_esec.items()
    }

    total_esecs = sum(qtd_esecs_por_coordenadoria.values())

    return qtd_esecs_por_coordenadoria, total_esecs


def calcular_propriedades_por_esec(
    propriedades_df: pd.DataFrame,
    municipio_to_esec: dict,
) -> dict[str, int]:

    df = propriedades_df.copy()

    df["esec"] = df["codigo_do_municipio"].map(municipio_to_esec)

    counts = df["esec"].value_counts()

    return {
        esec: int(counts.get(esec, 0))
        for esec in municipio_to_esec.values()
    }



def build_esec_municipio_mappings(
    coordenadorias_dict: dict[str, pd.DataFrame],
) -> tuple[dict[str, list], dict[str, str], int]:
    """
    Cria:
    - esec_to_municipios: ESEC → lista de municípios
    - municipio_to_esec: município → ESEC
    - total_municipios: total de municípios únicos
    """

    import pandas as pd

    # ------------------------------------------------------
    # 1. Concatenar tudo
    # ------------------------------------------------------
    df = pd.concat(coordenadorias_dict.values(), ignore_index=True)

    # garantir tipos
    df["CD_MUN"] = df["CD_MUN"].astype(str).str.strip()
    df["ESEC"] = df["ESEC"].astype(str).str.strip()

    # ------------------------------------------------------
    # 2. ESEC → municípios
    # ------------------------------------------------------
    esec_to_municipios = (
        df.groupby("ESEC")["CD_MUN"]
        .apply(lambda x: sorted(set(x)))
        .to_dict()
    )

    # ------------------------------------------------------
    # 3. município → ESEC
    # ------------------------------------------------------
    municipio_to_esec = dict(zip(df["CD_MUN"], df["ESEC"]))

    # ------------------------------------------------------
    # 4. total de municípios únicos
    # ------------------------------------------------------
    total_municipios = df["CD_MUN"].nunique()

    return esec_to_municipios, municipio_to_esec, total_municipios



def normalizar_chaves_municipio(
    municipio_to_esec: dict
) -> dict[str, str]:
    """
    Garante que as chaves (códigos de município) sejam strings limpas.
    """

    return {
        str(k).strip(): v
        for k, v in municipio_to_esec.items()
    }



def construir_df_propriedades_por_esec(
    propriedades_por_esec: dict[str, int]
) -> pd.DataFrame:
    """
    Converte o dicionário de contagem de propriedades por ESEC em DataFrame.
    """

    df = pd.DataFrame(
        list(propriedades_por_esec.items()),
        columns=["esec", "quantidade_propriedades"],
    )

    return df.sort_values("quantidade_propriedades", ascending=False).reset_index(drop=True)



def contar_propriedades_por_esec(
    propriedades_df: pd.DataFrame,
    esec_to_municipios: dict[str, list],
) -> dict[str, int]:
    """
    Conta propriedades por ESEC, incluindo ESECs com zero propriedades.
    """

    counts = propriedades_df["esec"].value_counts()

    return {
        esec: int(counts.get(esec, 0))
        for esec in esec_to_municipios.keys()
    }



def extrair_codigos_suinos(valor: str) -> tuple[list[str], list[str]]:
    """
    Extrai códigos de um texto, separando:
    - códigos com 'S'
    - códigos sem 'S'
    """

    texto = str(valor)

    codigos_com_s = re.findall(
        r"(?:CÓD|COD)[^0-9sS]*S[_ ]?(-?\d+)",
        texto,
        re.IGNORECASE
    )

    codigos_sem_s = re.findall(
        r"(?:CÓD|COD)[^0-9]*(-?\d+)",
        texto,
        re.IGNORECASE
    )

    # remover duplicatas já capturadas como "com S"
    codigos_sem_s = [x for x in codigos_sem_s if x not in codigos_com_s]

    return codigos_com_s, codigos_sem_s



def calcular_fatores_risco_suinos(
    relatorio_suinos_df: pd.DataFrame
) -> dict[str, set]:
    """
    Calcula fatores de risco por código de propriedade com base em:
    - Suinos_S
    - TIPO PRODUÇÃO TEC.
    - VULNERABILIDADE
    """

    fator_risco_suinos: dict[str, set] = {}

    for cod, suinos_s, tipo, vul in zip(
        relatorio_suinos_df["Cod. Propriedade"],
        relatorio_suinos_df["Suinos_S"],
        relatorio_suinos_df["TIPO PRODUÇÃO TEC."],
        relatorio_suinos_df["VULNERABILIDADE"],
    ):
        if cod not in fator_risco_suinos:
            fator_risco_suinos[cod] = set()

        if isinstance(suinos_s, list):
            if len(suinos_s) > 0 and "1" in str(suinos_s[0]):
                fator_risco_suinos[cod].add("SUINOS_S_1")

            if "7" in suinos_s:
                fator_risco_suinos[cod].add("LAVAGEM")

            if "17" in suinos_s:
                fator_risco_suinos[cod].add("BAIXA_BIOSSEGURIDADE")

        if isinstance(tipo, str):
            if tipo == "NÃO TECNIFICADA":
                fator_risco_suinos[cod].add("NAO_TECNIFICADA")

        if isinstance(vul, str):
            if vul == "GRANJA COM VULNERABILIDADE ALTA":
                fator_risco_suinos[cod].add("GRANJA_COM_VULNERABILIDADE_ALTA")

    return {
        cod: fatores
        for cod, fatores in fator_risco_suinos.items()
        if fatores
    }



def adicionar_risco_suinos(
    propriedades_df: pd.DataFrame,
    fator_risco_suinos: dict[str, set],
    coluna_propriedade: str = "codigo_da_propriedade",
    coluna_saida: str = "risco_suinos",
) -> pd.DataFrame:
    """
    Adiciona a coluna de risco de suínos.

    Regra:
    - baixo: propriedade sem fator de risco
    - alto: propriedade com pelo menos um fator de risco
    """
    df = propriedades_df.copy()

    df[coluna_saida] = "baixo"

    codigos_risco_suinos = set(fator_risco_suinos.keys())

    df.loc[
        df[coluna_propriedade].isin(codigos_risco_suinos),
        coluna_saida,
    ] = "alto"

    return df



def calcular_percentual_alto_risco_suinos(
    propriedades_df: pd.DataFrame,
    coluna_risco: str = "risco_suinos",
) -> float:
    """
    Calcula o percentual de propriedades com risco alto de suínos.
    """

    total = len(propriedades_df)

    if total == 0:
        return 0.0

    alto = (propriedades_df[coluna_risco] == "alto").sum()

    return (alto / total) * 100



def adicionar_distancia_minima(
    propriedades_df: pd.DataFrame,
    referencia_df: pd.DataFrame,
    coluna_lat_prop: str,
    coluna_lon_prop: str,
    coluna_lat_ref: str,
    coluna_lon_ref: str,
    coluna_saida: str,
) -> pd.DataFrame:
    """
    Calcula a distância mínima, em km, de cada propriedade até pontos de referência.
    """

    df = propriedades_df.copy()
    ref = referencia_df.copy()

    for col in [coluna_lat_prop, coluna_lon_prop]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
        )

    for col in [coluna_lat_ref, coluna_lon_ref]:
        ref[col] = (
            ref[col]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
        )

    df = df.dropna(subset=[coluna_lat_prop, coluna_lon_prop]).copy()
    ref = ref.dropna(subset=[coluna_lat_ref, coluna_lon_ref]).copy()

    conjunto_a = df[[coluna_lat_prop, coluna_lon_prop]].to_numpy(dtype=float)
    conjunto_b = ref[[coluna_lat_ref, coluna_lon_ref]].to_numpy(dtype=float)

    dist_matrix = haversine_distances(
        np.radians(conjunto_a),
        np.radians(conjunto_b),
    ) * 6371

    df[coluna_saida] = dist_matrix.min(axis=1)

    return df



def adicionar_distancia_lixao(
    propriedades_df: pd.DataFrame,
    lixoes_df: pd.DataFrame,
) -> pd.DataFrame:
    return adicionar_distancia_minima(
        propriedades_df=propriedades_df,
        referencia_df=lixoes_df,
        coluna_lat_prop="latitude",
        coluna_lon_prop="longitude",
        coluna_lat_ref="lat",
        coluna_lon_ref="long",
        coluna_saida="dist_lixao_km",
    )



def adicionar_distancia_eventos(
    propriedades_df: pd.DataFrame,
    eventos_df: pd.DataFrame,
) -> pd.DataFrame:
    return adicionar_distancia_minima(
        propriedades_df=propriedades_df,
        referencia_df=eventos_df,
        coluna_lat_prop="latitude",
        coluna_lon_prop="longitude",
        coluna_lat_ref="LATITUDE",
        coluna_lon_ref="LONGITUDE",
        coluna_saida="dist_eventos_km",
    )



def adicionar_risco_lixoes(
    propriedades_df: pd.DataFrame,
    coluna_dist: str = "dist_lixao_km",
    coluna_saida: str = "risco_lixoes",
) -> pd.DataFrame:
    """
    Classifica risco de lixões com base na distância mínima.
    """

    df = propriedades_df.copy()

    df[coluna_saida] = "baixo"

    df.loc[
        df[coluna_dist] <= 3,
        coluna_saida,
    ] = "alto"

    return df



def adicionar_risco_eventos(
    propriedades_df: pd.DataFrame,
    coluna_dist: str = "dist_eventos_km",
    coluna_saida: str = "risco_eventos",
    limite_alto: float = 3.0,
) -> pd.DataFrame:
    """
    Classifica risco de eventos com base na distância mínima.
    """

    df = propriedades_df.copy()

    df[coluna_saida] = "baixo"

    df.loc[
        df[coluna_dist] <= limite_alto,
        coluna_saida,
    ] = "alto"

    return df



def adicionar_risco_lixoes_por_suinos_cod(
    propriedades_df: pd.DataFrame,
    relatorio_suinos_df: pd.DataFrame,
    coluna_saida: str = "risco_lixoes",
) -> pd.DataFrame:
    """
    Marca risco_lixoes como alto para propriedades cujo Suinos_COD
    contenha código '4'.
    """

    df = propriedades_df.copy()

    codigos_alto = set(
        relatorio_suinos_df.loc[
            relatorio_suinos_df["Suinos_COD"].apply(
                lambda x: isinstance(x, list) and len(x) > 0 and "4" in str(x[0])
            ),
            "Cod. Propriedade",
        ]
        .astype(str)
        .str.strip()
    )

    df.loc[
        df["codigo_da_propriedade"].astype(str).str.strip().isin(codigos_alto),
        coluna_saida,
    ] = "alto"

    return df



def adicionar_risco_densidade_bovinos(
    propriedades_df: pd.DataFrame,
    coluna_densidade: str = "densidade_bovinos",
    coluna_saida: str = "risco_densidade_bovinos",
    quantil: float = 0.75,
) -> pd.DataFrame:
    """
    Classifica risco de densidade bovina com base no percentil.
    """

    df = propriedades_df.copy()

    # baseline
    df[coluna_saida] = "baixo"

    # threshold
    threshold = df[coluna_densidade].quantile(quantil)

    # classificação
    df.loc[
        df[coluna_densidade] >= threshold,
        coluna_saida,
    ] = "alto"

    return df



def calcular_percentual_alto_risco_lixoes(
    propriedades_df: pd.DataFrame,
    coluna_risco: str = "risco_lixoes",
) -> float:
    """
    Calcula o percentual de propriedades com risco alto de lixões.
    """

    total = len(propriedades_df)

    if total == 0:
        return 0.0

    alto = (propriedades_df[coluna_risco] == "alto").sum()

    return (alto / total) * 100



def filtrar_eventos_alto_risco(
    eventos_df: pd.DataFrame,
    colunas: list[str] = ["n_eventos_realizados", "n_gta"],
    quantil: float = 0.75,
) -> pd.DataFrame:
    """
    Filtra eventos considerados de alto risco com base no quantil.
    """

    thresholds = eventos_df[colunas].quantile(quantil)

    mask = (eventos_df[colunas] >= thresholds).all(axis=1)

    return eventos_df[mask].copy()



def identificar_gtas_duplicadas(
    gtas_df: pd.DataFrame,
    subset: list[str] = [
        "dt_emissao_gta",
        "cod_produtor_origem",
        "cod_produtor_destino",
    ],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identifica possíveis GTAs duplicadas e gera resumo por combinação.
    """

    linhas_duplicadas = (
        gtas_df[
            gtas_df.duplicated(
                subset=subset,
                keep=False,
            )
        ]
        .sort_values(by=subset)
        .copy()
    )

    qtd_por_combinacao = (
        linhas_duplicadas
        .groupby(subset)
        .size()
        .reset_index(name="qtd")
        .query("qtd > 1")
    )

    return linhas_duplicadas, qtd_por_combinacao



def calcular_periodo_dias_gtas(
    gtas_df: pd.DataFrame,
    coluna_data: str = "dt_emissao_gta",
) -> int:
    """
    Calcula o período total, em dias, coberto pelas GTAs.
    """

    datas = pd.to_datetime(
        gtas_df[coluna_data],
        errors="coerce",
    )

    return (datas.max() - datas.min()).days



def consolidar_gtas_mesma_origem_destino_data(
    gtas_df: pd.DataFrame,
    subset: list[str] = [
        "dt_emissao_gta",
        "cod_produtor_origem",
        "cod_produtor_destino",
    ],
    coluna_qtd: str = "qtd",
) -> pd.DataFrame:
    """
    Consolida movimentações GTA com mesma data, origem e destino,
    somando a quantidade de animais e mantendo apenas uma linha.
    """

    return (
        gtas_df.copy()
        .assign(
            qtd_total=lambda df: df.groupby(subset)[coluna_qtd].transform("sum")
        )
        .sort_values(by=coluna_qtd, ascending=False)
        .drop_duplicates(subset=subset, keep="first")
        .drop(columns=coluna_qtd)
        .rename(columns={"qtd_total": coluna_qtd})
        .reset_index(drop=True)
    )



def calcular_movimentacoes_gtas_por_propriedade(
    propriedades_df: pd.DataFrame,
    gtas_entrada_oe_df: pd.DataFrame,
    gtas_entrada_mg_df: pd.DataFrame,
    coluna_propriedade: str = "codigo_da_propriedade",
    coluna_destino_gta: str = "cod_propriedade_destino",
    coluna_qtd: str = "qtd",
) -> dict[str, dict]:
    """
    Calcula, por propriedade:
    - movimentacoes: número total de movimentações GTA
    - qtd: quantidade total de animais movimentados
    """

    agg_oe = (
        gtas_entrada_oe_df
        .groupby(coluna_destino_gta, as_index=True)
        .agg(
            movimentacoes=(coluna_destino_gta, "size"),
            qtd=(coluna_qtd, "sum"),
        )
    )

    agg_mg = (
        gtas_entrada_mg_df
        .groupby(coluna_destino_gta, as_index=True)
        .agg(
            movimentacoes=(coluna_destino_gta, "size"),
            qtd=(coluna_qtd, "sum"),
        )
    )

    agg_total = agg_oe.add(agg_mg, fill_value=0)

    todas_props = pd.Index(
        propriedades_df[coluna_propriedade].unique(),
        name=coluna_destino_gta,
    )

    agg_total = agg_total.reindex(todas_props, fill_value=0)

    return {
        prop_id: {
            "movimentacoes": int(row["movimentacoes"]),
            "qtd": float(row["qtd"]),
        }
        for prop_id, row in agg_total.iterrows()
    }



def adicionar_metricas_gtas(
    propriedades_df: pd.DataFrame,
    movimentacoes_por_propriedade_dict: dict,
    coluna_propriedade: str = "codigo_da_propriedade",
) -> pd.DataFrame:
    """
    Adiciona métricas de GTAs ao dataframe de propriedades.
    """

    df = propriedades_df.copy()

    df["total_movimentacoes_gtas"] = df[coluna_propriedade].map(
        lambda x: movimentacoes_por_propriedade_dict[x]["movimentacoes"]
    )

    df["total_animais_gtas"] = df[coluna_propriedade].map(
        lambda x: movimentacoes_por_propriedade_dict[x]["qtd"]
    )

    return df



def adicionar_risco_gtas(
    propriedades_df: pd.DataFrame,
    coluna_movimentacoes: str = "total_movimentacoes_gtas",
    coluna_saida: str = "risco_gtas",
    quantil: float = 0.75,
) -> pd.DataFrame:
    """
    Classifica risco GTAs com base no total de movimentações.
    """

    df = propriedades_df.copy()

    df[coluna_saida] = "baixo"

    limite_risco_alto = df[coluna_movimentacoes].quantile(quantil)

    df.loc[
        df[coluna_movimentacoes] >= limite_risco_alto,
        coluna_saida,
    ] = "alto"

    return df



def calcular_riscos_por_coordenadoria(
    propriedades_df: pd.DataFrame,
    coord_to_esec: dict[str, list],
) -> pd.DataFrame:
    """
    Calcula riscos dependentes da distribuição por coordenadoria.

    Atualmente:
    - risco_gtas
    - risco_densidade_bovinos

    Observação:
    - densidade_bovinos já deve existir no dataframe.
    """

    partes_processadas = []

    for nome_coordenadoria in sorted(coord_to_esec.keys()):
        propriedades_coord_df = propriedades_df[
            propriedades_df["coordenadoria"] == nome_coordenadoria
        ].copy()

        if propriedades_coord_df.empty:
            continue

        propriedades_coord_df = adicionar_risco_gtas(propriedades_coord_df)

        propriedades_coord_df = adicionar_risco_densidade_bovinos(
            propriedades_coord_df
        )

        partes_processadas.append(propriedades_coord_df)

    return (
        pd.concat(partes_processadas, axis=0)
        .sort_index()
        .reset_index(drop=True)
    )