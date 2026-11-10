'''
Projeto: Pesquisa, Desenvolvimento e Inovação Aplicados à Modernização Tecnológica
do Instituto Mineiro de Agropecuária - IMA
Convênio nº 024/2024 - IMA/UFLA/FUNDECC

Plano de Trabalho - "Raízes da Sanidade: um estudo sobre árvore de cenários para determinação 
de propriedades de risco para febre aftosa"

Autor: Mayron César de Oliveira Moreira
Departamento de Ciência da Computação - DCC
Universidade Federal de Lavras - UFLA
'''

import os
from pathlib import Path
import sys
import pandas as pd

import src.legacy.explora_modelo as explora_modelo
import monte_carlo
import seleciona_propriedades

# diretorios principais
DIRETORIO_RAIZ = Path(__file__).resolve().parent.parent
DIRETORIO_PRINCIPAL = os.path.join(DIRETORIO_RAIZ, "data")
DIRETORIO_RESULTADOS = os.path.join(DIRETORIO_RAIZ, "results")

if __name__ == "__main__":
    propriedades_consideradas_df = pd.read_csv(os.path.join(DIRETORIO_RESULTADOS, "Propriedades_consideradas_FINAL.csv"))
    coordenadoria_nome = sys.argv[1]
    esec_nome = sys.argv[2]
    coordenadoria_dir = os.path.join(DIRETORIO_RESULTADOS, coordenadoria_nome)
    Path(coordenadoria_dir).mkdir(parents=True, exist_ok=True)
    # testar se o diretório foi criado corretamente
    if not os.path.exists(coordenadoria_dir):
        raise Exception(f"Diretório {coordenadoria_dir} não pôde ser criado.")
    resultados_pert_dict, relevancia_dos_riscos, n_exploracoes = explora_modelo.main(DIRETORIO_RAIZ, coordenadoria_nome, esec_nome)
    resultados = monte_carlo.main(resultados_pert_dict, relevancia_dos_riscos, n_exploracoes, coordenadoria_nome, esec_nome, n_simulacoes=10000)
    #seleciona_propriedades.main(resultados, propriedades_consideradas_df, coordenadoria_dir, coordenadoria_nome, esec_nome)
    seleciona_propriedades.main(resultados, propriedades_consideradas_df, coordenadoria_dir, coordenadoria_nome, esec_nome)
    