# scripts/stress_test_monte_carlo.py

import time
import tracemalloc
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src import monte_carlo


resultados_pert_dict = {
    "gtas": {"min": 0.1, "mode": 0.5, "max": 0.9},
    "densidade_bovinos": {"min": 0.1, "mode": 0.5, "max": 0.9},
    "suinos": {"min": 0.1, "mode": 0.5, "max": 0.9},
    "eventos": {"min": 0.1, "mode": 0.5, "max": 0.9},
    "lixoes": {"min": 0.1, "mode": 0.5, "max": 0.9},
}

relevancia_dos_riscos = {
    "gtas": 0.25,
    "densidade_bovinos": 0.20,
    "suinos": 0.20,
    "eventos": 0.15,
    "lixoes": 0.20,
}


def rodar_teste(n_simulacoes: int):
    print("=" * 70)
    print(f"Rodando Monte Carlo com {n_simulacoes} simulações")
    print("=" * 70)

    tracemalloc.start()
    inicio = time.perf_counter()

    monte_carlo.main(
        resultados_pert_dict=resultados_pert_dict,
        relevancia_dos_riscos=relevancia_dos_riscos,
        n_exploracoes=1000,
        coordenadoria="stress_tests/monte_carlo",
        esec=f"ESEC_{n_simulacoes}",
        n_simulacoes=n_simulacoes,
    )

    tempo = time.perf_counter() - inicio
    memoria_atual, memoria_pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Tempo: {tempo:.2f} s")
    print(f"Memória atual: {memoria_atual / 1024 / 1024:.2f} MB")
    print(f"Pico de memória: {memoria_pico / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    for n in [1000, 10000, 50000, 100000]:
        rodar_teste(n)