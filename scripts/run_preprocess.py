# ==========================================================
# Script: run_preprocess_exploracoes.py
# Objetivo:
# Construir a planilha inicial de propriedades consideradas
# até o estágio interim.
# ==========================================================
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))


from src.data_io import (
    RAW_DIR,
    INTERIM_DIR,
    RESULTS_DIR,
    load_exploracao_pecuaria_raw,
    load_exploracoes_com_coordenadas,
    load_coordenadorias_dict,
    build_coordenadoria_mappings,
    build_esec_municipio_mappings,
    salvar_propriedades_por_esec,
)

from src.preprocessing import (
    preprocess_exploracoes,
    clean_and_pad_identifier,
    filtrar_propriedades_com_coordenadas,
    adicionar_coordenadas,
    adicionar_ano_atualizacao,
    filtrar_exploracoes_por_bovinos,
    filtrar_exploracoes_ativas,
    selecionar_maior_exploracao_por_propriedade,
    adicionar_total_bovinos,
    adicionar_esec_e_coordenadoria,
    gerar_propriedades_por_esec_df,
    padronizar_nomes_colunas,
)


# ==========================================================
# PARÂMETROS AJUSTÁVEIS
# ==========================================================

LIMITE_INFERIOR_DE_BOVINOS_POR_EXPLORACAO = 0

ARQUIVO_PROPRIEDADES_SEM_COORDENADAS = (
    INTERIM_DIR / "Propriedades_Sem_Coordenadas.csv"
)

ARQUIVO_SAIDA_INTERIM = (
    INTERIM_DIR / "propriedades_consideradas_interim.csv"
)


# ==========================================================
# PIPELINE
# ==========================================================

def main():
    print("=" * 70)
    print("INICIANDO PREPROCESSAMENTO DAS EXPLORAÇÕES")
    print("=" * 70)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------
    # 1. Carregar bases
    # ------------------------------------------------------
    print("\n[1/10] Carregando bases...")

    exploracoes_df = load_exploracao_pecuaria_raw()
    exploracoes_com_coordenadas_df = load_exploracoes_com_coordenadas()

    coordenadorias_dict = load_coordenadorias_dict(RAW_DIR)

    _, esec_para_coordenadoria = build_coordenadoria_mappings(
        coordenadorias_dict
    )

    _, codigo_municipio_para_esec = build_esec_municipio_mappings(
        coordenadorias_dict
    )

    print(f"Explorações: {exploracoes_df.shape}")
    print(f"Explorações com coordenadas: {exploracoes_com_coordenadas_df.shape}")
    print(f"Coordenadorias carregadas: {len(coordenadorias_dict)}")

    # ------------------------------------------------------
    # 2. Preprocess básico
    # ------------------------------------------------------
    print("\n[2/10] Limpando CPF/CNPJ e identificadores...")

    exploracoes_df = preprocess_exploracoes(exploracoes_df)

    exploracoes_df["Código da Propriedade"] = clean_and_pad_identifier(
        exploracoes_df["Código da Propriedade"],
        11,
    )

    exploracoes_df["Código do Município"] = clean_and_pad_identifier(
        exploracoes_df["Código do Município"],
        7,
    )

    exploracoes_com_coordenadas_df["Cód. Propriedade"] = clean_and_pad_identifier(
        exploracoes_com_coordenadas_df["Cód. Propriedade"],
        11,
    )

    exploracoes_com_coordenadas_df["Cód. Município"] = clean_and_pad_identifier(
        exploracoes_com_coordenadas_df["Cód. Município"],
        7,
    )

    # ------------------------------------------------------
    # 3. Salvar propriedades sem coordenadas
    # ------------------------------------------------------
    print("\n[3/10] Identificando propriedades sem coordenadas...")

    propriedades_sem_coordenadas_df = exploracoes_df[
        ~exploracoes_df["Código da Propriedade"].isin(
            exploracoes_com_coordenadas_df["Cód. Propriedade"]
        )
    ].copy()

    propriedades_sem_coordenadas_df.to_csv(
        ARQUIVO_PROPRIEDADES_SEM_COORDENADAS,
        index=False,
    )

    print(
        f"Propriedades sem coordenadas: {len(propriedades_sem_coordenadas_df)}"
    )
    print(f"Arquivo salvo em: {ARQUIVO_PROPRIEDADES_SEM_COORDENADAS}")

    # ------------------------------------------------------
    # 4. Filtrar propriedades com coordenadas
    # ------------------------------------------------------
    print("\n[4/10] Filtrando propriedades com coordenadas...")

    exploracoes_df = filtrar_propriedades_com_coordenadas(
        exploracoes_df,
        exploracoes_com_coordenadas_df,
    )

    print(f"Após filtro de coordenadas: {exploracoes_df.shape}")

    # ------------------------------------------------------
    # 5. Adicionar coordenadas
    # ------------------------------------------------------
    print("\n[5/10] Adicionando latitude e longitude...")

    exploracoes_df = adicionar_coordenadas(
        exploracoes_df,
        exploracoes_com_coordenadas_df,
    )

    print(
        "Linhas sem latitude após merge:",
        exploracoes_df["Latitude"].isna().sum(),
    )

    # ------------------------------------------------------
    # 6. Adicionar ano de atualização
    # ------------------------------------------------------
    print("\n[6/10] Criando ano_atualizacao...")

    exploracoes_df = adicionar_ano_atualizacao(exploracoes_df)

    print(
        "Datas inválidas:",
        exploracoes_df["Data da Atualizacao Cadastral"].isna().sum(),
    )

    # ------------------------------------------------------
    # 7. Filtrar bovinos e explorações ativas
    # ------------------------------------------------------
    print("\n[7/10] Filtrando explorações bovinas ativas...")

    exploracoes_bovinos_df = filtrar_exploracoes_por_bovinos(
        exploracoes_df,
        LIMITE_INFERIOR_DE_BOVINOS_POR_EXPLORACAO,
    )

    exploracoes_bovinos_df = filtrar_exploracoes_ativas(
        exploracoes_bovinos_df
    )

    print(f"Explorações bovinas ativas: {exploracoes_bovinos_df.shape}")

    # ------------------------------------------------------
    # 8. Selecionar uma linha por propriedade
    # ------------------------------------------------------
    print("\n[8/10] Selecionando maior exploração por propriedade...")

    propriedades_consideradas_df = selecionar_maior_exploracao_por_propriedade(
        exploracoes_bovinos_df
    )

    propriedades_consideradas_df = adicionar_total_bovinos(
        propriedades_consideradas_df,
        exploracoes_bovinos_df,
    )

    propriedades_consideradas_df = propriedades_consideradas_df.reset_index(
        drop=True
    )

    print(f"Propriedades consideradas: {propriedades_consideradas_df.shape}")

    # ------------------------------------------------------
    # 9. Adicionar ESEC e Coordenadoria
    # ------------------------------------------------------
    print("\n[9/10] Adicionando ESEC e Coordenadoria...")

    propriedades_consideradas_df = adicionar_esec_e_coordenadoria(
        propriedades_consideradas_df,
        codigo_municipio_para_esec,
        esec_para_coordenadoria,
    )

    esec_nan = propriedades_consideradas_df["ESEC"].isna().sum()
    coord_nan = propriedades_consideradas_df["Coordenadoria"].isna().sum()

    print(f"ESEC sem mapeamento: {esec_nan}")
    print(f"Coordenadoria sem mapeamento: {coord_nan}")

    if esec_nan > 0 or coord_nan > 0:
        raise ValueError(
            "Existem propriedades sem ESEC ou Coordenadoria mapeada."
        )

    # ------------------------------------------------------
    # 10. Gerar relatório por ESEC e salvar interim
    # ------------------------------------------------------
    print("\n[10/10] Gerando relatório por ESEC e salvando arquivo interim...")

    propriedades_por_esec_df = gerar_propriedades_por_esec_df(
        propriedades_consideradas_df
    )

    relatorio_path = salvar_propriedades_por_esec(
        propriedades_por_esec_df,
        RESULTS_DIR,
    )

    propriedades_consideradas_df = padronizar_nomes_colunas(
        propriedades_consideradas_df
    )

    propriedades_consideradas_df.to_csv(
        ARQUIVO_SAIDA_INTERIM,
        index=False,
    )

    print("\n" + "=" * 70)
    print("PREPROCESSAMENTO FINALIZADO COM SUCESSO")
    print("=" * 70)
    print(f"Arquivo interim salvo em: {ARQUIVO_SAIDA_INTERIM}")
    print(f"Relatório por ESEC salvo em: {relatorio_path}")
    print(f"Shape final: {propriedades_consideradas_df.shape}")


if __name__ == "__main__":
    main()