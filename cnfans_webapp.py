import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import re
import requests

BASE_URL = "https://cnfans.com"

@st.cache_data(ttl=3600, show_spinner=False)
def get_exchange_rates():
    """
    Fetch latest currency exchange rates from exchangerate.host API.
    Base is CNY, retrieving USD and EUR rates.
    """
    url = "https://api.exchangerate.host/latest?base=CNY&symbols=USD,EUR"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        rates = data.get("rates", {})
        return {
            "EUR": rates.get("EUR", None),
            "USD": rates.get("USD", None)
        }
    except Exception:
        # On failure, fallback to None
        return {"EUR": None, "USD": None}


@st.cache_data(show_spinner=False)
def search_cnfans(keyword: str, max_price: float | None = None, max_results: int = 20):
    """
    Scrapes cnfans.com for products matching the keyword.
    Converts prices from CNY to EUR and USD using live exchange rates.
    Applies max_price filter on CNY price and limits results to max_results.
    Returns a list of dict with Title, Prices, Link and Image URL.
    """
    exchange_rates = get_exchange_rates()
    cny_to_eur = exchange_rates["EUR"] if exchange_rates["EUR"] else 0.13
    cny_to_usd = exchange_rates["USD"] if exchange_rates["USD"] else 0.14

    keyword_encoded = requests.utils.quote(keyword)
    search_url = f"{BASE_URL}/search?keywords={keyword_encoded}&searchType=keywords"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Referer": BASE_URL,
        "Connection": "keep-alive",
    }

    scraper = cloudscraper.create_scraper()

    try:
        response = scraper.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        st.error(f"Network error: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Try finding product containers; adjust selectors if site changes
    products = soup.find_all("li", class_="product-item")
    if not products:
        products = soup.find_all("div", class_="product-list-item")

    if not products:
        return []

    results = []
    count = 0

    for product in products:
        if count >= max_results:
            break

        # Extract product title
        title_tag = product.find("a", class_="product-title") or product.find("h3")
        # Extract price element
        price_tag = product.find("span", class_="price") or product.find("div", class_="price")
        # Extract product link
        link_tag = product.find("a", href=True)
        # Extract product image
        img_tag = product.find("img")
        
        if not (title_tag and price_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)

        price_text = price_tag.get_text(strip=True).replace("¥", "").replace(",", "")
        try:
            price_cny = float(re.search(r"[\d.]+", price_text).group())
        except Exception:
            price_cny = 99999  # fallback

        if max_price is not None and price_cny > max_price:
            continue

        link = link_tag["href"]
        if link.startswith("/"):
            link = BASE_URL + link

        img_url = img_tag["src"] if img_tag and img_tag.has_attr("src") else None
        if img_url and img_url.startswith("/"):
            img_url = BASE_URL + img_url

        price_eur = round(price_cny * cny_to_eur, 2)
        price_usd = round(price_cny * cny_to_usd, 2)

        results.append({
            "Title": title,
            "Price (¥)": price_cny,
            "Price (€)": price_eur,
            "Price ($)": price_usd,
            "Link": link,
            "ImgURL": img_url,
        })
        count += 1

    return results


def main():
    st.set_page_config(page_title="CNFans.com Scraper with Images", layout="centered")
    st.title("🛍️ CNFans.com Shop Scraper with Currency Conversion & Images")

    keyword = st.text_input("🔍 Enter keyword to search:", placeholder="e.g., Jersey, Jeans")
    max_price = st.number_input("Maximum price in CNY (¥)", min_value=0.0, step=1.0, format="%.2f")
    max_results = st.slider("Maximum number of results to display", 1, 50, 20)

    exchange_rates = get_exchange_rates()
    cny_to_eur = exchange_rates["EUR"]
    cny_to_usd = exchange_rates["USD"]

    if max_price > 0 and cny_to_eur and cny_to_usd:
        price_eur = round(max_price * cny_to_eur, 2)
        price_usd = round(max_price * cny_to_usd, 2)
        st.markdown(
            f"**Max Price Specified:** {max_price:.2f} CNY ≈ {price_eur:.2f} EUR ≈ {price_usd:.2f} USD"
        )
    elif max_price > 0:
        # fallback static rates if API fails
        price_eur = round(max_price * 0.13, 2)
        price_usd = round(max_price * 0.14, 2)
        st.markdown(
            f"**Max Price Specified:** {max_price:.2f} CNY ≈ {price_eur:.2f} EUR ≈ {price_usd:.2f} USD (using static rates)"
        )

    if st.button("Search"):
        if not keyword.strip():
            st.warning("Please enter a search keyword before searching.")
            return

        with st.spinner("🔎 Searching CNFans.com..."):
            results = search_cnfans(keyword, max_price=max_price if max_price > 0 else None, max_results=max_results)

        if not results:
            st.info("No products found matching the criteria.")
            return

        st.markdown("### Search Results")

        # Display each result with image and clickable link
        for item in results:
            cols = st.columns([1, 4])
            if item["ImgURL"]:
                with cols[0]:
                    st.image(item["ImgURL"], width=100, use_column_width=False)
            else:
                with cols[0]:
                    st.write("No Image")

            # Title as clickable link with prices below
            with cols[1]:
                st.markdown(
                    f"### [{item['Title']}]({item['Link']})", 
                    unsafe_allow_html=True
                )
                st.write(
                    f"Price: {item['Price (¥)']:.2f} CNY ≈ {item['Price (€)']:.2f} EUR ≈ {item['Price ($)']:.2f} USD"
                )
                st.markdown(f"[Open Product Link]({item['Link']})")

        # Optionally, add CSV download without images and links for simplicity
        df = pd.DataFrame(results)
        df_csv = df.drop(columns=["ImgURL"]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download results as CSV",
            data=df_csv,
            file_name=f"cnfans_search_results_{keyword}.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()
