import streamlit as st
import pandas as pd
import folium
import os
import glob
from streamlit_folium import st_folium
import numpy as np
from scipy.spatial import ConvexHull
import plotly.express as px

st.set_page_config(
    page_title="Dashboard de Roteamento",
    layout="wide"
)

PASTA_DADOS = r"" # Escreva o caminho da pasta que contem os dados aqui
ARQUIVO_CENARIO_ATUAL = r"" # Escreva o caminho do csv Propriedades_consideradas_FINAL.csv 

@st.cache_data
def carregar_dados(x_escolhido):
    caminho_dashboard = os.path.join(PASTA_DADOS, f"Dashboard_{x_escolhido}.csv")
    caminho_resultado = os.path.join(PASTA_DADOS, f"resultado_{x_escolhido}.csv")
    caminho_esec = os.path.join(PASTA_DADOS, f"ESEC_{x_escolhido}.csv") 
    
    df_resumo = pd.read_csv(caminho_dashboard)
    df_resultados = pd.read_csv(caminho_resultado)
    df_resultados = df_resultados.dropna(subset=['facilidade_lat', 'facilidade_lon'])
    df_esec = pd.read_csv(caminho_esec)
    
    df_baseline = pd.DataFrame()
    if os.path.exists(ARQUIVO_CENARIO_ATUAL):
        df_baseline = pd.read_csv(ARQUIVO_CENARIO_ATUAL)

    return df_resumo, df_resultados, df_esec, df_baseline

arquivos_encontrados = glob.glob(os.path.join(PASTA_DADOS, "Dashboard_*.csv"))

if not arquivos_encontrados:
    st.warning(f"Nenhum arquivo encontrado na pasta '{PASTA_DADOS}'. Execute o algoritmo primeiro!")
else:
    opcoes_x = []
    for caminho in arquivos_encontrados:
        nome_arquivo = os.path.basename(caminho)
        nome_x = nome_arquivo.replace("Dashboard_", "").replace(".csv", "")
        opcoes_x.append(nome_x)

    st.sidebar.title("Filtros")
    x_escolhido = st.sidebar.selectbox("1. Selecione o arquivo de resultados:", opcoes_x)
    
    df_resumo, df_resultados, df_esec, df_baseline = carregar_dados(x_escolhido)

    crs_disponiveis = sorted(df_resultados["CR_processada"].unique())
    cr_escolhida = st.sidebar.selectbox("2. Selecione a Coordenadoria (CR):", crs_disponiveis)

    st.sidebar.markdown("---")
    tipo_mapa = st.sidebar.radio(
        "Visualização do Mapa:",
        ("Áreas de Cobertura (Mais leve)", "Linhas (Detalhado)")
    )

    df_resultado_filtrado = df_resultados[df_resultados["CR_processada"] == cr_escolhida]
    df_resumo_filtrado = df_resumo[df_resumo["CR_processada"] == cr_escolhida]
    df_esec_filtrado = df_esec[df_esec["CR_processada"] == cr_escolhida].copy()

    if "Cenario" not in df_esec_filtrado.columns:
        df_esec_filtrado["Cenario"] = "Otimizado (PuLP)"

    df_baseline_filtrado = pd.DataFrame()
    if not df_baseline.empty:
        df_baseline_filtrado = df_baseline[df_baseline["CR_processada"] == cr_escolhida].copy()

    st.title(f"Mapa de Alocação Otimizada: {cr_escolhida}")
    
    if df_resultado_filtrado.empty:
        st.info("Não há dados de mapa para mostrar nesta coordenadoria.")
    else:
        centro_lat = df_resultado_filtrado["proprieade_lat"].mean()
        centro_lon = df_resultado_filtrado["proprieade_lon"].mean()
        
        mapa = folium.Map(location=[centro_lat, centro_lon], zoom_start=8)
        cores = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', 
                 '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe']
        
        esecs_agrupadas = df_resultado_filtrado.groupby(['facilidade_lat', 'facilidade_lon', 'facilidade_nome'])
        
        cor_idx = 0
        for (lat_faci, lon_faci, nome_faci), grupo in esecs_agrupadas:
            cor_atual = cores[cor_idx % len(cores)]
            cor_idx += 1
            
            folium.Marker(
                location=[lat_faci, lon_faci],
                icon=folium.Icon(color="green", icon="home", prefix="fa"),
                popup=f"<b>ESEC:</b> {nome_faci}",
                tooltip=f"ESEC: {nome_faci}"
            ).add_to(mapa)

            if tipo_mapa == "Áreas de Cobertura (Mais leve)":
                pontos = grupo[['proprieade_lat', 'proprieade_lon']].values
                if len(pontos) >= 3:
                    hull = ConvexHull(pontos)
                    pontos_borda = pontos[hull.vertices]
                    pontos_borda = np.append(pontos_borda, [pontos_borda[0]], axis=0)
                    
                    folium.Polygon(
                        locations=pontos_borda,
                        color=cor_atual, weight=2, fill=True, fill_color=cor_atual, fill_opacity=0.3
                    ).add_to(mapa)
                
                clientes_risco = grupo[grupo['proprieade_risco'] == 1]
                for _, cliente in clientes_risco.iterrows():
                    folium.CircleMarker(
                        location=[cliente['proprieade_lat'], cliente['proprieade_lon']],
                        radius=3, color="red", fill=True, fill_opacity=0.8
                    ).add_to(mapa)
                    
            else: # VISUALIZAÇÃO DE LINHAS
                for _, cliente in grupo.iterrows():
                    coord_cliente = [cliente['proprieade_lat'], cliente['proprieade_lon']]
                    risco = cliente.get('proprieade_risco', 0)
                    cor_cliente = "red" if risco == 1 else "blue"
                    
                    folium.CircleMarker(
                        location=coord_cliente, radius=3, color=cor_cliente, fill=True, fill_opacity=0.7
                    ).add_to(mapa)
                    
                    folium.PolyLine(
                        locations=[coord_cliente, [lat_faci, lon_faci]],
                        color="gray", weight=1.0, opacity=0.5
                    ).add_to(mapa)

        st_data = st_folium(fig=mapa, use_container_width=True, height=550, returned_objects=[])

    st.markdown("---")
    st.subheader(f"Indicadores de Desempenho (Modelo PuLP) - {cr_escolhida}")

    if not df_resumo_filtrado.empty:
        resumo_dict = df_resumo_filtrado.iloc[0].to_dict()
        if "CR_processada" in resumo_dict:
            del resumo_dict["CR_processada"]

        NUM_COLUNAS = 4 
        colunas_metricas = st.columns(NUM_COLUNAS)
        
        idx = 0
        for chave, valor in resumo_dict.items():
            nome_amigavel = str(chave).replace("_", " ").title()
            if isinstance(valor, float):
                valor_formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                valor_formatado = str(valor)

            colunas_metricas[idx % NUM_COLUNAS].metric(label=nome_amigavel, value=valor_formatado)
            idx += 1
    else:
        st.info("Nenhum dado gerencial disponível para esta coordenadoria.")

    st.markdown("---")
    st.subheader(f"Distribuição do Modelo Otimizado por ESEC - {cr_escolhida}")

    if not df_esec_filtrado.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig_clientes = px.pie(
                df_esec_filtrado, values="Propriedades_Atendidas", names="ESEC",
                title="Distribuição de Propriedades", hole=0.3
            )
            st.plotly_chart(fig_clientes, use_container_width=True)

        with col2:
            fig_contrib = px.pie(
                df_esec_filtrado, values="Contribuicao_FO", names="ESEC",
                title="Contribuição na Distância Total (FO)", hole=0.3
            )
            st.plotly_chart(fig_contrib, use_container_width=True)

    st.markdown("---")
    st.subheader(f"Comparação: Cenário Atual vs Otimizado - {cr_escolhida}")

    if not df_baseline_filtrado.empty and not df_esec_filtrado.empty:

        fo_baseline = df_baseline_filtrado["Contribuicao_FO"].sum()
        fo_otimizado = df_esec_filtrado["Contribuicao_FO"].sum()
        
        if fo_baseline > 0:
            economia_abs = fo_baseline - fo_otimizado
            economia_pct = (economia_abs / fo_baseline) * 100
        else:
            economia_abs = 0
            economia_pct = 0
            
        st.markdown(" Ganho de Eficiência (Redução de Distância Total)")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        
        str_fo_base = f"{fo_baseline:,.2f} km".replace(",", "X").replace(".", ",").replace("X", ".")
        str_fo_otim = f"{fo_otimizado:,.2f} km".replace(",", "X").replace(".", ",").replace("X", ".")

        delta_abs = fo_otimizado - fo_baseline
        str_delta = f"{delta_abs:,.2f} km".replace(",", "X").replace(".", ",").replace("X", ".")
        
        col_m1.metric("Distância Atual (Baseline)", str_fo_base)
        col_m2.metric("Distância Otimizada (PuLP)", str_fo_otim, delta=str_delta, delta_color="inverse")
        col_m3.metric("Economia Percentual", f"{economia_pct:.2f}%", delta="Redução", delta_color="normal")
        
        st.markdown("<br>", unsafe_allow_html=True) 

        df_comparativo = pd.concat([df_baseline_filtrado, df_esec_filtrado], ignore_index=True)

        col_comp1, col_comp2 = st.columns(2)

        with col_comp1:
            fig_comp_prop = px.bar(
                df_comparativo, x="ESEC", y="Propriedades_Atendidas", color="Cenario",
                barmode="group", title="Comparativo: Propriedades Atendidas por ESEC",
                color_discrete_map={"Atual (Baseline)": "#1f77b4", "Otimizado (PuLP)": "#2ca02c"}
            )
            st.plotly_chart(fig_comp_prop, use_container_width=True)

        with col_comp2:
            fig_comp_dist = px.bar(
                df_comparativo, x="ESEC", y="Contribuicao_FO", color="Cenario",
                barmode="group", title="Comparativo: Distância Total por ESEC",
                color_discrete_map={"Atual (Baseline)": "#1f77b4", "Otimizado (PuLP)": "#2ca02c"}
            )
            st.plotly_chart(fig_comp_dist, use_container_width=True)

        st.markdown("**Tabela de Dados Comparativa:**")
        
        tabela_pivot = df_comparativo.pivot_table(
            index="ESEC", columns="Cenario", 
            values=["Propriedades_Atendidas", "Contribuicao_FO"], fill_value=0
        )
        st.dataframe(tabela_pivot, use_container_width=True)

    elif df_baseline_filtrado.empty:
        st.warning(" Arquivo 'Baseline_Cenario_Atual_Completo.csv' não encontrado ou sem dados para esta CR. Rode o script de Baseline primeiro para ver a comparação!")