Visão Geral

Este projeto é um painel interativo construído com Python e Streamlit para visualizar e analisar a alocação geográfica de propriedades rurais às Unidades Administrativas (ESECs). Ele foi desenvolvido para comparar o cenário atual de designação (Baseline) com cenários otimizados (como modelos matemáticos de distância), facilitando a tomada de decisão visual e baseada em dados.

O que o Dashboard mostra:

Mapas Interativos (Folium): Visualize a distribuição das propriedades e ESECs. O mapa possui dois modos: "Áreas de Cobertura" (desenha polígonos englobando a área de atuação da ESEC) e "Linhas" (mostra a conexão direta de cada propriedade até sua ESEC).

Indicadores de Desempenho (KPIs): Resumo gerencial por Coordenadoria (CR), exibindo o total de propriedades, ESECs ativas e distâncias percorridas.

Distribuição Visual: Gráficos interativos (Plotly) mostrando o volume de propriedades atendidas e o peso de cada ESEC na distância total da coordenadoria.

Comparativo de Eficiência: Uma seção dedicada a comparar o Cenário Atual com o Otimizado, calculando automaticamente a economia percentual e a redução bruta na distância de deslocamento.

Configuração Inicial Obrigatória
Antes de rodar o dashboard pela primeira vez, você precisa informar ao script onde os seus arquivos de dados estão salvos.

Abra o arquivo principal Dashboard_Designação_ESEC-Propriedades.py e preencha as variáveis nas linhas 14 e 15 com os caminhos corretos do seu computador:

# Exemplo de como deve ficar no seu código:
PASTA_DADOS = r"C:\Caminho\Para\A\Pasta\Com\Os\CSVs" 
ARQUIVO_CENARIO_ATUAL = r"C:\Caminho\Para\O\Arquivo\Baseline_Cenario_Atual.csv" 
Importante: A PASTA_DADOS deve conter os arquivos com o prefixo Dashboard_, resultado_ e ESEC_ gerados previamente pelos algoritmos de cálculo.

Como Executar
Após configurar os caminhos dos dados no código, abra o seu terminal (Prompt de Comando, PowerShell ou terminal do VSCode), certifique-se de estar na mesma pasta do arquivo .py e rode o seguinte comando:

python -m streamlit run Dashboard_Designação_ESEC-Propriedades.py
O servidor local do Streamlit será iniciado e o dashboard abrirá automaticamente no seu navegador padrão.