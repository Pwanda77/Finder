import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

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
                price = float(price_match.group().replace(",", ""))
            else:
                price = 99999  # fallback high price

            link = "https://cnfans.shop" + link_tag["href"]

            if not max_price or price <= max_price:
                results.append({"Title": title, "Price (¥)": price, "Link": link})
                count += 1

    return pd.DataFrame(results)

def make_clickable(link):
    return f'<a href="{link}" target="_blank">Link</a>'

def main():
    st.title("CNFans Shop Scraper")

    # Search bar
    keyword = st.text_input("Enter keyword to search:", "")
    max_price = st.number_input("Max price (¥):", min_value=0.0, step=1.0, format="%.2f")
    max_results = st.slider("Max results to display:", min_value=1, max_value=50, value=20)

    if st.button("Search"):
        if not keyword.strip():
            st.warning("Please enter a valid keyword before searching.")
            return

        with st.spinner("Searching CNFans..."):
            df = search_cnfans(keyword, max_price=max_price, max_results=max_results)

        if df.empty:
            st.info("No results found.")
        else:
            # Make link clickable
            df["Link"] = df["Link"].apply(make_clickable)
            st.write("### Search Results")
            st.write(df.to_html(escape=False), unsafe_allow_html=True)

            # Download button
            csv = df.drop(columns=["Link"]).to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download results as CSV",
                data=csv,
                file_name='cnfans_search_results.csv',
                mime='text/csv',
            )

if __name__ == "__main__":
    main()
