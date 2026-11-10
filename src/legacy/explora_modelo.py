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


# =========================
# PARÂMETROS AJUSTÁVEIS
# =========================
ALPHA_SIGNIFICANCIA = 0.05       # nível de significância -> IC de 95%
LAMBDA_PERT = 4.0                # parametrização clássica da Beta-PERT
N_AMOSTRAS_PLOT = 10000          # número de amostras para visualização
RANDOM_SEED = 532                # seed para reprodutibilidade
SALVAR_GRAFICOS = True           # controla geração dos histogramas
USAR_JEFFREYS_COMO_MODE = False  # False = usa p_hat | True = usa (x + 0.5)/(n + 1)

# =========================
# CARREGAMENTO DE BIBLIOTECAS
# =========================
import os
import json # adicionado no topo para maior clareza
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.stats.proportion import proportion_confint
from scipy.stats import beta
from pathlib import Path

from src.data_io import load_propriedades_risco_sanitario



def main(diretorio_principal, coordenadoria_teste, esec_teste):
    # coordenadoria para os testes
    coordenadoria = coordenadoria_teste

    # diretorios
    DOCS_DIR = diretorio_principal
    RESULTS_DIR = os.path.join(DOCS_DIR, "results")
    RESULTS_COORDENADORIA_DIR = os.path.join(RESULTS_DIR, coordenadoria)

    # carregar o dataframe de propriedades consideradas
    propriedades_df = load_propriedades_risco_sanitario()

    # cidade de teste
    cidade_teste = esec_teste
    
    # selecionando as explorações da cidade de teste
    exploracoes_consideradas_df = propriedades_df[
    propriedades_df["esec"].astype(str).str.strip() == str(cidade_teste).strip()
    ]

    # cálculo dos percentuais de risco alto para cada fator de risco
    total_exploracoes = len(exploracoes_consideradas_df)
    total_exploracoes_gtas = len(exploracoes_consideradas_df[exploracoes_consideradas_df['risco_gtas'] == 'alto'])
    total_exploracoes_densidade_bovinos = len(exploracoes_consideradas_df[exploracoes_consideradas_df['risco_densidade_bovinos'] == 'alto'])
    total_exploracoes_suinos = len(exploracoes_consideradas_df[exploracoes_consideradas_df['risco_suinos'] == 'alto'])
    total_exploracoes_eventos = len(exploracoes_consideradas_df[exploracoes_consideradas_df['risco_eventos'] == 'alto'])
    total_exploracoes_lixoes = len(exploracoes_consideradas_df[exploracoes_consideradas_df['risco_lixoes'] == 'alto'])
    
    # dicionário para armazenar os resultados (min, mode, max, alpha, beta)
    resultados_pert = {}
    
    # dicionário para armazenar o número de amostras específicas (risco alto) para cada fator de risco
    amostras_especificas = {
        'gtas': total_exploracoes_gtas,
        'densidade_bovinos': total_exploracoes_densidade_bovinos,
        'suinos': total_exploracoes_suinos,
        'eventos': total_exploracoes_eventos,
        'lixoes': total_exploracoes_lixoes
    }

    # amostragem da distribuição Beta-PERT para cada fator de risco
    for amostra_nome, amostra in amostras_especificas.items():
        x = amostra       # número de amostras classificadas como "risco alto"
        n = total_exploracoes      # total de amostras
        alpha = ALPHA_SIGNIFICANCIA  # nível de significância -> IC 95%
        lam = LAMBDA_PERT     # lambda do PERT (lambda=4 é o "beta-pert" clássico)

        # Atenção: se não houver propriedades na ESEC selecionada (n = 0),
        # a proporção observada não pode ser calculada. Idealmente, esse caso
        # deve ser tratado antes desta etapa.
        if n == 0:
            raise ValueError(f"Nenhuma exploração encontrada para a ESEC {cidade_teste}")

        # --- 1) proporção observada ---
        p_hat = x / n
        #print(f"Proporção observada p̂ = {p_hat:.4f} ({x}/{n})")

        # Nota: o uso de p̂ como estimativa pontual (mode) pode enviesar a Beta-PERT para amostras pequenas.
        # Alternativas mais robustas incluem:
        # - a média da distribuição Beta posterior (alpha / (alpha + beta))
        # - estimadores suavizados, como Jeffreys: (x + 0.5) / (n + 1)
        
        # TODO: avaliar impacto de substituir p̂ por estimativa Bayesiana na estabilidade das distribuições
        # e dos pesos finais.

        # --- 2) intervalo de confiança de Wilson ---
        lower, upper = proportion_confint(count=x, nobs=n, alpha=alpha, method='wilson')

        # defensiva: evitar degenerate interval 
        if upper <= lower:
            raise ValueError("Intervalo inválido: upper <= lower")

        # --- 3) definir min, mode, max para PERT ---
        pert_min = lower
        pert_mode = p_hat   # pode usar outro ponto, por ex. (lower+upper)/2 ou Agresti-Coull
        pert_max = upper

        # --- 4) converter para Beta(α, β) (Beta-PERT) ---
        # formula:
        alpha_beta = 1.0 + lam * (pert_mode - pert_min) / (pert_max - pert_min)
        beta_beta  = 1.0 + lam * (pert_max - pert_mode) / (pert_max - pert_min)

        # armazenar resultados
        resultados_pert[amostra_nome] = {
            'min': pert_min,
            'mode': pert_mode,
            'max': pert_max,
            'alpha': alpha_beta,
            'beta': beta_beta
        }
        # histograma da distribuição Beta-PERT
        samples_pert = beta.rvs(a=alpha_beta, b=beta_beta, size=10000, random_state=RANDOM_SEED)
        plt.figure(figsize=(8,4))
        plt.hist(samples_pert, bins=80, density=True, alpha=0.6)
        plt.title("Beta-PERT (aprox) para proporção 'risco alto'")
        plt.xlabel("proporção")
        plt.grid(True)
        # armazenar a figura

        # 1) criar o diretório se não existir
        #if not os.path.exists(os.path.join(RESULTS_COORDENADORIA_DIR, esec_teste)):
        #    os.makedirs(os.path.join(RESULTS_COORDENADORIA_DIR, esec_teste))
        os.makedirs(os.path.join(RESULTS_COORDENADORIA_DIR, esec_teste), exist_ok=True) # BUGFIX: antes criava diretórios repetidos

        if SALVAR_GRAFICOS: # Adiciona opcionalidade de salvar gráficos
            plt.savefig(f"{RESULTS_COORDENADORIA_DIR}/{esec_teste}/{esec_teste}_beta_pert_{amostra_nome}.png")
            plt.close() # BUGFIX: risco de estourar memória

    lam = LAMBDA_PERT

    # armazenando a relevancia dos riscos
    relevancia_dos_riscos = {}
    # nome_dos_riscos = ['gtas', 'densidade_bovinos', 'suinos', 'eventos', 'lixoes']
    nome_dos_riscos = list(amostras_especificas.keys())  # Deixa o código escalável

    resultados_pert_array = np.array([
    [resultados_pert[n]['min'], resultados_pert[n]['mode'], resultados_pert[n]['max']]
    for n in nome_dos_riscos
    ])

    resultados_pert_dict = {
    nome: {
        'min': resultados_pert[nome]['min'],
        'mode': resultados_pert[nome]['mode'],
        'max': resultados_pert[nome]['max'],
    }
    for nome in nome_dos_riscos
}   # Manutenção da refatoração

    means = (resultados_pert_array[:,0] + lam*resultados_pert_array[:,1] + resultados_pert_array[:,2]) / (lam + 2)

    if means.sum() == 0:
        raise ValueError("Soma dos valores PERT é zero (impossível normalizar pesos)")

    weights = means / means.sum()
    
    for nome, w in zip(nome_dos_riscos, weights):
        relevancia_dos_riscos[nome] = w

    # imprimir em um json file resultados_pert_dict e relevancia_dos_riscos
    with open(Path(RESULTS_COORDENADORIA_DIR, esec_teste, f"{esec_teste}_pert.json"), "w") as f:
        json.dump({
            "resultados_pert_dict": resultados_pert_dict,
            "relevancia_dos_riscos": relevancia_dos_riscos,
            "#exploracoes_consideradas": len(exploracoes_consideradas_df)
        }, f, indent=4)

    return resultados_pert_dict, relevancia_dos_riscos, len(exploracoes_consideradas_df)