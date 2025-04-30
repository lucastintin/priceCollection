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

def gerar_html(jogos):
    html = """
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
            }
            .jogo {
                margin-bottom: 50px;
                border-bottom: 2px solid #ddd;
                padding-bottom: 30px;
            }
            img {
                width: 100%;
                max-height: 300px;
                object-fit: cover;
                border-radius: 8px;
                opacity: 0.2;
            }
            img:hover {
                opacity: 1.0;
            }
            .info {
                display: flex;
                justify-content: space-between;
                margin-top: 20px;
                
            }
            .col {
                width: 48%;
            }
            .rating {
                background: #f0f0f0;
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 10px;
                font-size: 1.2em;
            }
        </style>
    </head>
    <body>
    """

    for jogo in jogos:
        html += f"""
        <div class="jogo">
            <img src={jogo['image']} />
            <h1>{jogo['name']}</h1>
            <div class="info">
                <div class="col">
                    <p><strong>Ano Publicação:</strong> {jogo['year']}</p>
                    <p><strong>Jogadores:</strong> {jogo['stats']['minplayers']} - {jogo['stats']['maxplayers']}</p>
                    <p><strong>Duração:</strong> {jogo['stats']['minplaytime']} - {jogo['stats']['maxplaytime']} min.</p>
                    <p><strong>Partidas:</strong> {jogo['numplays']}</p>
                </div>
                <div class="col">
                    <div>
                        <strong>Preço Histórico Máximo</strong>
                    </div>
                    <div> </div>
                    <div> </div>
                    <div>
                        <strong>Preço Histórico Mínimo</strong>
                    </div>
                </div>
            </div>
        </div>
        """

    html += "</body></html>"
    return html

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
    url = f"https://boardgamegeek.com/xmlapi2/collection?username={username}&own=1&stats=1 "
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
            prices = fetch_price_USD(game_id)
            price = prices[0]['price']

            numplays = item.find("numplays").text
            image = item.find("image").text if item.find("image") is not None else None
            stats = {
                "vendidos": item.find("stats").attrib["numowned"] if item.find("stats") is not None else 0,
                "minplayers": item.find("stats").attrib["minplayers"] if item.find("stats") is not None else 0,
                "maxplayers": item.find("stats").attrib["maxplayers"] if item.find("stats") is not None else 0,
                "minplaytime": item.find("stats").attrib["minplaytime"] if item.find("stats") is not None else 0,
                "maxplaytime": item.find("stats").attrib["maxplaytime"] if item.find("stats") is not None else 0,
            }
            games.append({"id": game_id, "name": name, "year": year, "price": price, "prices": prices, "image": image, "numplays":numplays, "stats": stats })
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
if "catalogoCreated" not in st.session_state:
    st.session_state["catalogoCreated"] = False

def changeCatalogoState():
    st.session_state["catalogoCreated"] = True

st.set_page_config(page_title="Vale Ouro", layout="wide")

st.title("Quanto vale minha coleção de Boardgames?")

username = st.text_input("Digite seu nome de usuário do BoardGameGeek")

if st.button("Buscar coleção") and username:
    tab1, tab2, tab3, tab4 = st.tabs(["Valores", "Análise", "Catálogo", "Sugestões"])
    with st.spinner("Consultando coleção no BGG...Se você achar que está demorando, venda alguns jogos!"):
        collection = fetch_collection(username)
        priceTotal = 0
        maxPriceTotal = 0
        minPriceTotal = 0
        data  = []
        porJogas = sorted(collection, key=lambda jogo: int(jogo['numplays']))

    with tab1:
       st.info(f"{len(collection)} jogos encontrados!")
       with st.spinner("Calculando valores no mercado..."):
        if collection:
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
                st.write(f"{porJogas[-1]['name']} jogado {porJogas[-1]['numplays']} vezes")

            with kol3: 
                st.subheader("⬇️ Menos jogado:")
                #st.image(porJogas[0]['image'], width=200)
                st.write(f"{porJogas[0]['name']} jogado {porJogas[0]['numplays']} vezes")
            st.divider()

            col1, col2, col3 = st.columns(3)
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
                st.subheader("🧙 Designers mais frequentes")
                for aut, count in aut_top[:10]:
                    st.write(f"{aut}: {count} jogos")
                st.altair_chart(plot_frequencia("🧙 Designers mais presentes", aut_top))
    
    with tab3:
        st.subheader("Catálogo de jogos")  
        pagHTML = gerar_html(collection)
        if st.session_state["catalogoCreated"]:
            st.warning("Zé, eu vou mudar um monte de coisa ainda.")
            st.download_button(
                label="Baixar catálogo",
                data=pagHTML,
                file_name="catalogo.html",
                mime="text/html",
            )
            st.divider()
        st.html(pagHTML)
        st.session_state["catalogoCreated"] = True 
        st.toast("O catálogo foi gerado em HTML, para você abrir no navegador. Você pode usar o botão acima para baixar o arquivo.")

    #Sugestão - Aqui que é o PUNK              
    # with st.spinner("Pensando em sugestões..."):
    with tab4:
        st.subheader("Sugestões de jogos semelhantes.")  
        st.write("Em breve!")