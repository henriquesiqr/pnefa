# ==========================================================
# Script: run_all_pipeline.py
# Objetivo:
# Rodar o pipeline completo para todas as combinações de
# coordenadoria e esec.
# ==========================================================

import pandas as pd
import time
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))


from src.pipeline_runner import run_single_pipeline
from src.data_io import load_propriedades_risco_sanitario, RESULTS_DIR


# ==========================================================
# PARÂMETROS AJUSTÁVEIS
# ==========================================================
COLUNA_COORDENADORIA = "coordenadoria"
COLUNA_ESEC = "esec"

REMOVER_DUPLICATAS = True
MOSTRAR_LOG_NO_TERMINAL = False
ARQUIVO_RESUMO = RESULTS_DIR / "resumo_execucao_pipeline_todas_esecs.csv"
LIMITE_TESTE = None


def carregar_pares_coord_esec():
    df = load_propriedades_risco_sanitario()

    if COLUNA_COORDENADORIA not in df.columns:
        raise KeyError(
            f"Coluna '{COLUNA_COORDENADORIA}' não encontrada. "
            f"Colunas disponíveis: {list(df.columns)}"
        )

    if COLUNA_ESEC not in df.columns:
        raise KeyError(
            f"Coluna '{COLUNA_ESEC}' não encontrada. "
            f"Colunas disponíveis: {list(df.columns)}"
        )

    pares_df = df[[COLUNA_COORDENADORIA, COLUNA_ESEC]].dropna().copy()
    pares_df[COLUNA_COORDENADORIA] = pares_df[COLUNA_COORDENADORIA].astype(str).str.strip()
    pares_df[COLUNA_ESEC] = pares_df[COLUNA_ESEC].astype(str).str.strip()

    if REMOVER_DUPLICATAS:
        pares_df = pares_df.drop_duplicates()

    return list(pares_df.itertuples(index=False, name=None))


def salvar_resumo(resultados):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df_resultados = pd.DataFrame(resultados)
    df_resultados.to_csv(ARQUIVO_RESUMO, index=False, encoding="utf-8-sig")
    return df_resultados


def main():
    pares = carregar_pares_coord_esec()

    if not pares:
        print("Nenhum par coordenadoria/esec encontrado.")
        return

    print("=" * 70)
    print(f"Total de combinações encontradas: {len(pares)}")
    print("=" * 70)

    resultados = []

    if LIMITE_TESTE is not None:
        pares = pares[:LIMITE_TESTE]

    for i, (coordenadoria, esec) in enumerate(pares, start=1):
        print(
            f"\n[{i}/{len(pares)}] "
            f"Rodando coordenadoria='{coordenadoria}' | esec='{esec}'"
        )

        inicio = time.perf_counter()

        try:
            resultado = run_single_pipeline(coordenadoria, esec)

            tempo_execucao = time.perf_counter() - inicio

            resultado["returncode"] = 0
            resultado["status"] = "SUCESSO"
            resultado["tempo_execucao_s"] = round(tempo_execucao, 2)

            resultados.append(resultado)

            print(f"  -> SUCESSO em {tempo_execucao:.2f}s")

        except Exception as e:
            tempo_execucao = time.perf_counter() - inicio

            resultados.append({
                "coordenadoria": coordenadoria,
                "esec": esec,
                "returncode": -1,
                "status": "EXCEPTION",
                "stderr": str(e),
                "tempo_execucao_s": round(tempo_execucao, 2),
            })

            print(f"  -> EXCEPTION em {tempo_execucao:.2f}s: {e}")

    df_resumo = salvar_resumo(resultados)

    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)
    print(df_resumo["status"].value_counts(dropna=False))
    print(f"\nResumo salvo em: {ARQUIVO_RESUMO}")


if __name__ == "__main__":
    main()