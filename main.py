import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import time
import json as JSON

def fetch_game_mechanics(paramGameId):
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={paramGameId}&type=boardgame&stats=0"
    response = requests.get(url)
    
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        mechanics = []
        for link in root.findall(".//link[@type='mechanic']"):
            mechanics.append(link.attrib["value"])
        return mechanics
    else:
        return []

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
            price = fetch_lastPrice_USD(game_id)
            games.append({"id": game_id, "name": name, "year": year, "price": price})
    return games

#====== Streamlit App ======#
st.set_page_config(page_title="Vale Ouro", layout="wide")

st.title("Quanto vale minha coleção de Boardgames?")

username = st.text_input("Digite seu nome de usuário do BoardGameGeek")

if st.button("Buscar coleção") and username:
    with st.spinner("Consultando a coleção..."):
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