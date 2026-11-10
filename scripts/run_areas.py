# ==========================================================
# Script: run_areas.py
# Objetivo:
# Enriquecer propriedades consideradas com CAR, geometria,
# área e densidade de bovinos, salvando o dataset final em
# data/processed.
# ==========================================================
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))


from src.data_io import (
    RAW_DIR,
    PROCESSED_DIR,
    load_propriedades_consideradas_interim,
    load_area_imovel,
    load_propriedade_car,
    salvar_propriedades_processed,
)

from src.preprocessing import (
    selecionar_colunas_area_imovel,
    padronizar_nomes_colunas,
    adicionar_geometria_imovel,
    preencher_area_pela_mediana_municipio,
    remover_colunas_auxiliares_geometria,
    calcular_densidade_bovinos,
)

from src.debug_tools import diagnosticar_cobertura_geometria


def main():
    print("=" * 70)
    print("INICIANDO ENRIQUECIMENTO COM ÁREA/CAR")
    print("=" * 70)

    # ------------------------------------------------------
    # 1. Carregar bases
    # ------------------------------------------------------
    print("\n[1/7] Carregando bases...")

    propriedades_df = load_propriedades_consideradas_interim()
    area_imovel_gdf = load_area_imovel(RAW_DIR)
    propriedade_car_df = load_propriedade_car(RAW_DIR)

    print(f"Propriedades interim: {propriedades_df.shape}")
    print(f"Área imóvel: {area_imovel_gdf.shape}")
    print(f"Correspondências propriedade-CAR: {propriedade_car_df.shape}")

    # ------------------------------------------------------
    # 2. Selecionar colunas do shapefile
    # ------------------------------------------------------
    print("\n[2/7] Selecionando colunas relevantes do shapefile...")

    area_imovel_gdf = selecionar_colunas_area_imovel(area_imovel_gdf)

    # ------------------------------------------------------
    # 3. Padronizar nomes de colunas
    # ------------------------------------------------------
    print("\n[3/7] Padronizando nomes de colunas...")

    propriedades_df = padronizar_nomes_colunas(propriedades_df)
    propriedade_car_df = padronizar_nomes_colunas(propriedade_car_df)
    area_imovel_gdf = padronizar_nomes_colunas(area_imovel_gdf)

    # ------------------------------------------------------
    # 4. Adicionar CAR, área e geometria
    # ------------------------------------------------------
    print("\n[4/7] Adicionando geometria e área via CAR...")

    propriedades_df = adicionar_geometria_imovel(
        propriedades_df,
        propriedade_car_df,
        area_imovel_gdf,
    )

    diag_antes = diagnosticar_cobertura_geometria(propriedades_df)

    print("Cobertura antes da imputação:")
    print(diag_antes)

    # ------------------------------------------------------
    # 5. Preencher áreas ausentes pela mediana do município
    # ------------------------------------------------------
    print("\n[5/7] Preenchendo num_area ausente pela mediana do município...")

    propriedades_df = preencher_area_pela_mediana_municipio(propriedades_df)

    diag_depois = diagnosticar_cobertura_geometria(propriedades_df)

    print("Cobertura depois da imputação:")
    print(diag_depois)

    # ------------------------------------------------------
    # 6. Limpar colunas auxiliares e calcular densidade
    # ------------------------------------------------------
    print("\n[6/7] Removendo colunas auxiliares e calculando densidade...")

    propriedades_df = remover_colunas_auxiliares_geometria(propriedades_df)
    propriedades_df = calcular_densidade_bovinos(propriedades_df)

    # ------------------------------------------------------
    # 7. Salvar dataset processed
    # ------------------------------------------------------
    print("\n[7/7] Salvando dataset final em processed...")

    path = salvar_propriedades_processed(
        propriedades_df,
        PROCESSED_DIR,
    )

    print("\n" + "=" * 70)
    print("ENRIQUECIMENTO FINALIZADO COM SUCESSO")
    print("=" * 70)
    print(f"Arquivo processed salvo em: {path}")
    print(f"Shape final: {propriedades_df.shape}")


if __name__ == "__main__":
    main()