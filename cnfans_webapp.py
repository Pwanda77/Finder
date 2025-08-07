import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Static exchange rates for conversions
CNY_TO_EUR = 0.13
CNY_TO_USD = 0.14

BASE_URL = "https://cnfans.com"

@st.cache_data
def search_cnfans(keyword, max_price=None, max_results=20):
    keyword_encoded = requests.utils.quote(keyword)
    search_url = f"{BASE_URL}/search?keywords={keyword_encoded}&searchType=keywords"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Network error: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, "html.parser")

    # Find product containers - update selector based on actual site structure:
    products = soup.find_all("li", class_="product-item")
    if not products:
        # Try alternative selector if needed:
        products = soup.find_all("div", class_="product-list-item")

    if not products:
        st.info("No products found.")
        return pd.DataFrame()

    results = []
    count = 0

    for product in products:
        if count >= max_results:
            break

        # Extract title
        title_tag = product.find("a", class_="product-title") or product.find("h3")
        # Extract price
        price_tag = product.find("span", class_="price") or product.find("div", class_="price")
        # Extract link
        link_tag = product.find("a", href=True)

        if not (title_tag and price_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        price_text = price_tag.get_text(strip=True).replace("¥", "").replace(",", "")
        try:
            price_cny = float(re.search(r"[\d.]+", price_text).group())
        except:
            price_cny = 99999  # fallback for no price or parse error

        if max_price and price_cny > max_price:
            continue

        link = link_tag['href']
        # If link is relative, prepend BASE_URL
        if link.startswith("/"):
            link = BASE_URL + link

        price_eur = round(price_cny * CNY_TO_EUR, 2)
        price_usd = round(price_cny * CNY_TO_USD, 2)

        results.append({
            "Title": title,
            "Price (¥)": price_cny,
            "Price (€)": price_eur,
            "Price ($)": price_usd,
            "Link": link,
        })
        count += 1

    return pd.DataFrame(results)

def make_clickable(link):
    return f'<a href="{link}" target="_blank">Open Link</a>'

def main():
    st.title("CNFans.com Shop Scraper with Currency Conversion")

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
