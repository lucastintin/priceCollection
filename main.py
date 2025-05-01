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
todasMecanicas = []
todasCategorias = []
todosDesigners = []
jogos = []
#breveArtistas

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

    return contagem_mec.most_common(), contagem_cat.most_common(), contagem_aut.most_common()

def fetch_game_mechanics_and_categories(paramGameId):
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={paramGameId}&type=boardgame&stats=1"
    response = requests.get(url)
    mec, cat, aut = [], [], []
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
        
        return mec, cat, aut
    else:
        return [], [], []

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

##DEPRECATED
def fetch_lastPrice_USD(paramGameId):
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
                date = item["saledate"]
                prices.append({"price": price, "date": date})
    return prices[0]['price']

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
            #Tentar colocar Mecanicas e Categorias atreladas ao jogo
            mecanicas, categorias, designers = fetch_game_mechanics_and_categories(game_id)           

            jogos.append({"id": game_id, "name": name, "year": year, "prices": prices, "last_sell": last_sell, "minPrice": minPrice, "maxPrice": maxPrice, "image": image, "numplays":numplays, "stats": stats, "mecanicas": mecanicas, "categorias": categorias, "designers": designers})
    return jogos

#====== Streamlit App ======#
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
if "catalogoCreated" not in st.session_state:
    st.session_state["catalogoCreated"] = False

def changeCatalogoState():
    st.session_state["catalogoCreated"] = True

st.set_page_config(page_title="Vale Ouro (versão 0.0.3)", layout="wide")
st.markdown(style_page, unsafe_allow_html=True)
st.title("Quanto vale minha coleção de Boardgames?")

username = st.text_input("Digite seu nome de usuário do BoardGameGeek")

if st.button("Buscar coleção") and username:
    tab1, tab2, tab3, tab4 = st.tabs(["Valores", "Análise", "Detalhamento", "Sugestões"])
    with st.spinner("Consultando coleção no BGG...Se você achar que está demorando, venda alguns jogos!"):
        collection = fetch_collection(username)
        data  = []
        priceTotal = 0
        maxPriceTotal = 0
        minPriceTotal = 0
        porJogas = sorted(collection, key=lambda jogo: int(jogo['numplays']))

    with tab1:
       st.info(f"{len(collection)} jogos encontrados!")
       with st.spinner("Calculando valores no mercado..."):
        if collection:
                #st.write(collection)
                for index, game in enumerate(collection):
                    maxPriceTotal += float(game['maxPrice'])
                    minPriceTotal += float(game['minPrice'])

                    #Total da Ultima venda
                    priceTotal += float(game['last_sell'])
       
                    data.append({"name": game["name"], "last_sell": game['last_sell'], 'min_price': game['minPrice'], 'max_price': game['maxPrice']})
                    #jogos.append({"id": game["id"], "name": game["name"], "year": game["year"], "last_sell": game['price'], "image": game['image'], "numplays":game['numplays'], "stats": game['stats'], 'min_price': minPrice, 'max_price': maxPrice, 'prices': precos})
                st.success(f"Coleção estimada entre (em USD$): {minPriceTotal:.2f} ~ {maxPriceTotal:.2f}")       
                
                df = pd.DataFrame(data)
                df.round(decimals=2)
                df['last_sell'] = df['last_sell'].astype(float)
                with st.expander("Ver Detalhes de valores da coleção"):
                    st.write("A coleção foi estimada com base no preço da última venda realizada no BGG Market, independente da condição do jogo.")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                st.toast("No detalhamento da coleção, há opção de Exportar para CSV. Pode ser importado no Excel, para você usar mais funções.", icon="🔔")
        else:
            st.warning("Nenhum jogo encontrado ou usuário inválido.")

    with tab2:
        with st.spinner("Analisando a coleção..."):            
            kol1, kol2, kol3 = st.columns(3)
            with kol1:
                st.subheader("⬆️ Mais jogado:")
                #st.image(porJogas[-1]['image'], width=200)
                for index, jogo in enumerate(reversed(porJogas[-10:])):
                    st.write(f"{jogo['name']}: {jogo['numplays']} partidas")
                #st.write(f"{porJogas[-1]['name']} jogado {porJogas[-1]['numplays']} vezes")

            with kol3: 
                st.subheader("⬇️ Menos jogado:")
                #st.image(porJogas[0]['image'], width=200)
                for index, jogo in enumerate(porJogas[:10]):    
                    st.write(f"{jogo['name']}: {jogo['numplays']} partidas")
                #st.write(f"{porJogas[0]['name']} jogado {porJogas[0]['numplays']} vezes")
            st.divider()

            col1, col2, col3 = st.columns(3)
            mec_top, cat_top, aut_top = contarMecanicasCategorias()
            with col1:  
                st.subheader("🧩 Mecânicas mais frequentes")
                for mec, count in mec_top[:10]:
                    st.write(f"{mec}: {count} jogos")
                st.altair_chart(plot_frequencia("🧩 Mecânicas mais presentes", mec_top))
            with col2:
                st.subheader("🏷️ Categorias mais frequentes")
                for cat, count in cat_top[:10]:
                    st.write(f"{cat}: {count} jogos")
                st.altair_chart(plot_frequencia("🏷️ Categorias mais presentes", cat_top))
            with col3:
                st.subheader("🧙 Designers mais frequentes")
                for aut, count in aut_top[:10]:
                    st.write(f"{aut}: {count} jogos")
                st.altair_chart(plot_frequencia("🧙 Designers mais presentes", aut_top))
    
    with tab3:
        st.subheader("Detalhamento dos jogos da coleção.")
        for index, jogo in enumerate(jogos):
            #st.write(jogo)
            card = st.container()
            kcol1, kcol2, kcol3 = card.columns(3)
            card.markdown(f"<div class=card", unsafe_allow_html=True)
            card.image(jogo['image'], width=200)
            card.markdown(f"<div class=container", unsafe_allow_html=True)
            card.write(f"**{jogo['name']}**")
            card.write(f"Ano: {jogo['year']}")
            card.write(f"Jogadores: {jogo['stats']['minplayers']} - {jogo['stats']['maxplayers']}")
            card.write(f"Duração Média: {jogo['stats']['playingtime']} min.")
            card.write(f"Duração: {jogo['stats']['minplaytime']} - {jogo['stats']['maxplaytime']} min.")
            card.write(f"Partidas: {jogo['numplays']}")
            with kcol1:
                card.write(f"Preço última venda")
                card.write(f"${jogo['last_sell']:.2f}")
            with kcol2:
                card.write(f"Preço mínimo histórico")
                card.write(f"${jogo['minPrice']:.2f}")
            with kcol3:
                card.write(f"Preço máximo histórico")
                card.write(f"${jogo['maxPrice']:.2f}")
            card.line_chart(jogo['prices'], x='date', y='price', use_container_width=True)
            card.markdown("</div>", unsafe_allow_html=True)
            card.markdown("</div>", unsafe_allow_html=True)
                
                

    #Sugestão - Aqui que é o PUNK              
    # with st.spinner("Pensando em sugestões..."):
    with tab4:
        st.subheader("Sugestões de jogos semelhantes.")  
        st.write("Em breve!")