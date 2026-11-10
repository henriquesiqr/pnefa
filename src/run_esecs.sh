#!/usr/bin/env bash

almenara=("Almenara" "Araçuaí" "Felisburgo" "Itaobim" "Jequitinhonha" "Medina" "Pedra Azul" "Rubim" "Salto da Divisa")
belo_horizonte=("Belo Horizonte" "Belo Vale" "Betim" "Conselheiro Lafaiete" "Itabira" "Itabirito" "Itaúna" "Lagoa Santa" "Pedro Leopoldo" "Santa Luzia" "Sete Lagoas")
bom_despacho=("Abaeté" "Bambuí" "Bom Despacho" "Iguatama" "Luz" "Pará de Minas" "Santo Antônio do Monte")
curvelo=("Corinto" "Curvelo" "Diamantina" "Paraopeba" "Pirapora" "Pompéu" "Várzea da Palma")
governador_valadares=("Aimorés" "Caratinga" "Conselheiro Pena" "Governador Valadares" "Inhapim" "Ipanema" "Ipatinga" "Mantena" "Resplendor" "Tarumirim")
guanhaes=("Água Boa" "Capelinha" "Conceição do Mato Dentro" "Guanhães" "Itamarandiba" "Peçanha" "Sabinópolis" "Santa Maria de Itabira" "São João Evangelista" "Serro" "Virginópolis")
janauba=("Espinosa" "Jaíba" "Janaúba" "Manga" "Montalvânia" "Porteirinha" "São João do Paraíso" "Taiobeiras")
juiz_de_fora=("Além Paraíba" "Alto Rio Doce" "Barbacena" "Bicas" "Carandaí" "Dona Euzébia" "Juiz de Fora" "Leopoldina" "Lima Duarte" "Matias Barbosa" "Rio Pomba" "Ubá" "Visconde do Rio Branco")
montes_claros=("Bocaiúva" "Brasília de Minas" "Coração de Jesus" "Francisco Sá" "Januária" "Montes Claros" "Salinas" "São Francisco" "São João da Ponte" "São Romão")
oliveira=("Campo Belo" "Divinópolis" "Entre Rios de Minas" "Formiga" "Itaguara" "Lavras" "Oliveira" "Perdões" "São João Del Rei")
passos=("Cássia" "Guaxupé" "Passos" "Piumhí" "São Roque de Minas" "São Sebastião do Paraíso")
patos_de_minas=("Carmo do Paranaíba" "Lagoa Formosa" "Patos de Minas" "Presidente Olegário" "São Gotardo" "Tiros" "Varjão de Minas" "Vazante")
patrocinio=("Abadia dos Dourados" "Coromandel" "Estrela do Sul" "Ibiá" "Monte Carmelo" "Patrocínio" "Perdizes" "Santa Juliana")
pocos_de_caldas=("Alfenas" "Alterosa" "Boa Esperança" "Machado" "Ouro Fino" "Poços de Caldas" "Muzambinho")
pouso_alegre=("Cambuí" "Extrema" "Itajubá" "Paraisópolis" "Pouso Alegre" "Santa Rita do Sapucaí" "São Gonçalo do Sapucaí")
teofilo_otoni=("Águas Formosas" "Ataléia" "Carlos Chagas" "Frei Inocêncio" "Itambacuri" "Malacacheta" "Nanuque" "Teófilo Otoni")
uberaba=("Araxá" "Campo Florido" "Carneirinho" "Conceição das Alagoas" "Frutal" "Itapagipe" "Iturama" "Limeira do Oeste" "Nova Ponte" "Sacramento" "Uberaba" "União de Minas")
uberlandia=("Araguari" "Campina Verde" "Capinópolis" "Ituiutaba" "Monte Alegre de Minas" "Prata" "Santa Vitória" "Tupaciguara" "Uberlândia")
unai=("Arinos" "Bonfinópolis de Minas" "Brasilândia de Minas" "Buritis" "João Pinheiro" "Paracatu" "Unaí" "Urucuia")
varginha=("Baependi" "Campanha" "Itamonte" "Lambari" "Liberdade" "São Vicente de Minas" "Três Corações" "Três Pontas" "Varginha")
vicosa=("Carangola" "Manhuaçu" "Manhumirim" "Muriaé" "Ponte Nova" "Rio Casca" "Rio Piracicaba" "São Domingos do Prata" "Viçosa")

coordenadorias=(
  almenara
  belo_horizonte
  bom_despacho
  curvelo
  governador_valadares
  guanhaes
  janauba
  juiz_de_fora
  montes_claros
  oliveira
  passos
  patos_de_minas
  patrocinio
  pocos_de_caldas
  pouso_alegre
  teofilo_otoni
  uberaba
  uberlandia
  unai
  varginha
  vicosa
)

declare -A esecs
esecs["Almenara"]="3101706"
esecs["Araçuaí"]="3103405"
esecs["Felisburgo"]="3125606"
esecs["Itaobim"]="3133303"
esecs["Jequitinhonha"]="3135803"
esecs["Medina"]="3117009"
esecs["Pedra Azul"]="3101003"
esecs["Rubim"]="3156601"
esecs["Salto da Divisa"]="3134707"
esecs["Belo Horizonte"]="3106200"
esecs["Belo Vale"]="3106408"
esecs["Betim"]="3106705"
esecs["Conselheiro Lafaiete"]="3114907"
esecs["Itabira"]="3105400"
esecs["Itabirito"]="3131901"
esecs["Itaúna"]="3133709"
esecs["Lagoa Santa"]="3105004"
esecs["Pedro Leopoldo"]="3112505"
esecs["Santa Luzia"]="3110004"
esecs["Sete Lagoas"]="3109600"
esecs["Abaeté"]="3100203"
esecs["Bambuí"]="3105103"
esecs["Bom Despacho"]="3103900"
esecs["Iguatama"]="3104205"
esecs["Luz"]="3123205"
esecs["Pará de Minas"]="3126000"
esecs["Santo Antônio do Monte"]="3137205"
esecs["Corinto"]="3104809"
esecs["Curvelo"]="3120904"
esecs["Diamantina"]="3120102"
esecs["Paraopeba"]="3103207"
esecs["Pirapora"]="3109402"
esecs["Pompéu"]="3140506"
esecs["Várzea da Palma"]="3138104"
esecs["Aimorés"]="3101102"
esecs["Caratinga"]="3107802"
esecs["Conselheiro Pena"]="3102209"
esecs["Governador Valadares"]="3101805"
esecs["Inhapim"]="3109253"
esecs["Ipanema"]="3117405"
esecs["Ipatinga"]="3103009"
esecs["Mantena"]="3115706"
esecs["Resplendor"]="3134103"
esecs["Tarumirim"]="3112653"
esecs["Água Boa"]="3100609"
esecs["Capelinha"]="3102852"
esecs["Conceição do Mato Dentro"]="3117504"
esecs["Guanhães"]="3113800"
esecs["Itamarandiba"]="3113503"
esecs["Peçanha"]="3112059"
esecs["Sabinópolis"]="3140605"
esecs["Santa Maria de Itabira"]="3125903"
esecs["São João Evangelista"]="3116803"
esecs["Serro"]="3102407"
esecs["Virginópolis"]="3100500"
esecs["Espinosa"]="3124302"
esecs["Jaíba"]="3135050"
esecs["Janaúba"]="3135100"
esecs["Manga"]="3132107"
esecs["Montalvânia"]="3136959"
esecs["Porteirinha"]="3115474"
esecs["São João do Paraíso"]="3143450"
esecs["Taiobeiras"]="3106655"
esecs["Além Paraíba"]="3101508"
esecs["Alto Rio Doce"]="3102100"
esecs["Barbacena"]="3102902"
esecs["Bicas"]="3106903"
esecs["Carandaí"]="3101631"
esecs["Dona Euzébia"]="3104601"
esecs["Juiz de Fora"]="3115904"
esecs["Leopoldina"]="3104403"
esecs["Lima Duarte"]="3103603"
esecs["Matias Barbosa"]="3106101"
esecs["Rio Pomba"]="3103306"
esecs["Ubá"]="3121902"
esecs["Visconde do Rio Branco"]="3124005"
esecs["Bocaiúva"]="3107307"
esecs["Brasília de Minas"]="3108602"
esecs["Coração de Jesus"]="3116506"
esecs["Francisco Sá"]="3108503"
esecs["Januária"]="3108255"
esecs["Montes Claros"]="3127354"
esecs["Salinas"]="3127073"
esecs["São Francisco"]="3130051"
esecs["São João da Ponte"]="3129657"
esecs["São Romão"]="3111150"
esecs["Campo Belo"]="3100807"
esecs["Divinópolis"]="3114204"
esecs["Entre Rios de Minas"]="3121407"
esecs["Formiga"]="3110400"
esecs["Itaguara"]="3108107"
esecs["Lavras"]="3114600"
esecs["Oliveira"]="3114006"
esecs["Perdões"]="3108008"
esecs["São João Del Rei"]="3115201"
esecs["Cássia"]="3112406"
esecs["Guaxupé"]="3128303"
esecs["Passos"]="3101904"
esecs["Piumhí"]="3112802"
esecs["São Roque de Minas"]="3164308"
esecs["São Sebastião do Paraíso"]="3104106"
esecs["Carmo do Paranaíba"]="3114303"
esecs["Lagoa Formosa"]="3137502"
esecs["Patos de Minas"]="3148004"
esecs["Presidente Olegário"]="3137536"
esecs["São Gotardo"]="3111507"
esecs["Tiros"]="3103801"
esecs["Varjão de Minas"]="3161700"
esecs["Vazante"]="3128600"
esecs["Abadia dos Dourados"]="3100104"
esecs["Coromandel"]="3119302"
esecs["Estrela do Sul"]="3115003"
esecs["Ibiá"]="3129509"
esecs["Monte Carmelo"]="3131604"
esecs["Patrocínio"]="3120706"
esecs["Perdizes"]="3149804"
esecs["Santa Juliana"]="3149200"
esecs["Alfenas"]="3101607"
esecs["Alterosa"]="3102001"
esecs["Boa Esperança"]="3107109"
esecs["Machado"]="3114709"
esecs["Ouro Fino"]="3101409"
esecs["Poços de Caldas"]="3102605"
esecs["Muzambinho"]="3105301"
esecs["Cambuí"]="3107901"
esecs["Extrema"]="3110509"
esecs["Itajubá"]="3120508"
esecs["Paraisópolis"]="3108909"
esecs["Pouso Alegre"]="3108305"
esecs["Santa Rita do Sapucaí"]="3117207"
esecs["São Gonçalo do Sapucaí"]="3113602"
esecs["Águas Formosas"]="3100906"
esecs["Ataléia"]="3104700"
esecs["Carlos Chagas"]="3113701"
esecs["Frei Inocêncio"]="3126901"
esecs["Itambacuri"]="3110806"
esecs["Malacacheta"]="3126752"
esecs["Nanuque"]="3144300"
esecs["Teófilo Otoni"]="3113008"
esecs["Araxá"]="3104007"
esecs["Campo Florido"]="3111408"
esecs["Carneirinho"]="3114550"
esecs["Conceição das Alagoas"]="3100708"
esecs["Frutal"]="3116902"
esecs["Itapagipe"]="3133402"
esecs["Iturama"]="3134400"
esecs["Limeira do Oeste"]="3138625"
esecs["Nova Ponte"]="3145000"
esecs["Sacramento"]="3118205"
esecs["Uberaba"]="3121258"
esecs["União de Minas"]="3170438"
esecs["Araguari"]="3103504"
esecs["Campina Verde"]="3111101"
esecs["Capinópolis"]="3109808"
esecs["Ituiutaba"]="3134202"
esecs["Monte Alegre de Minas"]="3142809"
esecs["Prata"]="3152808"
esecs["Santa Vitória"]="3129103"
esecs["Tupaciguara"]="3103751"
esecs["Uberlândia"]="3130705"
esecs["Arinos"]="3104502"
esecs["Bonfinópolis de Minas"]="3108206"
esecs["Brasilândia de Minas"]="3108552"
esecs["Buritis"]="3109303"
esecs["João Pinheiro"]="3136306"
esecs["Paracatu"]="3147006"
esecs["Unaí"]="3109451"
esecs["Urucuia"]="3154457"
esecs["Baependi"]="3101201"
esecs["Campanha"]="3110707"
esecs["Itamonte"]="3101300"
esecs["Lambari"]="3114105"
esecs["Liberdade"]="3107208"
esecs["São Vicente de Minas"]="3102803"
esecs["Três Corações"]="3160801"
esecs["Três Pontas"]="3111606"
esecs["Varginha"]="3113909"
esecs["Carangola"]="3110103"
esecs["Manhuaçu"]="3112901"
esecs["Manhumirim"]="3102050"
esecs["Muriaé"]="3103108"
esecs["Ponte Nova"]="3102506"
esecs["Rio Casca"]="3100302"
esecs["Rio Piracicaba"]="3100401"
esecs["São Domingos do Prata"]="3106002"
esecs["Viçosa"]="3103702"

for coord in "${coordenadorias[@]}"; do
  declare -n lista="$coord"   # nameref: referência ao array real

  echo "Coordenadoria: $coord"
  for municipio in "${lista[@]}"; do
    echo "  - $municipio"
    # chamar o programa python3 run_pipeline.py $coord $municipio
    python3 run_pipeline.py "$coord" "$municipio"
  done
done

