import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import time
import json as JSON
from collections import Counter
import altair as alt
from datetime import datetime

#variáveis globais
collection = []
jogos = []
todasMecanicas = []
todasCategorias = []
todosDesigners = []
todosArtistas = []
totalColecao = 0
totalPlays = 0
totalPeso = 0

def extrair_ano(data_str):
    data = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
    return data.year

def plot_frequencia(titulo, contagem):
    df = pd.DataFrame(contagem[:10], columns=["Nome", "Frequência"])  # Top 10
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Frequência:Q"),
        y=alt.Y("Nome:N", sort='-x'),
        tooltip=["Nome", "Frequência"]
    ).properties(
        width=600,
        height=400,
        title=titulo
    )
    return chart

def contarMecanicasCategorias():
    contagem_mec = Counter(todasMecanicas)
    contagem_cat = Counter(todasCategorias)
    contagem_aut = Counter(todosDesigners)
    contagem_art = Counter(todosArtistas)

    return contagem_mec.most_common(), contagem_cat.most_common(), contagem_aut.most_common(), contagem_art.most_common()

def fetch_game_details(paramGameId):
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={paramGameId}&stats=1"
    response = requests.get(url)
    mec, cat, aut, art, peso, compradores = [], [], [], [], [], []
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        for link in root.findall(".//link"):
            if link.attrib["type"] == "boardgamecategory":
               mec.append(link.attrib["value"])
               todasCategorias.append(link.attrib["value"]) 
            if link.attrib["type"] =='boardgamemechanic':
                cat.append(link.attrib["value"])
                todasMecanicas.append(link.attrib["value"])
            if link.attrib["type"] =='boardgamedesigner':
                aut.append(link.attrib["value"])
                todosDesigners.append(link.attrib["value"])
            if link.attrib["type"] =='boardgameartist':
                art.append(link.attrib["value"])
                todosArtistas.append(link.attrib["value"])
        if root.find(".//averageweight") is not None:
            peso.append(float(root.find(".//averageweight").attrib.get("value")))
        if root.find(".//wishing") is not None:
            compradores.append(float(root.find(".//wishing").attrib.get("value")))
        return mec, cat, aut, art, peso, compradores
    else:
        return [], [], [], [], [0], [0]	

def fetch_price_USD(paramGameId):
    uri = f"https://boardgamegeek.com/api/market/products/pricehistory?ajax=1&condition=any&currency=USD&objectid={paramGameId}&objecttype=thing&pageid=1"
    response = requests.get(uri)

    # Espera até a API processar (BGG tem delay)
    while response.status_code == 202:
        time.sleep(2)
        response = requests.get(uri)

    prices = []
    if response.status_code == 200:
        root = JSON.loads(response.content)
        if len(root["items"]) == 0:
            prices.append({"price": 0, "date": "N/A"})
        else:
            for item in root["items"]:
                price = item["price"]
                date = extrair_ano(item["saledate"])
                prices.append({"price": float(price), "date": date})
    return prices

def fetch_collection(username):
    url = f"https://boardgamegeek.com/xmlapi2/collection?username={username}&own=1&stats=1 "
    response = requests.get(url)

    # Espera até a API processar (BGG tem delay)
    while response.status_code == 202:
        time.sleep(30)
        response = requests.get(url)

    minPrice = 0
    maxPrice = 0
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        for item in root.findall("item"):
            game_id = item.attrib["objectid"]
            name = item.find("name").text
            year_elem = item.find("yearpublished")
            year = year_elem.text if year_elem is not None else "?"

            prices = fetch_price_USD(game_id)
            last_sell = prices[0]['price']
            maxPrice = max(prices, key=lambda x: x['price'])['price']
            minPrice = min(prices, key=lambda x: x['price'])['price']

            numplays = item.find("numplays").text            
            image = item.find("image").text if item.find("image") is not None else None

            if("playtime" not in item.find("stats").attrib):
                playtime = "Não informado"
            else:
                playtime = item.find("stats").attrib["playtime"]
            
            if("minplaytime" not in item.find("stats").attrib):
                minplaytime = "Não informado"
            else:
                minplaytime = item.find("stats").attrib["minplaytime"]
            
            if("maxplaytime" not in item.find("stats").attrib):
                maxplaytime = "Não informado"
            else:
                maxplaytime = item.find("stats").attrib["maxplaytime"]
            
            stats = {
                "vendidos": item.find("stats").attrib["numowned"] if item.find("stats").attrib["numowned"] is not None else 0,
                "minplayers": item.find("stats").attrib["minplayers"] if item.find("stats").attrib["minplayers"] is not None else 0,
                "maxplayers": item.find("stats").attrib["maxplayers"] if item.find("stats").attrib["maxplayers"] is not None else 0,
                "playingtime": playtime,
                "minplaytime": minplaytime,
                "maxplaytime": maxplaytime,
            }
            mecanicas, categorias, designers, artistas, peso, compradores = fetch_game_details(game_id)           

            jogos.append({"id": game_id, "name": name, "year": year, "prices": prices, "last_sell": last_sell, "minPrice": minPrice, "maxPrice": maxPrice, "image": image, "numplays":numplays, "stats": stats, "mecanicas": mecanicas, "categorias": categorias, "designers": designers, "artistas": artistas, "peso": peso, "compradores": compradores})
    return jogos

#====== Streamlit App ======#
versao = "0.0.7"
##INICIO LIXO
#TODO: LIMPAR
hide_github_icon = """
<style>
    .stApp [data-testid="stToolbar"] {
        display: none;
    }
</style>
"""
#st.markdown(hide_github_icon, unsafe_allow_html=True)

style_page = """
<style>
    .card {
        /* Add shadows to create the "card" effect */
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        transition: 0.3s;
        border-radius: 5px;
    }   

    /* On mouse-over, add a deeper shadow */
    .card:hover {
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
    }

    /* Add some padding inside the card container */
    .container {
        padding: 2px 16px;
    }
    img {
      border-radius: 5px 5px 0 0;
      opacity: 0.15;
    }
    img:hover {
      border-radius: 5px 5px 0 0;
      opacity: 1;
    }
    </style>
    """
####FIM LIXO
if "catalogoCreated" not in st.session_state:
    st.session_state["catalogoCreated"] = False

def changeCatalogoState():
    st.session_state["catalogoCreated"] = True

st.set_page_config(page_title=f"Vale Ouro v{versao}", layout="wide")
st.markdown(style_page, unsafe_allow_html=True)
st.title("Quanto vale minha coleção de Boardgames?")

username = st.text_input("Digite seu nome de usuário do BoardGameGeek")

if st.button("Buscar coleção") and username:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Valores", "Catálogo", "Tops", "Detalhamento", "Sugestões"])
    with st.spinner("Consultando coleção no BGG...Se você achar que está demorando, venda alguns jogos!"):
        collection = fetch_collection(username)
        totalColecao = len(collection)
        data  = []
        priceTotal = 0
        maxPriceTotal = 0
        minPriceTotal = 0
        porJogas = sorted(collection, key=lambda jogo: int(jogo['numplays']))

    with tab1:
       st.info(f"{totalColecao} jogos encontrados!")
       with st.spinner("Calculando valores no mercado..."):
        if collection:
                #st.write(collection)
                for index, game in enumerate(collection):
                    maxPriceTotal += float(game['maxPrice'])
                    minPriceTotal += float(game['minPrice'])
                    #Total da Ultima venda
                    priceTotal += float(game['last_sell'])

                    #Total de partidas jogadas
                    totalPlays += int(game['numplays'])

                    #Peso total da coleção
                    totalPeso += float(game['peso'][0]) if game['peso'] else 0
       
                    data.append({"name": game["name"], "last_sell": game['last_sell'], 'min_price': game['minPrice'], 'max_price': game['maxPrice']})
                    #jogos.append({"id": game["id"], "name": game["name"], "year": game["year"], "last_sell": game['price'], "image": game['image'], "numplays":game['numplays'], "stats": game['stats'], 'min_price': minPrice, 'max_price': maxPrice, 'prices': precos})
                st.success(f"Coleção estimada entre (em USD$): {minPriceTotal:.2f} ~ {maxPriceTotal:.2f}")       
                st.success(f"Total considerando últimas vendas no BGG (em USD$): {priceTotal:.2f} ")       

                df = pd.DataFrame(data)
                df.round(decimals=2)
                df['last_sell'] = df['last_sell'].astype(float)
                with st.expander("Ver listagem de valores da coleção"):
                    st.write("A coleção foi estimada com base no preço da última venda realizada no BGG Market, independente da condição do jogo.")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                #st.toast("No detalhamento da coleção, há opção de Exportar para CSV. Pode ser importado no Excel, para você usar mais funções.", icon="🔔")
        else:
            st.warning("Nenhum jogo encontrado ou usuário inválido.")

    with tab2:
        #st.subheader("Catálogo de jogos da coleção.")
        #TODO: Deixar bonito
        #fragment botão dowload do Catalodo

        for index, jogo in enumerate(jogos):
            card = st.container()
            card.markdown(f"<div class=card", unsafe_allow_html=True)
            card.image(jogo['image'], width=200)
            card.markdown(f"<div class=container", unsafe_allow_html=True)
            card.write(f"**{jogo['name']}**")
            card.write(f"Ano: {jogo['year']}")
            card.write(f"Jogadores: {jogo['stats']['minplayers']} - {jogo['stats']['maxplayers']}")
            #TODO:REVISAR
            card.write(f"Duração Média: {jogo['stats']['playingtime']} min.")
            if jogo['stats']['minplaytime'] == jogo['stats']['maxplaytime']:
                card.write(f"Duração: {jogo['stats']['maxplaytime']} min.")
            else:
                card.write(f"Duração: {jogo['stats']['minplaytime']} - {jogo['stats']['maxplaytime']} min.")
            card.write(f"Partidas: {jogo['numplays']}.")
            card.markdown("</div>", unsafe_allow_html=True)
            card.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        with st.spinner("Analisando a coleção..."):            
            col1, col2 = st.columns(2)
            mec_top, cat_top, aut_top, art_top = contarMecanicasCategorias()
            with col1:
                st.subheader("⬆️ Mais jogados:")
                #st.image(porJogas[-1]['image'], width=200)
                for index, jogo in enumerate(reversed(porJogas[-10:])):
                    st.write(f"{jogo['name']}: {jogo['numplays']} partidas")
                #st.write(f"{porJogas[-1]['name']} jogado {porJogas[-1]['numplays']} vezes")
                st.divider()
                st.subheader("🧩 Mecânicas mais frequentes")
                for mec, count in mec_top[:10]:
                    st.write(f"{mec}: {count} jogos")
                st.altair_chart(plot_frequencia("🧩 Mecânicas mais presentes", mec_top))
                st.divider()
                st.subheader("🧙 Designers mais frequentes")
                for aut, count in aut_top[:10]:
                    st.write(f"{aut}: {count} jogos")
                st.altair_chart(plot_frequencia("🧙 Designers mais presentes", aut_top))

            with col2: 
                st.subheader("⬇️ Menos jogados:")
                #st.image(porJogas[0]['image'], width=200)
                for index, jogo in enumerate(porJogas[:10]):    
                    st.write(f"{jogo['name']}: {jogo['numplays']} partidas")
                #st.write(f"{porJogas[0]['name']} jogado {porJogas[0]['numplays']} vezes")
                #dfMaisJogados = pd.DataFrame(porJogas[:10])
                #st.table(dfMaisJogados)
                st.divider()
                st.subheader("🏷️ Categorias mais frequentes")
                for cat, count in cat_top[:10]:
                    st.write(f"{cat}: {count} jogos")
                st.altair_chart(plot_frequencia("🏷️ Categorias mais presentes", cat_top))
                st.divider()
                st.subheader("🎨 Artistas mais frequentes")
                for art, count in art_top[:10]:
                    st.write(f"{art}: {count} jogos")
                st.altair_chart(plot_frequencia("🎨 Artistas mais presentes", art_top))
    
    with tab4:
        #st.subheader("Detalhamento dos jogos da coleção.")
        #TODO: Arrumar esse Frankstein
        for index, jogo in enumerate(jogos):
            #st.write(jogo)
            with st.container():
                ###Calculos
                #Partidas
                if jogo['numplays'] == 0:
                    porcPartidas = 0
                else:
                    porcPartidas = float(jogo['numplays'])/float(totalPlays)

                #Peso
                medianPeso = float(totalPeso)/float(totalColecao)
                diffPeso = float(jogo['peso'][0]) - medianPeso	
                if diffPeso < 0:
                    pesoStr = "Esse jogo é mais leve que a média da coleção."
                elif diffPeso > 0:
                    pesoStr = "Esse jogo é mais pesado que a média da coleção."
                else:
                    pesoStr = "Esse jogo está na média da coleção."

                #Apresentação                
                st.header(f"**{jogo['name']}**")
                st.write(f"Partidas: {jogo['numplays']} de {totalPlays} partidas jogadas. {porcPartidas:.2%} das partidas.")
                st.write(f"Peso: {jogo['peso'][0]:.2F}/5. Média: {medianPeso:.2F}. {pesoStr}")
                ####
                #Pensar melhor analisar os limites de cada faixa
                #st.write(porcPartidas)
                #match porcPartidas:
                #    case porc if porc == 0.0 and porc <= 0.2:
                #        st.progress(0.0, text="Pouquíssimas partidas jogadas.")
                #        st.write("Você pode vender.")
                #    case porc if porc > 0.2 and porc <= 0.5:
                #        st.progress(0.3, text="Poucas partidas jogadas.")
                #        st.write("Você pode começar a jogar!")
                #    case porc if porc > 0.5 and porc <= 0.8:
                #        st.progress(0.4, text="Muitas as partidas jogadas.")
                #        st.write("Você gosta muito! Pode considerar comprar expansões ou jogos parecidos!")
                #    case 1.0:
                #        st.progress(1.0, text="Todas as partidas jogadas.")
                #        st.write("Você é um expert nesse jogo! Vire expert em outros jogos também! Ou venda-os")
                ####
                st.dataframe(
                    pd.DataFrame({
                        "Preço última venda": [jogo['last_sell']],
                        "Preço mínimo histórico": [jogo['minPrice']],
                        "Preço máximo histórico": [jogo['maxPrice']],
                    }), hide_index=True
                )	
                
                with st.expander(f"Historico de preço do {jogo['name']} ", expanded=False):
                    st.line_chart(jogo['prices'], x='date', y='price', use_container_width=True)
                
    #Sugestão - Aqui que é o PUNK              
    # with st.spinner("Pensando em sugestões..."):
    with tab5:
        #st.subheader("Sugestões de jogos semelhantes.")  
        st.write("Em breve! Um abraço a todos os membros do LUDUS Magisterium.")
        #TODO: Calular a media de peso da coleção
        #Soma Peso / len(jogos) 
        for x in range(0, 3):
            st.write(jogos[x])