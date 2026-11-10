import os
import pandas as pd
from pathlib import Path
import math
import pulp

def seleciona_propriedades_na_otimalidade(exploracoes_selecionadas_dict,
    codigo_maior_prob, cenarios_de_especialista, quantidade_de_movimentos_dict, 
    quantidade_de_bovinos_movimentados_dict, total_de_bovinos_movimentados,
    threshold_risk, total_de_propriedades_cenarios_especialistas_dict, 
    propriedades_por_municipio_dict, lower_bound_propriedades_por_municipio,
    lista_de_propriedades, propriedades_df_filtered):
    #print("#### Modelo matemático ####")
    propriedades_validas = set()

    Big_M = 1e6
    
    modelo = pulp.LpProblem('seleciona_propriedades', pulp.LpMaximize)
    
    # variáveis de decisão
    x_vars = pulp.LpVariable.dicts('x', lista_de_propriedades, cat="Binary")
    penalty_vars = pulp.LpVariable.dicts('penalty', cenarios_de_especialista, lowBound=0, cat='Integer')
    # função objetivo
    modelo += pulp.lpSum([quantidade_de_movimentos_dict[cod_propriedade] * x_vars[cod_propriedade] 
        + (quantidade_de_bovinos_movimentados_dict[cod_propriedade] / total_de_bovinos_movimentados) * x_vars[cod_propriedade] for cod_propriedade in lista_de_propriedades]) - pulp.lpSum([Big_M * penalty_vars[codigo] for codigo in cenarios_de_especialista])

    #for cod_propriedade in lista_de_propriedades:
    #    print(f"cod_propriedade: {cod_propriedade}\t{quantidade_de_movimentos_dict[cod_propriedade]}\t{quantidade_de_bovinos_movimentados_dict[cod_propriedade]}")

    #print(f"threshold_risk = {threshold_risk}")

    # restrição 1
    #print("restrição 1")
    #print(f"codigo_maior_prob = {codigo_maior_prob}")
    df_cenario_maior_prob = exploracoes_selecionadas_dict[codigo_maior_prob]
    lista_propriedades_maior_prob = df_cenario_maior_prob["codigo_da_propriedade"].tolist()
    propriedades_validas = (propriedades_validas | set(lista_propriedades_maior_prob))
    #print(f"len(lista_propriedades_maior_prob) = {len(lista_propriedades_maior_prob)}")
    #print(f"len(propriedades_validas) = {len(propriedades_validas)}")
    modelo += pulp.lpSum([x_vars[cod_propriedade] for cod_propriedade in lista_propriedades_maior_prob]) == threshold_risk

    # restrição 2
    #print("restrição 2")
    propriedades_por_cenarios_de_especialista = {
        codigo: exploracoes_selecionadas_dict[codigo]["codigo_da_propriedade"]
                    .unique()
                    .tolist()
        for codigo in cenarios_de_especialista
    }
    for codigo in cenarios_de_especialista:
        #print(f"propriedades_por_cenarios_de_especialista[{codigo}] = {len(propriedades_por_cenarios_de_especialista[codigo])}")
        propriedades_validas = (propriedades_validas | set(propriedades_por_cenarios_de_especialista[codigo]))
        #print(f"total_de_propriedades_cenarios_especialistas_dict[{codigo}] = {total_de_propriedades_cenarios_especialistas_dict[codigo]}")
        modelo += pulp.lpSum([x_vars[cod_propriedade] for cod_propriedade in propriedades_por_cenarios_de_especialista[codigo]]) <= total_de_propriedades_cenarios_especialistas_dict[codigo] + penalty_vars[codigo]

    # restrição 3
    #print("restrição 3")
    #print(f"lower_bound_propriedades_por_municipio = {lower_bound_propriedades_por_municipio}")
    #print(f"Total de municipios: ", len(propriedades_por_municipio_dict.keys()))
    
    for cod_municipio in propriedades_por_municipio_dict:
        intersecao = list(set(propriedades_por_municipio_dict[cod_municipio]) & set(propriedades_validas))
        #print(f"len(interseccao) = {len(intersecao)}")
        #print("cod_municipio = ", cod_municipio)
        modelo += pulp.lpSum([x_vars[cod_propriedade] for cod_propriedade in intersecao]) >= min(len(intersecao), lower_bound_propriedades_por_municipio)
    
    # restrição 4
    #print("restrição 4")
    propriedades_nao_validas = (set(lista_de_propriedades) - propriedades_validas)
    #print(f"len(lista_de_propriedades) = {len(lista_de_propriedades)}")
    #print(f"len(propriedades_validas) = {len(propriedades_validas)}")
    #print(f"len(propriedades_nao_validas) = {len(propriedades_nao_validas)}")
    for cod_propriedade in propriedades_nao_validas:
        #print("cod_propriedade", cod_propriedade)
        modelo += x_vars[cod_propriedade] == 0 

    # exluir propriedades que tem 'total_movimentacoes_gtas' == 0
    #print("exluir propriedades que tem 'total_movimentacoes_gtas' == 0")
    #for cod_propriedade in lista_de_propriedades:
    #    if(quantidade_de_movimentos_dict[cod_propriedade] == 0):
            #print("cod_propriedade", cod_propriedade)
    #        modelo += x_vars[cod_propriedade] == 0

    #modelo.writeLP("modelo.lp")

    modelo.solve(pulp.PULP_CBC_CMD(msg=False))
    '''
    for cod_propriedade in lista_de_propriedades:
        if(x_vars[cod_propriedade].value() >= 0.9):
            print(f"x_vars[{cod_propriedade}] = {x_vars[cod_propriedade].value()}")
    '''
    from pulp import LpStatus
    df_resultado = None
    if LpStatus[modelo.status] == "Optimal":
        
        propriedades_selecionadas = [
            i for i in x_vars
            if x_vars[i].value() is not None and x_vars[i].value() >= 0.9 and quantidade_de_movimentos_dict[i] > 0
        ]

        df_resultado = (
            propriedades_df_filtered[
                propriedades_df_filtered["codigo_da_propriedade"].isin(propriedades_selecionadas)
            ]
            .sort_values(
                by=["total_movimentacoes_gtas", "total_animais_gtas"],
                ascending=[False, False]
            )
        )
        return df_resultado

    else:
        print("Modelo não encontrou solução ótima.")
        return None


# ==========================================================
# 1) DEFINIÇÃO DO PADRÃO DO ESPECIALISTA
# ==========================================================

def cenario_especialista(codigo_cenario: str) -> bool:
    """
    Critério do especialista:
    retorna True se o cenário tiver pelo menos 2 riscos altos.
    Ex.: AABBB, ABABB, BAABB, AAABB, etc.
    """
    return codigo_cenario.count('A') >= 2 or codigo_cenario == "ABBBB"


PARAMS_ESPECIALISTA = {
    'quota_minima': 5,     # mínimo de propriedades vindas desses cenários
    'quota_maxima': 10
}


def main(simulacao_df, propriedades_df, diretorio_principal, coordenadoria, esec):

    # ==========================================================
    # 2) INICIALIZAÇÃO DOS CENÁRIOS VÁLIDOS
    # ==========================================================

    exploracoes_selecionadas_dict = {
        codigo: None
        for codigo in simulacao_df[simulacao_df['probabilidade_%'] >= 1]['codigo_cenario']
    }

    # armezenar o código do cenário com maior probabilidade
    df_filtrado = simulacao_df[simulacao_df['probabilidade_%'] >= 1]
    codigo_maior_prob = (
        df_filtrado[df_filtrado["codigo_cenario"] != "BBBBB"]
        .sort_values("probabilidade_%", ascending=False)
        .iloc[0]["codigo_cenario"]
    )

    cenarios_de_especialista_utilizados_dict = {
        codigo:False for codigo in exploracoes_selecionadas_dict.keys()
        if cenario_especialista(codigo) and codigo != codigo_maior_prob
    }
    cenarios_de_especialista = cenarios_de_especialista_utilizados_dict.keys()

    # ----------------------------------------------------------
    # probabilidade ajustada = estatística + especialista
    # ----------------------------------------------------------
    def peso_especialista(codigo_cenario: str,
                      peso_min: float = 1.0,
                      base: float = 1.5,
                      max_peso: float = 4.0) -> float:
        """
        Peso exponencial suave baseado no número de A's.
        """
        n_A = codigo_cenario.count('A')
        #print(f"Cenário {codigo_cenario}: número de A's = {n_A}")
        if(n_A > 1):
            peso = peso_min * (base ** n_A)
        else:
            peso = peso_min
        #print(f"Cenário {codigo_cenario}: peso calculado = {peso:.2f}")
        return min(peso, max_peso)

    def probabilidade_ajustada(codigo):
        prob = simulacao_df.loc[
            simulacao_df['codigo_cenario'] == codigo,
            'probabilidade_%'
        ].values[0]

        #print(f"Cenário {codigo}: probabilidade original = {prob:.2f}%")

        peso = peso_especialista(codigo)
        #print(f"Cenário {codigo}: peso do especialista = {peso:.2f}")
        #print(f"Cenário {codigo}: probabilidade ajustada = {prob * peso:.2f}%\n")
        return prob * peso

    # ordenar cenários por probabilidade ajustada
    exploracoes_selecionadas_dict = dict(sorted(
        exploracoes_selecionadas_dict.items(),
        key=lambda item: probabilidade_ajustada(item[0]),
        reverse=True
    ))

    # forçar 'BBBBB' como último
    if 'BBBBB' in exploracoes_selecionadas_dict:
        exploracoes_selecionadas_dict['BBBBB'] = exploracoes_selecionadas_dict.pop('BBBBB')

    # ==========================================================
    # 3) FILTRAR PROPRIEDADES POR ESEC
    # ==========================================================

    propriedades_df_filtered = propriedades_df[
        propriedades_df['esec'] == esec
    ]

    # ==========================================================
    # 4) ASSOCIAR PROPRIEDADES A CADA CENÁRIO
    # ==========================================================

    for codigo in exploracoes_selecionadas_dict.keys():
        #print(f"Processando cenário {codigo}...")
        gtas_nivel = simulacao_df.loc[
            simulacao_df['codigo_cenario'] == codigo, 'gtas'
        ].values[0].lower()

        densidade_nivel = simulacao_df.loc[
            simulacao_df['codigo_cenario'] == codigo, 'densidade_bovinos'
        ].values[0].lower()

        suinos_nivel = simulacao_df.loc[
            simulacao_df['codigo_cenario'] == codigo, 'suinos'
        ].values[0].lower()

        lixoes_nivel = simulacao_df.loc[
            simulacao_df['codigo_cenario'] == codigo, 'lixoes'
        ].values[0].lower()

        eventos_nivel = simulacao_df.loc[
            simulacao_df['codigo_cenario'] == codigo, 'eventos'
        ].values[0].lower()

        filtro = (
            (propriedades_df_filtered['risco_gtas'] == gtas_nivel) &
            (propriedades_df_filtered['risco_densidade_bovinos'] == densidade_nivel) &
            (propriedades_df_filtered['risco_suinos'] == suinos_nivel) &
            (propriedades_df_filtered['risco_lixoes'] == lixoes_nivel) &
            (propriedades_df_filtered['risco_eventos'] == eventos_nivel)
        )

        exploracoes_selecionadas_dict[codigo] = (
            propriedades_df_filtered.loc[filtro].reset_index(drop=True)
        )
    
    #print("movimentações - cenário ABBBB")
    #print(exploracoes_selecionadas_dict['ABBBB']["total_movimentacoes_gtas"].describe())

    # imprimir as propriedades associadas a ABBBB, com total_movimentacoes_gtas > 0
    #print("propriedades associadas a ABBBB com total_movimentacoes_gtas > 0")
    #print(exploracoes_selecionadas_dict['ABBBB'][exploracoes_selecionadas_dict['ABBBB']["total_movimentacoes_gtas"] > 0][["codigo_da_propriedade", "total_movimentacoes_gtas"]])

    # ==========================================================
    # 5) SALVAR CSVs POR CENÁRIO (mantido)
    # ==========================================================

    exploracoes_dir = os.path.join(diretorio_principal, esec)
    os.makedirs(exploracoes_dir, exist_ok=True)

    for codigo, df in exploracoes_selecionadas_dict.items():
        arq = Path(exploracoes_dir, f"{esec}_{codigo}_exploracoes_selecionadas.csv")
        df.to_csv(str(arq), index=False)

    # ==========================================================
    # 6) DEFINIÇÃO DO THRESHOLD (CAPACIDADE)
    # ==========================================================

    BASE_DIR = Path(__file__).resolve().parent.parent
    DIRETORIO_DADOS = BASE_DIR / "data"

    capacidade_esecs_arq = DIRETORIO_DADOS / "Capacidade_esecs.xls"
    
    capacidade_esecs_df = pd.read_excel(capacidade_esecs_arq, header=2)
    
    # padronizar nomes das colunas
    capacidade_esecs_df.columns = capacidade_esecs_df.columns.str.strip().str.upper()

    # padronizar conteúdo textual
    capacidade_esecs_df.columns = capacidade_esecs_df.columns.str.strip().str.upper()
    capacidade_esecs_df['CR'] = capacidade_esecs_df['CR'].ffill()
    capacidade_esecs_df['ESEC'] = capacidade_esecs_df['ESEC'].astype(str).str.strip().str.upper()
    esec = esec.strip().upper()

    #print(f"Calculando capacidade para ESEC: {esec}")
    capacidade_planejamento = capacidade_esecs_df.loc[
        capacidade_esecs_df['ESEC'] == esec, 'PLANEJAMENTO'
    ]

    capacidade_quantitativo = capacidade_esecs_df.loc[
        capacidade_esecs_df['ESEC'] == esec,
        'QUANTITATIVO NA LISTA ÁRVORE DE CENÁRIOS'
    ]

    capacidade_planejamento = (
        capacidade_planejamento.values[0]
        if not capacidade_planejamento.empty else 0
    )

    capacidade_quantitativo = (
        capacidade_quantitativo.values[0]
        if not capacidade_quantitativo.empty else 0
    )

    #########################################################

    threshold_risk = math.ceil(1.5*max(capacidade_planejamento, capacidade_quantitativo))
    termo_extra = 0
    #print(f"ANTES) threshold_risk = {threshold_risk}")
    #rint(f"ANTES) termo_extra = {termo_extra}")
    #rint(f"codigo_maior_prob = {codigo_maior_prob}")
    # priorizando a densidade bovina
    if(codigo_maior_prob == 'BABBB'):
        termo_extra = int(0.7*threshold_risk)
        threshold_risk = int(threshold_risk - termo_extra)
    #print(f"DEPOIS) threshold_risk = {threshold_risk}")
    #print(f"DEPOIS) termo_extra = {termo_extra}")
    #print(f"len(cenarios_de_especialista) = {len(cenarios_de_especialista)}")
    termo_dividido_por_especialista = int(termo_extra/len(cenarios_de_especialista))
    #print(f"termo_dividido_por_especialista = {termo_dividido_por_especialista}")
    quantidade_de_movimentos_dict = dict(
        zip(
            propriedades_df_filtered["codigo_da_propriedade"],
            propriedades_df_filtered["total_movimentacoes_gtas"]
        )
    )


    quantidade_de_bovinos_movimentados_dict = dict(
        zip(
            propriedades_df_filtered["codigo_da_propriedade"],
            propriedades_df_filtered["total_animais_gtas"]
        )
    )

    total_de_bovinos_movimentados = propriedades_df_filtered["total_animais_gtas"].sum()

    total_de_propriedades_cenarios_especialistas_dict = {}
    probabilidade_ajustada_melhor_cenario = probabilidade_ajustada(codigo_maior_prob)
    for codigo in exploracoes_selecionadas_dict:
        if(cenario_especialista(codigo)):
            probabilidade_ajustada_especialista = probabilidade_ajustada(codigo)
            #print(f"Analisar - {codigo} - {probabilidade_ajustada_especialista} - {probabilidade_ajustada_melhor_cenario}")
            if(probabilidade_ajustada_especialista >= probabilidade_ajustada_melhor_cenario):
                total_de_propriedades_cenarios_especialistas_dict[codigo] = PARAMS_ESPECIALISTA['quota_maxima'] + termo_dividido_por_especialista
            else:
                total_de_propriedades_cenarios_especialistas_dict[codigo] = PARAMS_ESPECIALISTA['quota_minima'] + termo_dividido_por_especialista

    propriedades_por_municipio_dict = (
        propriedades_df_filtered
        .groupby("codigo_do_municipio")["codigo_da_propriedade"]
        .apply(lambda x: sorted(x))
        .to_dict()
    )

    lower_bound_propriedades_por_municipio = 5

    lista_de_propriedades = propriedades_df_filtered["codigo_da_propriedade"].tolist()

    #########################################################

    # ==========================================================
    # DEFINIÇÃO DOS CONJUNTOS

    # 1) exploracoes_selecionadas_dict: conjunto das linhas de 
    # propriedades_df_filtered de acordo com o codigo

    # 2) codigo_maior_prob: código com maior probabilidade sem
    # considerar probabilidade ajustada

    # 3) cenarios_de_especialista: lista de códigos de especialista

    # 4) quantidade_de_movimentos_dict: quantidade de movimentos
    # para cada propriedade

    # 5) quantidade_de_bovinos_movimentados_dict: quantidade de bovinos
    # movimentados para cada propriedade

    # 6) total_de_bovinos_movimentados: total de bovinos movimentados
    # em todas as GTAs

    # 7) threshold_risk: total de propriedades
    # a serem selecionas advindas do melhor cenário (sem probabilidade
    # ajustada)

    # 8) total_de_propriedades_cenarios_especialistas_dict: total de
    # propriedades que devem ser selecionadas dos cenários de 
    # especialistas

    # 9) propriedades_por_municipio_dict: quais propriedades por 
    # municipio

    # 10) lower_bound_propriedades_por_municipio: menor número de 
    # propriedades a serem selecionadas por município

    # 11) lista_de_propriedades: lista de todas as propriedades

    # 12) propriedades_df_filtered: todo o frame
    # ==========================================================

    df_resultado = seleciona_propriedades_na_otimalidade(exploracoes_selecionadas_dict,
        codigo_maior_prob, cenarios_de_especialista, quantidade_de_movimentos_dict, 
        quantidade_de_bovinos_movimentados_dict, total_de_bovinos_movimentados,
        threshold_risk, total_de_propriedades_cenarios_especialistas_dict, 
        propriedades_por_municipio_dict, lower_bound_propriedades_por_municipio,
        lista_de_propriedades, propriedades_df_filtered)

    if(df_resultado is None):
        #print("\tERRO: sol. factível não encontrada")
        arq_final = os.path.join(
            exploracoes_dir, f"{esec}_ERRO.txt"
        )
        #print(f"\t\t{arq_final}")

        exploracoes_dir_path = Path(exploracoes_dir)
        diretorio_pai = exploracoes_dir_path.parent

        arq_final2 = os.path.join(
            diretorio_pai, f"{esec}_ERRO.txt"
        )
        #print(f"\t\t{arq_final2}")
        
        # Escrevendo no arquivo
        with open(arq_final, 'w', encoding='utf-8') as f:
            f.write(f"Modelo não resolvido na ESEC: {esec}\n")

            # Escrevendo no arquivo
        with open(arq_final2, 'w', encoding='utf-8') as f:
            f.write(f"Modelo não resolvido na ESEC: {esec}\n")
    else:
        # ==========================================================
        # 9) SALVAR RESULTADO FINAL
        # ==========================================================

        arq_final = os.path.join(
            exploracoes_dir, f"{esec}_exploracoes_ordenadas_por_risco.csv"
        )

        df_resultado.to_csv(arq_final, index=False)
