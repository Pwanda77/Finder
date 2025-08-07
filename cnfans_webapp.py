import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Static exchange rates: adjust as needed or fetch live rates
CNY_TO_EUR = 0.13
CNY_TO_USD = 0.14

@st.cache_data
def search_cnfans(keyword, max_price=None, max_results=20):
    keyword_encoded = requests.utils.quote(keyword)
    # Try primary search URL pattern
    urls_to_try = [
        f"https://cnfans.shop/search?type=product&q={keyword_encoded}",
        f"https://cnfans.shop/collections/all?q={keyword_encoded}"
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    response = None
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                response = resp
                search_url_used = url
                break
        except requests.RequestException:
            continue

    if not response:
        st.error("No valid search results page found (received 404 or network error).")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, "html.parser")
    products = soup.find_all("div", class_="product-card")

    if not products:
        st.info("No products found on the search page.")
        return pd.DataFrame()

    results = []
    count = 0
    for product in products:
        if count >= max_results:
            break
        title_tag = product.find("h3")
        price_tag = product.find("span", class_="price")
        link_tag = product.find("a", href=True)

        if title_tag and price_tag and link_tag:
            title = title_tag.text.strip()
            price_text = price_tag.text.strip().replace("¥", "")
            price_match = re.search(r"[\d,.]+", price_text)
            if price_match:
                try:
                    price_cny = float(price_match.group().replace(",", ""))
                except:
                    price_cny = 99999
            else:
                price_cny = 99999  # fallback price high

            link = "https://cnfans.shop" + link_tag["href"]

            if (not max_price) or (price_cny <= max_price):
                price_eur = round(price_cny * CNY_TO_EUR, 2)
                price_usd = round(price_cny * CNY_TO_USD, 2)
                results.append({
                    "Title": title,
                    "Price (¥)": price_cny,
                    "Price (€)": price_eur,
                    "Price ($)": price_usd,
                    "Link": link
                })
                count += 1

    return pd.DataFrame(results)

def make_clickable(link):
    return f'<a href="{link}" target="_blank">Open Link</a>'

def main():
    st.title("CNFans Shop Scraper with Currency Conversion")

    keyword = st.text_input("Enter keyword to search:", "")
    max_price = st.number_input("Max price in CNY (¥):", min_value=0.0, step=1.0, format="%.2f")
    max_results = st.slider("Max results to display:", 1, 50, 20)

    if st.button("Search"):
        if not keyword.strip():
            st.warning("Please enter a search keyword.")
            return

        with st.spinner("Searching CNFans..."):
            df = search_cnfans(keyword, max_price=max_price if max_price > 0 else None, max_results=max_results)

        if df.empty:
            st.info("No results found.")
        else:
            df["Link"] = df["Link"].apply(make_clickable)
            st.write(df.to_html(escape=False), unsafe_allow_html=True)

            csv = df.drop(columns=["Link"]).to_csv(index=False).encode("utf-8")
            st.download_button("Download results as CSV", csv, "cnfans_results.csv", "text/csv")

if __name__ == "__main__":
    main()
