import re
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

@st.cache_data
def search_cnfans(keyword, max_price=None, max_results=20):
    keyword_encoded = requests.utils.quote(keyword)
    search_url = f"https://cnfans.shop/search?q={keyword_encoded}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Network error: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, "html.parser")
    products = soup.find_all("div", class_="product-card")

    results = []
    for product in products[:max_results]:
        title_tag = product.find("h3")
        price_tag = product.find("span", class_="price")
        link_tag = product.find("a", href=True)

        if title_tag and price_tag and link_tag:
            title = title_tag.text.strip()
            price_text = price_tag.text.strip().replace("¥", "")
            price_match = re.search(r"[\d,.]+", price_text)
            if price_match:
                price = float(price_match.group().replace(",", ""))
            else:
                price = 99999

            link = "https://cnfans.shop" + link_tag["href"]

            if not max_price or price <= max_price:
                results.append({"Title": title, "Price (¥)": price, "Link": link})

    return pd.DataFrame(results)
