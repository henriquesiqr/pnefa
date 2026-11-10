# =========================
# IMPORTS
# =========================

from pathlib import Path
import pandas as pd

from src.legacy import explora_modelo
from src import monte_carlo
from src import seleciona_propriedades

from src.data_io import load_propriedades_risco_sanitario, RESULTS_DIR

# =========================
# PATHS DO PROJETO
# =========================
DIRETORIO_RAIZ = Path(__file__).resolve().parent.parent


def run_single_pipeline(coordenadoria_nome: str, esec_nome: str) -> dict:
    propriedades_df = load_propriedades_risco_sanitario()

    coordenadoria_dir = RESULTS_DIR / coordenadoria_nome
    coordenadoria_dir.mkdir(parents=True, exist_ok=True)

    resultados_pert_dict, relevancia_dos_riscos, n_exploracoes = explora_modelo.main(
        DIRETORIO_RAIZ,
        coordenadoria_nome,
        esec_nome,
    )

    resultados = monte_carlo.main(
        resultados_pert_dict,
        relevancia_dos_riscos,
        n_exploracoes,
        coordenadoria_nome,
        esec_nome,
        n_simulacoes=10000,
    )

    seleciona_propriedades.main(
        resultados,
        propriedades_df,
        str(coordenadoria_dir),
        coordenadoria_nome,
        esec_nome,
    )

    return {
        "coordenadoria": coordenadoria_nome,
        "esec": esec_nome,
        "status": "SUCESSO",
    }