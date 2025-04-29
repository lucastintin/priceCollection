import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import time
import json as JSON
from collections import Counter
import altair as alt

collection = []
todasMecanicas = []
todasCategorias = []
todosDesigners = []
#breveArtistas

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

def contarMecanicasCategorias(jogos_ids):
    
    for game_id in jogos_ids:
        info = fetch_game_mechanics_and_categories(game_id["id"])
        #print(info)
        #todas_mecanicas.extend(info["mechanics"])
        #todas_categorias.extend(info["categories"])
        time.sleep(1)  # evitar overload na API

    contagem_mec = Counter(todasMecanicas)
    contagem_cat = Counter(todasCategorias)
    contagem_aut = Counter(todosDesigners)

    return contagem_mec.most_common(), contagem_cat.most_common(), contagem_aut.most_common()

def fetch_game_mechanics_and_categories(paramGameId):
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={paramGameId}&type=boardgame&stats=1"
    response = requests.get(url)
    
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        for link in root.findall(".//link"):
            if link.attrib["type"] == "boardgamecategory":
               todasCategorias.append(link.attrib["value"]) 
            if link.attrib["type"] =='boardgamemechanic':
                todasMecanicas.append(link.attrib["value"])
            if link.attrib["type"] =='boardgamedesigner':
                todosDesigners.append(link.attrib["value"])
        
        return todasMecanicas, todasCategorias, todosDesigners
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
                date = item["saledate"]
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
    url = f"https://boardgamegeek.com/xmlapi2/collection?username={username}&own=1"
    response = requests.get(url)

    # Espera até a API processar (BGG tem delay)
    while response.status_code == 202:
        time.sleep(30)
        response = requests.get(url)

    games = []
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        for item in root.findall("item"):
            game_id = item.attrib["objectid"]
            name = item.find("name").text
            year_elem = item.find("yearpublished")
            year = year_elem.text if year_elem is not None else "?"
            price = fetch_price_USD(game_id)[0]['price']
            games.append({"id": game_id, "name": name, "year": year, "price": price})
    return games

#====== Streamlit App ======#
hide_github_icon = """
<style>
    .stApp [data-testid="stToolbar"] {
        display: none;
    }
</style>
"""

#st.markdown(hide_github_icon, unsafe_allow_html=True)
st.set_page_config(page_title="Vale Ouro", layout="wide")

st.title("Quanto vale minha coleção de Boardgames?")

username = st.text_input("Digite seu nome de usuário do BoardGameGeek")

if st.button("Buscar coleção") and username:
    with st.spinner("Consultando coleção no BGG...Se você achar que está demorando, venda alguns jogos!"):
        collection = fetch_collection(username)
        priceTotal = 0
        maxPriceTotal = 0
        minPriceTotal = 0
        data  = []
        if collection:
            st.warning(f"{len(collection)} jogos encontrados!")
            #st.write(collection)
            for index, game in enumerate(collection):

                precos = fetch_price_USD(game["id"])
                
                maxPrice = max(precos, key=lambda x: x['price'])['price']
                minPrice = min(precos, key=lambda x: x['price'])['price']

                maxPriceTotal += float(maxPrice)
                minPriceTotal += float(minPrice)

                priceTotal += float(game['price'])
                #Montando o dataFrame
                data.append({"name": game["name"], "last_sell": game['price'], 'min_price': minPrice, 'max_price': maxPrice})
            st.success(f"Coleção estimada entre (em USD$): {minPriceTotal:.2f} ~ {maxPriceTotal:.2f}")       
            
            df = pd.DataFrame(data)
            df.round(decimals=2)
            df['last_sell'] = df['last_sell'].astype(float)
            with st.expander("Ver Detalhes da coleção"):
                st.write("A coleção foi estimada com base no preço da última venda realizada no BGG Market, independente da condição do jogo.")
                st.dataframe(df, use_container_width=True, hide_index=True)
            st.toast("No detalhamento da coleção, há opção de Exportar para CSV. Pode ser importado no Excel, para você usar mais funções.", icon="🔔")
        else:
            st.warning("Nenhum jogo encontrado ou usuário inválido.")

    with st.spinner("Analisando a coleção..."):
        col1, col2, col3 = st.columns(3)
        #Futuramente Apresentar um gráfico com as mecanicas
        mec_top, cat_top, aut_top = contarMecanicasCategorias(collection)
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
            st.subheader("🏷️ Autores mais frequentes")
            for aut, count in aut_top[:10]:
                st.write(f"{aut}: {count} jogos")
            st.altair_chart(plot_frequencia("🏷️ Designers mais presentes", aut_top))

    #Sugestão - Aqui que é o PUNK              
    # with st.spinner("Pensando em sugestões..."):
    st.subheader("Sugestões de jogos semelhantes.")  
    st.write("Em breve!")
        