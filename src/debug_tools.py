import pandas as pd



def diagnostico_digitos(df, col):
    print(f"Diagnóstico: {col}")
    
    serie = df[col].astype(str).str.strip()
    
    # tamanho da string
    tamanhos = serie.str.len()
    
    # contagem por tamanho
    dist = tamanhos.value_counts().sort_index()
    
    print(dist)
    
    # exemplos estranhos
    print("\nExemplos por tamanho:")
    for tamanho in dist.index:
        exemplos = serie[tamanhos == tamanho].head(3).tolist()
        print(f"{tamanho} dígitos → {exemplos}")



def checar_coluna_identificador(coluna: pd.Series, nome: str) -> None:
    """
    Exibe diagnóstico de uma coluna identificadora:
    - dtype original
    - presença de sufixo .0
    - distribuição de tamanho após limpeza básica
    """
    print(f"\n--- {nome} ---")

    serie = (
        coluna.astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .replace("nan", None)
    )

    print("dtype:", coluna.dtype)
    print("tem '.0'? ->", coluna.astype(str).str.contains(r"\.0$").any())
    print("distribuição de tamanho:")
    print(serie.dropna().str.len().value_counts().sort_index())



def diagnosticar_exploracoes_bovinos(
    df: pd.DataFrame,
    coluna_status: str = "Situação da Exploração",
    coluna_propriedade: str = "Código da Propriedade",
    coluna_bovinos: str = "Quantidade de Bovinos",
) -> dict:
    """
    Gera diagnóstico das explorações bovinas.
    """
    diagnostico = {}

    diagnostico["situacoes_exploracao"] = df[coluna_status].dropna().unique().tolist()
    diagnostico["linhas_duplicadas"] = int(df.duplicated().sum())
    diagnostico["estatisticas_bovinos"] = df[coluna_bovinos].describe()
    diagnostico["num_propriedades_distintas"] = int(df[coluna_propriedade].nunique())

    exploracoes_por_propriedade = df[coluna_propriedade].value_counts()
    propriedades_mais_de_uma = exploracoes_por_propriedade[
        exploracoes_por_propriedade > 1
    ]

    diagnostico["num_propriedades_mais_de_uma_exploracao"] = int(
        propriedades_mais_de_uma.count()
    )
    diagnostico["total_exploracoes_mais_de_uma"] = int(
        propriedades_mais_de_uma.sum()
    )
    diagnostico["total_exploracoes"] = int(
        exploracoes_por_propriedade.sum()
    )
    diagnostico["propriedades_mais_de_uma_exploracao"] = propriedades_mais_de_uma

    return diagnostico



def contar_inconsistencias_bovinos(df: pd.DataFrame) -> int:
    """
    Conta quantas propriedades têm Total de Bovinos diferente da Quantidade de Bovinos.
    """
    return int(
        (df["Total de Bovinos"] != df["Quantidade de Bovinos"]).sum()
    )



def validar_total_vs_exploracao(df: pd.DataFrame) -> dict:
    """
    Verifica inconsistências entre total de bovinos e exploração selecionada.
    """

    inconsistencias = (
        df["Total de Bovinos"] < df["Quantidade de Bovinos"]
    ).sum()

    return {
        "qtd_total_menor_que_exploracao": int(inconsistencias),
        "ok": inconsistencias == 0
    }



def contar_esecs_por_coordenadoria(coordenadoria_para_esecs: dict) -> dict:
    """
    Retorna:
    - quantidade de ESECs por coordenadoria
    - total de ESECs
    """
    por_coord = {
        nome: len(esecs)
        for nome, esecs in coordenadoria_para_esecs.items()
    }

    total = sum(por_coord.values())

    return {
        "por_coordenadoria": por_coord,
        "total_esecs": total
    }



def diagnosticar_cobertura_geometria(df: pd.DataFrame) -> dict:
    """
    Avalia cobertura de num_area e geometry após merge geoespacial.
    """

    total = len(df)

    num_area_nulls = df["num_area"].isna().sum()
    geometry_nulls = df["geometry"].isna().sum()

    num_area_filled_pct = 100 * (1 - num_area_nulls / total)
    geometry_filled_pct = 100 * (1 - geometry_nulls / total)

    return {
        "total": total,
        "num_area_nulls": int(num_area_nulls),
        "geometry_nulls": int(geometry_nulls),
        "num_area_filled_pct": float(num_area_filled_pct),
        "geometry_filled_pct": float(geometry_filled_pct),
    }