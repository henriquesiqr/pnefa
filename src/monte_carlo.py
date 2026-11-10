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

# importação de bibliotecas
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import beta



DIRETORIO_RAIZ = Path(__file__).resolve().parent.parent

RESULTS_DIR = DIRETORIO_RAIZ / "results"



# Criar log
def setup_logger() -> logging.Logger:
    log_dir = RESULTS_DIR / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        file_handler = logging.FileHandler(log_dir / "monte_carlo.log")
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


logger = setup_logger()



# Centralizar fatores de risco e suas ordens para garantir consistência em todo o código
FATORES_ORDEM = [
    "gtas",
    "densidade_bovinos",
    "suinos",
    "lixoes",
    "eventos",
]



# Configuração de estilo para os gráficos
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")



def categorizar_risco(risco: float) -> str:
    """
    Categoriza o risco em Baixo, Médio ou Alto.
    """
    if risco > 66:
        return "Alto"

    if risco > 33:
        return "Médio"

    return "Baixo"



class MonteCarloFebreAftosa:
    """
    Simulação de Monte Carlo para análise de risco de Febre Aftosa
    em explorações agropecuárias usando árvore de cenários (2^5 = 32 cenários)
    
    Usa distribuição PERT para modelar incerteza nas probabilidades
    """

    def __init__(self, resultados_pert_dict, relevancia_dos_riscos, n_exploracoes, coordenadoria, esec, n_simulacoes=10000):
        self.n_simulacoes = n_simulacoes
        self.n_exploracoes = n_exploracoes  # Número total de explorações
        self.coordenadoria = coordenadoria
        self.esec = esec

        # Parâmetros PERT para cada fator (mínimo, mais provável, máximo)
        # Valores representam a probabilidade do fator ser "Alto"
        self.parametros_pert = {
            "gtas": resultados_pert_dict["gtas"],
            "densidade_bovinos": resultados_pert_dict["densidade_bovinos"],
            "suinos": resultados_pert_dict["suinos"],
            "eventos": resultados_pert_dict["eventos"],
            "lixoes": resultados_pert_dict["lixoes"],
        }

        # ===============================
        # Cenários guiados por especialista (stress)
        # ===============================

        # padrões no formato do código de cenário
        # proporção = fração das simulações
        self.padroes_especialista = {
            'AABBB': 0.05,  # 5% das simulações
        }

        # pré-processamento
        self._padroes_lista = list(self.padroes_especialista.keys())
        self._padroes_pesos = np.array(list(self.padroes_especialista.values()))
        self._peso_total_especialista = self._padroes_pesos.sum()
        ##############################################################

        # imprimir os parametros_pert para conferência
        logger.info("Parâmetros PERT carregados:")
        for fator, params in self.parametros_pert.items():
            logger.info(f"  {fator}: min={params['min']}, mode={params['mode']}, max={params['max']}")
        
        # Pesos de risco para cada fator (quanto contribui para o risco total)
        self.pesos_risco = relevancia_dos_riscos

        # imprimir os pesos de risco para conferência
        logger.info("Pesos de risco carregados:")
        for fator, peso in self.pesos_risco.items():
            logger.info(f"  {fator}: peso={peso}")
        
        self.resultados = None
        self.df_simulacoes = None


    def _output_dir(self) -> Path:
        """
        Retorna o diretório de saída da coordenadoria/ESEC.
        """
        output_dir = RESULTS_DIR / self.coordenadoria / self.esec
        output_dir.mkdir(parents=True, exist_ok=True)

        return output_dir


    def _fatores_from_codigo(self, codigo):
        """
        Constrói o dicionário de fatores a partir do código A/B
        """
        return {
            fator: ('Alto' if codigo[i] == 'A' else 'Baixo')
            for i, fator in enumerate(FATORES_ORDEM)
        }


    def plotar_resultados(self):
        """Gera visualizações dos resultados"""
        if self.resultados is None:
            logger.warning("Execute a simulação primeiro!")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Análise de Risco - Febre Aftosa (Monte Carlo)', 
                     fontsize=16, fontweight='bold')
        
        # 1. Top 15 cenários mais prováveis
        ax1 = axes[0, 0]
        top15 = self.resultados.head(15)
        ax1.barh(range(len(top15)), top15['probabilidade_%'])
        ax1.set_yticks(range(len(top15)))
        ax1.set_yticklabels(top15.index)
        ax1.set_xlabel('Probabilidade (%)')
        ax1.set_title('Top 15 Cenários Mais Prováveis')
        ax1.invert_yaxis()
        
        # Adicionar valores nas barras
        for i, v in enumerate(top15['probabilidade_%']):
            ax1.text(v + 0.1, i, f'{v:.1f}%', va='center')
        
        # 2. Distribuição de risco
        ax2 = axes[0, 1]
        ax2.hist(self.df_simulacoes['risco'], bins=30, edgecolor='black', alpha=0.7)
        ax2.axvline(self.df_simulacoes['risco'].mean(), color='red', 
                   linestyle='--', linewidth=2, label=f"Média: {self.df_simulacoes['risco'].mean():.1f}")
        ax2.set_xlabel('Escore de Risco')
        ax2.set_ylabel('Frequência')
        ax2.set_title('Distribuição do Risco')
        ax2.legend()
        
        # 3. Categorias de risco (Pizza)
        ax3 = axes[1, 0]
        categorias = self.df_simulacoes['categoria_risco'].value_counts()
        colors = {'Baixo': '#2ecc71', 'Médio': '#f39c12', 'Alto': '#e74c3c'}
        ax3.pie(categorias.values, labels=categorias.index, autopct='%1.1f%%',
               colors=[colors[cat] for cat in categorias.index], startangle=90)
        ax3.set_title('Categorias de Risco')

        # 4. Risco médio por cenário (scatter)
        ax4 = axes[1, 1]
        x = range(len(self.resultados))
        y = self.resultados['risco_medio']
        colors_risk = ['#2ecc71' if r <= 33 else '#f39c12' if r <= 66 else '#e74c3c' 
                      for r in y]
        # resultados de 2 em 2 para melhor visualização
        ax4.scatter(x, y, c=colors_risk, s=self.resultados['risco_medio'] * 10, alpha=0.7)
        ax4.set_xlabel('Cenários')
        ax4.set_ylabel('Risco Médio')
        ax4.set_title('Risco Médio por Cenário')

        plt.tight_layout()

        # salvar figura

        output_dir = self._output_dir()

        plt.savefig(
            output_dir / f"{self.esec}_analise_risco_febre_aftosa.png",
            dpi=300,
            bbox_inches="tight",
        )
        
        plt.close(fig)


    def pert_distribution(self, minimum, mode, maximum, size=1):
        """
        Gera amostras da distribuição PERT clássica (Beta reescalada)
        """
        minimum, mode, maximum = sorted([minimum, mode, maximum])
        if minimum > mode or mode > maximum:
            raise ValueError("Deve satisfazer: minimum <= mode <= maximum")

        if minimum == maximum:
            return np.full(size, minimum)

        lamb = 4  # PERT clássico

        alpha = 1 + lamb * (mode - minimum) / (maximum - minimum)
        beta_param = 1 + lamb * (maximum - mode) / (maximum - minimum)

        samples = beta.rvs(alpha, beta_param, size=size)
        return minimum + samples * (maximum - minimum)

    
    def sortear_fator(self, nome_fator):
        """
        Sorteia se um fator é Alto ou Baixo usando distribuição PERT
        
        1. Sorteia uma probabilidade da distribuição PERT
        2. Usa essa probabilidade para decidir se o fator é Alto ou Baixo
        """
        params = self.parametros_pert[nome_fator]
        
        # Sortear probabilidade usando PERT
        prob_alto = self.pert_distribution(
            params['min'], 
            params['mode'], 
            params['max'],
            size=1
        )[0]
        
        # Decidir se é Alto ou Baixo baseado na probabilidade sorteada
        return 'Alto' if np.random.random() < prob_alto else 'Baixo'
    

    def calcular_sensibilidade_componente(self, componentes_ativos):
        """
        Calcula SeU (Sensibilidade Unitária) e CSe (Sensibilidade Composta)
        
        Parâmetros:
        -----------
        componentes_ativos : list
            Lista com os nomes dos fatores que estão "Alto"
            
        Retorna:
        --------
        seu : float
            Sensibilidade Unitária (produto das sensibilidades)
        cse : float
            Sensibilidade Composta para n explorações
        sampled_sensitivities : dict
            Sensibilidades individuais sorteadas para cada componente
        """
        # Sortear sensibilidade de cada componente ativo usando PERT
        sampled_sensitivities = {}
        
        for componente in componentes_ativos:
            params = self.parametros_pert[componente]

            sens = self.pert_distribution(
                params["min"],
                params["mode"],
                params["max"],
                size=1,
            )[0]

            sampled_sensitivities[componente] = sens
        
        if len(sampled_sensitivities) > 0:
            probs = np.array(list(sampled_sensitivities.values()))
            seu = 1.0 - np.prod(1.0 - probs)
        else:
            seu = 0.0
        
        # CSe = 1 - (1 - SeU)^n
        n = self.n_exploracoes
        
        # Para valores muito grandes de n, (1-SeU)^n pode ser extremamente pequeno
        # Usamos uma aproximação mais estável numericamente
        if seu > 0:
            cse = -np.expm1(n * np.log1p(-seu))
        else:
            cse = 0.0
        
        return seu, cse, sampled_sensitivities


    def calcular_risco(self, fatores, seu):
        """
        Calcula o escore de risco residual (0-100),
        considerando a capacidade de detecção (SeU).
        """
        risco_base = 0.0

        for fator, valor in fatores.items():
            if valor == "Alto":
                risco_base += self.pesos_risco[fator] * 100

        # Risco residual: quanto maior a sensibilidade, menor o risco
        risco_ajustado = risco_base * (1.0 - seu)

        return risco_ajustado


    def gerar_codigo_cenario(self, fatores):
        """
        Gera código do cenário (ex: AABBA)
        A = Alto, B = Baixo
        Ordem: Movimentação, Densidade, Alimentação, Lixões, Eventos
        """
        return "".join(
            "A" if fatores[fator] == "Alto" else "B"
            for fator in FATORES_ORDEM
        )
    
    def gerar_top_cenarios(self, n: int = 10) -> pd.DataFrame:
        """
        Gera dataframe com os principais cenários e seus fatores decodificados.
        """
        top_cenarios = self.resultados.head(n).reset_index()

        fatores_df = pd.DataFrame([
            self._fatores_from_codigo(codigo)
            for codigo in top_cenarios["codigo_cenario"]
        ])

        return pd.concat([top_cenarios, fatores_df], axis=1)


    def exportar_top_cenarios(self, n: int = 10) -> Path | None:
        """
        Exporta os principais cenários para CSV.
        """
        if self.resultados is None:
            logger.info("Execute a simulação primeiro!")
            return

        self.top_cenarios = self.gerar_top_cenarios(n=n)

        output_dir = self._output_dir()
        output_path = output_dir / f"{self.esec}_top_{n}.csv"

        self.top_cenarios.to_csv(output_path, index=False)

        logger.info(f"\nTop {n} cenários exportados para: {output_path}")

        return output_path
    
    
    def executar_simulacao(self):
        """Executa n simulações de Monte Carlo com cálculo de sensibilidade"""
        
        simulacoes = []
        
        for i in range(self.n_simulacoes):
            u = np.random.random()
            origem_cenario = None

            # -------------------------------
            # 1) Cenário guiado por especialista
            # -------------------------------
            if u < self._peso_total_especialista:

                codigo_escolhido = np.random.choice(
                    self._padroes_lista,
                    p=self._padroes_pesos / self._peso_total_especialista
                )

                fatores = self._fatores_from_codigo(codigo_escolhido)
                origem_cenario = 'especialista'

            # -------------------------------
            # 2) Cenário estatístico (PERT)
            # -------------------------------
            else:
                fatores = {
                    nome: self.sortear_fator(nome)
                    for nome in self.parametros_pert.keys()
                }
                origem_cenario = 'estatistico'
                    
            # Identificar componentes ativos (fatores que estão "Alto")
            componentes_ativos = [nome for nome, valor in fatores.items() if valor == 'Alto']
            
            # Calcular sensibilidade
            seu, cse, sampled_sens = self.calcular_sensibilidade_componente(componentes_ativos)
            
            # Gerar código do cenário (nó da árvore)
            codigo_cenario = self.gerar_codigo_cenario(fatores)
            
            # Calcular risco (agora incorpora SeU)
            risco = self.calcular_risco(fatores, seu)

            if (i + 1) % 1000 == 0:
                logger.info(
                    f"Simulação {i + 1}/{self.n_simulacoes}: "
                    f"Cenário {codigo_cenario}, Risco: {risco:.2f}, "
                    f"SeU: {seu:.4f}, CSe: {cse:.4f}"
                )
            
            # Categorizar risco
            categoria_risco = categorizar_risco(risco)
            
            simulacoes.append({
                'simulacao_id': i + 1,
                'codigo_cenario': codigo_cenario,
                'origem_cenario': origem_cenario,  
                'risco': risco,
                'categoria_risco': categoria_risco,
                'seu': seu,
                'cse': cse,
                'n_componentes_ativos': len(componentes_ativos),
                **fatores
            })
        
        # Criar DataFrame com os resultados
        self.df_simulacoes = pd.DataFrame(simulacoes)
        
        # Calcular estatísticas por cenário
        self.resultados = self._calcular_estatisticas()

        df_stress = self.df_simulacoes[self.df_simulacoes['origem_cenario'] == 'especialista']
        logger.info("\n--- CENÁRIOS DE STRESS (ESPECIALISTA) ---")
        logger.info(f"Total: {len(df_stress)}")
        logger.info(f"Risco médio: {df_stress['risco'].mean():.1f}")
        logger.info(f"Risco máximo: {df_stress['risco'].max():.1f}")
        
        logger.info("Simulação concluída!")
        logger.info(f"Cenários únicos encontrados: {len(self.resultados)} de 32 possíveis")
        
        return self.resultados
    

    def _calcular_estatisticas(self):
        """Calcula estatísticas agregadas por cenário"""
        stats = self.df_simulacoes.groupby('codigo_cenario').agg({
            'simulacao_id': 'count',
            'risco': 'mean',
            'seu': 'mean',
            'cse': 'mean',
            'n_componentes_ativos': 'mean'
        }).rename(columns={
            'simulacao_id': 'ocorrencias',
            'risco': 'risco_medio',
            'seu': 'seu_medio',
            'cse': 'cse_medio',
            'n_componentes_ativos': 'n_comp_ativos_medio'
        })
        
        stats['probabilidade_%'] = (stats['ocorrencias'] / self.n_simulacoes * 100).round(2)
        stats['risco_medio'] = stats['risco_medio'].round(1)
        stats['seu_medio'] = stats['seu_medio'].round(4)
        stats['cse_medio'] = stats['cse_medio'].round(4)
        stats['n_comp_ativos_medio'] = stats['n_comp_ativos_medio'].round(1)
        stats = stats.sort_values('ocorrencias', ascending=False)
        
        return stats
    

    def exibir_resumo(self):
        """Exibe resumo estatístico da simulação"""
        if self.resultados is None:
            logger.warning("Execute a simulação primeiro!")
            return
        
        logger.info("\n" + "="*70)
        logger.info("RESUMO DA SIMULAÇÃO - RISCO DE FEBRE AFTOSA")
        logger.info("\n" + "="*70)
        logger.info("SOBRE SENSIBILIDADE")
        logger.info("="*70)
        logger.info("SeU (Sensibilidade Unitária):")
        logger.info("  • Produto das sensibilidades dos componentes ativos")
        logger.info("  • Representa a probabilidade de detectar em uma unidade")
        logger.info("  • Quanto mais fatores 'Alto', menor tende a ser o SeU")
        logger.info("\nCSe (Sensibilidade Composta):")
        logger.info("  • CSe = 1 - (1 - SeU)^n")
        logger.info("  • Sensibilidade do sistema considerando n unidades")
        logger.info("  • Aumenta com o número de unidades testadas")
        logger.info("="*70)
            
        logger.info(f"\nNúmero de simulações: {self.n_simulacoes}")
        logger.info(f"Cenários únicos encontrados: {len(self.resultados)} de 32 possíveis")
        
        logger.info("\n--- ESTATÍSTICAS DE RISCO ---")
        logger.info(f"Risco médio geral: {self.df_simulacoes['risco'].mean():.1f}")
        logger.info(f"Risco máximo: {self.df_simulacoes['risco'].max():.1f}")
        logger.info(f"Risco mínimo: {self.df_simulacoes['risco'].min():.1f}")
        logger.info(f"Desvio padrão: {self.df_simulacoes['risco'].std():.1f}")
        
        logger.info("\n--- ESTATÍSTICAS DE SENSIBILIDADE ---")
        logger.info(f"SeU médio: {self.df_simulacoes['seu'].mean():.4f}")
        logger.info(f"SeU máximo: {self.df_simulacoes['seu'].max():.4f}")
        logger.info(f"SeU mínimo: {self.df_simulacoes['seu'].min():.4f}")
        logger.info(f"CSe médio: {self.df_simulacoes['cse'].mean():.4f}")
        logger.info(f"Componentes ativos (média): {self.df_simulacoes['n_componentes_ativos'].mean():.1f}")
        
        logger.info("\n--- DISTRIBUIÇÃO POR CATEGORIA ---")
        categorias = self.df_simulacoes['categoria_risco'].value_counts()
        for cat, count in categorias.items():
            logger.info(f"{cat}: {count} ({count/self.n_simulacoes*100:.1f}%)")
        
        logger.info("\n--- TOP 10 CENÁRIOS MAIS PROVÁVEIS ---")
        logger.info(self.resultados.head(10).to_string())


    def exportar_csv(self, nome_arquivo: str | Path = "resultados_monte_carlo.csv"):
        """
        Exporta resultados para CSV.
        """
        if self.resultados is None:
            logger.info("Execute a simulação primeiro!")
            return

        nome_arquivo = Path(nome_arquivo)

        self.resultados.to_csv(nome_arquivo)
        logger.info(f"\nResultados exportados para: {nome_arquivo}")

        nome_detalhado = nome_arquivo.with_name(
            f"{nome_arquivo.stem}_detalhado{nome_arquivo.suffix}"
        )

        self.df_simulacoes.to_csv(nome_detalhado, index=False)
        logger.info(f"Simulações detalhadas exportadas para: {nome_detalhado}")
    

    def plotar_distribuicoes_pert(self):
        """Visualiza as distribuições PERT de cada fator"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('Distribuições PERT - Probabilidade de cada Fator ser "Alto"', 
                     fontsize=14, fontweight='bold')
        
        fatores = FATORES_ORDEM
        
        for idx, fator in enumerate(fatores):
            ax = axes[idx // 3, idx % 3]
            params = self.parametros_pert[fator]
            
            # Gerar 10000 amostras para visualização suave
            samples = self.pert_distribution(
                params["min"],
                params["mode"],
                params["max"],
                size=10000,
            )
            
            # Plotar histograma
            ax.hist(samples, bins=50, density=True, alpha=0.7, edgecolor='black')
            
            # Marcar os três pontos (mín, mode, máx)
            ax.axvline(params['min'], color='green', linestyle='--', 
                      linewidth=2, label=f"Mín: {params['min']:.2f}")
            ax.axvline(params['mode'], color='red', linestyle='--', 
                      linewidth=2, label=f"Moda: {params['mode']:.2f}")
            ax.axvline(params['max'], color='orange', linestyle='--', 
                      linewidth=2, label=f"Máx: {params['max']:.2f}")
            
            ax.set_xlabel('Probabilidade de ser "Alto"')
            ax.set_ylabel('Densidade')
            ax.set_title(fator.replace('_', ' ').title())
            ax.legend(fontsize=8)
            ax.set_xlim(0, 1)
        
        # Remover subplot extra
        fig.delaxes(axes[1, 2])
        
        plt.tight_layout()
        
        output_dir = self._output_dir()

        plt.savefig(
            output_dir / f"{self.esec}_distribuicoes_pert_fatores.png",
            dpi=300,
            bbox_inches="tight",
        )

        plt.close(fig)

        logger.info(f"\nDistribuições PERT salvas como: {self.esec}_distribuicoes_pert_fatores.png")

        
    def analisar_fatores(self):
        """Analisa a influência de cada fator no risco"""
        if self.df_simulacoes is None:
            logger.info("Execute a simulação primeiro!")
            return
        
        logger.info("\n" + "="*70)
        logger.info("ANÁLISE DE INFLUÊNCIA DOS FATORES")
        logger.info("="*70)
        
        fatores = FATORES_ORDEM

        for fator in fatores:
            risco_alto = self.df_simulacoes[self.df_simulacoes[fator] == 'Alto']['risco'].mean()
            risco_baixo = self.df_simulacoes[self.df_simulacoes[fator] == 'Baixo']['risco'].mean()
            diferenca = risco_alto - risco_baixo
            
            logger.info(f"\n{fator.replace('_', ' ').title()}:")
            logger.info(f"  Risco médio quando Alto: {risco_alto:.1f}")
            logger.info(f"  Risco médio quando Baixo: {risco_baixo:.1f}")
            logger.info(f"  Diferença: {diferenca:.1f} ({diferenca/risco_baixo*100:.1f}% de aumento)")


    def selecionar_top_cenarios_com_fator_alto(
        self,
        min_probabilidade: float = 5.0,
        n: int = 3,
    ) -> pd.DataFrame:
        """
        Seleciona cenários com pelo menos um fator alto e probabilidade mínima.
        """
        if self.resultados is None:
            logger.info("Execute a simulação primeiro!")
            return pd.DataFrame()

        codigos_com_alto = [
            codigo
            for codigo in self.resultados.index
            if "A" in codigo
        ]

        resultados_filtrados = self.resultados.loc[codigos_com_alto]

        return resultados_filtrados[
            resultados_filtrados["probabilidade_%"] > min_probabilidade
        ].head(n)


# ==============================================================================
# EXEMPLO DE USO
# ==============================================================================

def main(resultados_pert_dict, relevancia_dos_riscos, n_exploracoes, coordenadoria, esec, n_simulacoes=10000):

    # Criar instância da simulação
    mc = MonteCarloFebreAftosa(resultados_pert_dict, relevancia_dos_riscos, n_exploracoes, coordenadoria, esec, n_simulacoes=n_simulacoes)
    
    # Visualizar as distribuições PERT configuradas
    logger.info("Visualizando distribuições PERT...")
    mc.plotar_distribuicoes_pert()
    
    # Executar simulação
    resultados = mc.executar_simulacao()
    
    # Exibir resumo
    mc.exibir_resumo()

    # Exportar cenários
    mc.exportar_top_cenarios(n=10)
    
    # Analisar influência dos fatores
    mc.analisar_fatores()
    
    # Gerar gráficos
    mc.plotar_resultados()
    
    # Exportar para CSV
    output_dir = mc._output_dir()

    mc.exportar_csv(
        output_dir / f"{mc.esec}_resultados.csv"
    )
    # Selecionar as TOP3 de maiores probabilidades, com algum fator Alto
    top3_cenarios = mc.selecionar_top_cenarios_com_fator_alto(
        min_probabilidade=5.0,
        n=3,
    )

    logger.info("\nTOP 3 CENÁRIOS COM MAIOR PROBABILIDADE E FATOR ALTO:")
    logger.info(top3_cenarios)    
    logger.info("\n" + "="*70)
    logger.info("INTERPRETAÇÃO DOS CÓDIGOS DE CENÁRIO")
    logger.info("="*70)
    logger.info("Cada cenário é identificado por 5 letras (A=Alto, B=Baixo):")
    logger.info("  Posição 1: Movimentação de Bovinos")
    logger.info("  Posição 2: Densidade de Bovinos")
    logger.info("  Posição 3: Alimentação de Suínos")
    logger.info("  Posição 4: Proximidade de Lixões")
    logger.info("  Posição 5: Proximidade de Eventos")
    logger.info("\nExemplo: AABAB = Alta movimentação, Alta densidade, Baixa alimentação,")
    logger.info("                 Alta proximidade de lixões, Baixa proximidade de eventos")
    logger.info("\n" + "="*70)
    logger.info("SOBRE A DISTRIBUIÇÃO PERT")
    logger.info("="*70)
    logger.info("PERT (Program Evaluation and Review Technique) modela incerteza usando:")
    logger.info("  • Mínimo: valor mais otimista")
    logger.info("  • Moda: valor mais provável (maior peso)")
    logger.info("  • Máximo: valor mais pessimista")
    logger.info("\nÉ mais realista que distribuições uniformes, pois:")
    logger.info("  [CHECK] Concentra probabilidade no valor mais provável")
    logger.info("  [CHECK] Permite assimetria (moda não precisa estar no centro)")
    logger.info("  [CHECK] Reflete conhecimento especializado sobre os fatores")
    logger.info("="*70)

    return mc.top_cenarios