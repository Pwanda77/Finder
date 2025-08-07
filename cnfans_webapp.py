import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import re
import requests

# Static currency conversion rates (update as needed)
CNY_TO_EUR = 0.13
CNY_TO_USD = 0.14

BASE_URL = "https://cnfans.com"

@st.cache_data(show_spinner=False)
def search_cnfans(keyword: str, max_price: float | None = None, max_results: int = 20) -> pd.DataFrame:
    """
    Scrapes cnfans.com for products matching the keyword.
    Converts prices from CNY to EUR and USD.
    Applies max_price filter on CNY price and limits results to max_results.
    Returns a pandas DataFrame with Title, Prices, and Link.
    """
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
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, "html.parser")

    # Try finding product containers; adjust selectors if site changes
    products = soup.find_all("li", class_="product-item")
    if not products:
        products = soup.find_all("div", class_="product-list-item")

    if not products:
        st.info("No products found.")
        return pd.DataFrame()

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

        if not (title_tag and price_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)

        price_text = price_tag.get_text(strip=True).replace("¥", "").replace(",", "")
        try:
            price_cny = float(re.search(r"[\d.]+", price_text).group())
        except Exception:
            price_cny = 99999  # Fallback big number if parsing fails

        if max_price is not None and price_cny > max_price:
            continue  # Skip price over max_price filter

        link = link_tag["href"]
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


def make_clickable(link: str) -> str:
    """Return HTML anchor tag to open link in new tab"""
    return f'<a href="{link}" target="_blank" rel="noopener noreferrer">Open Link</a>'


def main():
    st.set_page_config(page_title="CNFans.com Scraper", layout="centered")
    st.title("🛍️ CNFans.com Shop Scraper with Currency Conversion")

    keyword = st.text_input("🔍 Enter keyword to search:", placeholder="e.g., Jersey, Jeans")
    max_price = st.number_input("Maximum price in CNY (¥)", min_value=0.0, step=1.0, format="%.2f")
    max_results = st.slider("Maximum number of results to display", 1, 50, 20)

    if st.button("Search"):
        if not keyword.strip():
            st.warning("Please enter a search keyword before searching.")
            return

        with st.spinner("🔎 Searching CNFans.com..."):
            df = search_cnfans(keyword, max_price=max_price if max_price > 0 else None, max_results=max_results)

        if df.empty:
            st.info("No products found matching the criteria.")
            return

        # Convert links to clickable HTML
        df["Link"] = df["Link"].apply(make_clickable)

        # Display results as HTML table with clickable links
        st.markdown("### Search Results")
        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

        # Provide download button for CSV (without Link column or with clickable links if preferred)
        csv_data = df.drop(columns=["Link"]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download results as CSV",
            data=csv_data,
            file_name=f"cnfans_search_results_{keyword}.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
