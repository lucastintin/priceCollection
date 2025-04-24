import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import time
import json as JSON
import io

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
        data  = []
        if collection:
            st.warning(f"{len(collection)} jogos encontrados!")
            #st.write(collection)
            for index, game in enumerate(collection):
                #price = fetch_price_USD(game["id"])
                priceTotal += float(game['price'])
                data.append({"name": game["name"], "price": game['price']})
            st.success(f"Coleção estimada em USD$ {priceTotal:.2f}")       
            
            df = pd.DataFrame(data)
            newdata = df.astype(str)
            with st.expander("Ver Detalhes da coleção"):
                st.write("A coleção foi estimada com base no preço da última venda realizada no BGG Market, independente da condição do jogo.")
                st.dataframe(newdata, use_container_width=True, hide_index=True)

            # Exportar para Excel
            if st.button("Exportar coleção para Excel"):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as XLwriter:
                    df.to_excel(XLwriter, index=False, sheet_name="Coleção")
                    XLwriter.save()
                st.download_button(
                    label="📥 Baixar coleção como Excel",
                    data=output.getvalue(),
                    file_name="colecao_bgg.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("Nenhum jogo encontrado ou usuário inválido.")