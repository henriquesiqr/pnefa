# ==========================================================
# Script: run_risk.py
# Objetivo:
# Calcular riscos sanitários por propriedade a partir do
# dataset processed gerado no pipeline anterior.
# ==========================================================
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))


import pandas as pd

from src.data_io import (
    RAW_DIR,
    PROCESSED_DIR,
    load_propriedades_processed,
    load_coordenadorias_dict,
    build_coordenadoria_mappings,
    load_relatorio_suinos,
    load_lixoes,
    load_eventos,
    load_gtas_entrada_origem_qualquer_MG_destino_prop_MG,
    load_gtas_entrada_origem_qualquer_OE_destino_prop_MG,
    load_gtas_saida_origem_prop_MG_destino_qualquer,
    salvar_propriedades_por_esec,
    save_propriedades_risco_sanitario,
)

from src.risk_processing import (
    calcular_qtd_esecs_por_coordenadoria,
    build_esec_municipio_mappings,
    normalizar_chaves_municipio,
    contar_propriedades_por_esec,
    construir_df_propriedades_por_esec,
    extrair_codigos_suinos,
    calcular_fatores_risco_suinos,
    adicionar_risco_suinos,
    calcular_percentual_alto_risco_suinos,
    adicionar_distancia_lixao,
    adicionar_risco_lixoes,
    adicionar_risco_lixoes_por_suinos_cod,
    calcular_percentual_alto_risco_lixoes,
    filtrar_eventos_alto_risco,
    adicionar_distancia_eventos,
    adicionar_risco_eventos,
    adicionar_risco_densidade_bovinos,
    identificar_gtas_duplicadas,
    calcular_periodo_dias_gtas,
    consolidar_gtas_mesma_origem_destino_data,
    calcular_movimentacoes_gtas_por_propriedade,
    adicionar_metricas_gtas,
    adicionar_risco_gtas,
    calcular_riscos_por_coordenadoria,
)


# ==========================================================
# PARÂMETROS AJUSTÁVEIS
# ==========================================================

COLUNA_TEXTO_SUINOS = 11
COLUNA_TEXTO_PROPRIEDADE_SUINOS = 17


# ==========================================================
# PIPELINE
# ==========================================================

def main():
    print("=" * 70)
    print("INICIANDO CÁLCULO DE RISCOS POR COORDENADORIA")
    print("=" * 70)

    # ------------------------------------------------------
    # 1. Carregar base principal e coordenadorias
    # ------------------------------------------------------
    print("\n[1/9] Carregando propriedades processadas e coordenadorias...")

    propriedades_df = load_propriedades_processed()

    coordenadorias_dict = load_coordenadorias_dict(RAW_DIR)

    coord_to_esec, esec_to_coord = build_coordenadoria_mappings(
        coordenadorias_dict
    )

    qtd_esecs_por_coordenadoria, total_esecs = (
        calcular_qtd_esecs_por_coordenadoria(coord_to_esec)
    )

    esec_to_municipios, municipio_to_esec, total_municipios = (
        build_esec_municipio_mappings(coordenadorias_dict)
    )

    municipio_to_esec = normalizar_chaves_municipio(municipio_to_esec)

    print(f"Propriedades: {propriedades_df.shape}")
    print(f"Coordenadorias: {len(coord_to_esec)}")
    print(f"ESECs: {total_esecs}")
    print(f"Municípios mapeados: {total_municipios}")

    # ------------------------------------------------------
    # 2. Gerar e salvar agregação de propriedades por ESEC
    # ------------------------------------------------------
    print("\n[2/9] Calculando propriedades por ESEC...")

    propriedades_por_esec = contar_propriedades_por_esec(
        propriedades_df,
        esec_to_municipios,
    )

    propriedades_por_esec_df = construir_df_propriedades_por_esec(
        propriedades_por_esec
    )

    propriedades_por_esec_path = salvar_propriedades_por_esec(
        propriedades_por_esec_df,
        PROCESSED_DIR,
    )

    print(f"Relatório propriedades por ESEC salvo em: {propriedades_por_esec_path}")

    # ------------------------------------------------------
    # 3. Calcular risco de suínos
    # ------------------------------------------------------
    print("\n[3/9] Calculando risco de suínos...")

    relatorio_suinos_df = load_relatorio_suinos(RAW_DIR)

    relatorio_suinos_df[["Suinos_S", "Suinos_COD"]] = (
        relatorio_suinos_df.iloc[:, COLUNA_TEXTO_SUINOS]
        .apply(lambda x: pd.Series(extrair_codigos_suinos(x)))
    )

    relatorio_suinos_df[["Prop_S", "Prop_COD"]] = (
        relatorio_suinos_df.iloc[:, COLUNA_TEXTO_PROPRIEDADE_SUINOS]
        .apply(lambda x: pd.Series(extrair_codigos_suinos(x)))
    )

    relatorio_suinos_df = relatorio_suinos_df[
        relatorio_suinos_df["Prop_S"].notna()
        | relatorio_suinos_df["Prop_COD"].notna()
    ]

    fator_risco_suinos = calcular_fatores_risco_suinos(relatorio_suinos_df)

    propriedades_df = adicionar_risco_suinos(
        propriedades_df,
        fator_risco_suinos,
    )

    percentual_suinos = calcular_percentual_alto_risco_suinos(propriedades_df)

    print(f"Percentual alto risco suínos: {percentual_suinos:.2f}%")
    print(propriedades_df["risco_suinos"].value_counts())

    # ------------------------------------------------------
    # 4. Calcular risco de lixões
    # ------------------------------------------------------
    print("\n[4/9] Calculando risco de lixões...")

    lixoes_df = load_lixoes(RAW_DIR)

    propriedades_df = adicionar_distancia_lixao(
        propriedades_df,
        lixoes_df,
    )

    propriedades_df = adicionar_risco_lixoes(propriedades_df)

    propriedades_df = adicionar_risco_lixoes_por_suinos_cod(
        propriedades_df,
        relatorio_suinos_df,
    )

    percentual_lixoes = calcular_percentual_alto_risco_lixoes(propriedades_df)

    print(f"Percentual alto risco lixões: {percentual_lixoes:.2f}%")
    print(propriedades_df["risco_lixoes"].value_counts())

    # ------------------------------------------------------
    # 5. Calcular risco de eventos
    # ------------------------------------------------------
    print("\n[5/9] Calculando risco de eventos...")

    relatorio_eventos_df = load_eventos(RAW_DIR)

    eventos_considerados_df = filtrar_eventos_alto_risco(
        relatorio_eventos_df
    )

    propriedades_df = adicionar_distancia_eventos(
        propriedades_df,
        eventos_considerados_df,
    )

    propriedades_df = adicionar_risco_eventos(propriedades_df)

    print(propriedades_df["risco_eventos"].value_counts())

    # ------------------------------------------------------
    # 6. Calcular risco de densidade bovina
    # ------------------------------------------------------
    print("\n[6/9] Calculando risco de densidade bovina...")

    propriedades_df = adicionar_risco_densidade_bovinos(propriedades_df)

    print(propriedades_df["risco_densidade_bovinos"].value_counts())

    # ------------------------------------------------------
    # 7. Carregar, consolidar e agregar GTAs
    # ------------------------------------------------------
    print("\n[7/9] Processando GTAs...")

    gtas_entrada_origem_qualquer_MG_destino_prop_MG_df = (
        load_gtas_entrada_origem_qualquer_MG_destino_prop_MG(RAW_DIR)
    )

    gtas_entrada_origem_qualquer_OE_destino_prop_MG_df = (
        load_gtas_entrada_origem_qualquer_OE_destino_prop_MG(RAW_DIR)
    )

    _ = load_gtas_saida_origem_prop_MG_destino_qualquer(RAW_DIR)

    _, qtd_duplicadas_oe = identificar_gtas_duplicadas(
        gtas_entrada_origem_qualquer_OE_destino_prop_MG_df
    )

    _, qtd_duplicadas_mg = identificar_gtas_duplicadas(
        gtas_entrada_origem_qualquer_MG_destino_prop_MG_df
    )

    total_dias = calcular_periodo_dias_gtas(
        gtas_entrada_origem_qualquer_MG_destino_prop_MG_df
    )

    antes_oe = len(gtas_entrada_origem_qualquer_OE_destino_prop_MG_df)
    antes_mg = len(gtas_entrada_origem_qualquer_MG_destino_prop_MG_df)

    gtas_entrada_origem_qualquer_OE_destino_prop_MG_df = (
        consolidar_gtas_mesma_origem_destino_data(
            gtas_entrada_origem_qualquer_OE_destino_prop_MG_df
        )
    )

    gtas_entrada_origem_qualquer_MG_destino_prop_MG_df = (
        consolidar_gtas_mesma_origem_destino_data(
            gtas_entrada_origem_qualquer_MG_destino_prop_MG_df
        )
    )

    print(f"Período GTAs: {total_dias} dias")
    print(f"Duplicadas OE: {len(qtd_duplicadas_oe)} combinações")
    print(f"Duplicadas MG: {len(qtd_duplicadas_mg)} combinações")
    print(
        "Redução OE: "
        f"{((antes_oe - len(gtas_entrada_origem_qualquer_OE_destino_prop_MG_df)) / antes_oe * 100):.2f}%"
    )
    print(
        "Redução MG: "
        f"{((antes_mg - len(gtas_entrada_origem_qualquer_MG_destino_prop_MG_df)) / antes_mg * 100):.2f}%"
    )

    movimentacoes_por_propriedade_dict = (
        calcular_movimentacoes_gtas_por_propriedade(
            propriedades_df,
            gtas_entrada_origem_qualquer_OE_destino_prop_MG_df,
            gtas_entrada_origem_qualquer_MG_destino_prop_MG_df,
        )
    )

    propriedades_df = adicionar_metricas_gtas(
        propriedades_df,
        movimentacoes_por_propriedade_dict,
    )

    propriedades_df = adicionar_risco_gtas(propriedades_df)

    print(propriedades_df["risco_gtas"].value_counts())

    # ------------------------------------------------------
    # 8. Recalcular riscos regionais por coordenadoria
    # ------------------------------------------------------
    print("\n[8/9] Recalculando riscos regionais por coordenadoria...")

    propriedades_df = calcular_riscos_por_coordenadoria(
        propriedades_df,
        coord_to_esec,
    )


    # ------------------------------------------------------
    # Contar quantidade de riscos altos por propriedade
    # ------------------------------------------------------

    colunas_risco = [
        "risco_suinos",
        "risco_lixoes",
        "risco_eventos",
        "risco_densidade_bovinos",
        "risco_gtas",
    ]

    propriedades_df["qtd_riscos_altos"] = (
        propriedades_df[colunas_risco]
        .eq("alto")
        .sum(axis=1)
    )


    # ------------------------------------------------------
    # 9. Salvar base final
    # ------------------------------------------------------
    print("\n[9/9] Salvando dataset consolidado de risco sanitário...")

    output_path = save_propriedades_risco_sanitario(
        propriedades_df,
        PROCESSED_DIR,
    )


    print("\n" + "=" * 70)
    print("CÁLCULO DE RISCOS FINALIZADO COM SUCESSO")
    print("=" * 70)
    print(f"Arquivo salvo em: {output_path}")
    print(f"Shape final: {propriedades_df.shape}")


if __name__ == "__main__":
    main()