import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import re
import requests

BASE_URL = "https://cnfans.com"

@st.cache_data(ttl=3600, show_spinner=False)
def get_exchange_rates():
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
        return {"EUR": None, "USD": None}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_product_page(url: str) -> BeautifulSoup | None:
    """Fetch product detail page and return BeautifulSoup object"""
    scraper = cloudscraper.create_scraper()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
    try:
        response = scraper.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        st.warning(f"Failed to fetch product page {url}: {e}")
        return None

def find_spreadsheet_links(soup: BeautifulSoup) -> list[str]:
    """
    Search the product page content for Google Sheets URLs or other spreadsheet links.
    Returns a list of unique spreadsheet URLs.
    """
    spreadsheet_links = set()

    # Find all <a> tags href containing docs.google.com/spreadsheets
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "docs.google.com/spreadsheets" in href.lower():
            spreadsheet_links.add(href.split("?")[0])  # remove URL parameters for neatness

    # Additionally, search raw text for spreadsheet URLs (just in case)
    text = soup.get_text()
    found_urls = re.findall(r"https?://docs\.google\.com/spreadsheets/[^\s'\"]+", text, re.IGNORECASE)
    for url in found_urls:
        spreadsheet_links.add(url.split("?")[0])

    return list(spreadsheet_links)

@st.cache_data(show_spinner=False)
def search_cnfans(keyword: str, max_price: float | None = None, max_results: int = 20):
    exchange_rates = get_exchange_rates()
    cny_to_eur = exchange_rates["EUR"] if exchange_rates["EUR"] else 0.13
    cny_to_usd = exchange_rates["USD"] if exchange_rates["USD"] else 0.14

    keyword_encoded = requests.utils.quote(keyword)
    search_url = f"{BASE_URL}/search?keywords={keyword_encoded}&searchType=keywords"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
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

    product_selectors = [
        ("li", "product-item"),
        ("div", "product-list-item"),
        ("div", "search-item"),
        ("div", "item"),
    ]

    products = []
    for tag, class_name in product_selectors:
        found = soup.find_all(tag, class_=class_name)
        if found:
            products = found
            break

    if not products:
        st.warning("Could not find product elements with current selectors. Site structure may have changed.")
        return []

    results = []
    count = 0

    for product in products:
        if count >= max_results:
            break

        try:
            title_tag = product.find("a", class_="product-title") or product.find("h3") or product.find("a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)

            price_tag = product.find("span", class_="price") or product.find("div", class_="price") or product.find("em", class_="price") or product.find("span")
            if not price_tag:
                continue

            price_text = price_tag.get_text(strip=True).replace("¥", "").replace(",", "")
            price_numbers = re.findall(r"[\d.]+", price_text)
            if not price_numbers:
                continue
            price_cny = float(price_numbers[0])

            if max_price is not None and price_cny > max_price:
                continue

            link_tag = product.find("a", href=True)
            if not link_tag:
                continue

            link = link_tag["href"]
            if link.startswith("/"):
                link = BASE_URL + link

            img_tag = product.find("img")
            img_url = None
            if img_tag and img_tag.has_attr("src"):
                img_url = img_tag["src"]
                if img_url.startswith("/"):
                    img_url = BASE_URL + img_url

            # Fetch product page to find spreadsheet links
            product_soup = fetch_product_page(link)
            spreadsheet_links = find_spreadsheet_links(product_soup) if product_soup else []

            price_eur = round(price_cny * cny_to_eur, 2)
            price_usd = round(price_cny * cny_to_usd, 2)

            results.append({
                "Title": title,
                "Price (¥)": price_cny,
                "Price (€)": price_eur,
                "Price ($)": price_usd,
                "Link": link,
                "ImgURL": img_url,
                "Spreadsheet Links": spreadsheet_links,
            })
            count += 1
        except Exception as e:
            st.write(f"Skipped one product due to parsing error: {e}")
            continue

    return results

def main():
    st.set_page_config(page_title="CNFans.com Shop Scraper with Spreadsheets", layout="centered")
    st.title("🛍️ CNFans.com Shop Scraper with Currency Conversion & Spreadsheet Links")

    keyword = st.text_input("🔍 Enter keyword to search:", placeholder="e.g., Jersey, Jeans")
    max_price = st.number_input("Maximum price in CNY (¥)", min_value=0.0, step=1.0, format="%.2f")
    max_results = st.slider("Maximum number of results to display", 1, 20, 10)

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
        price_eur = round(max_price * 0.13, 2)
        price_usd = round(max_price * 0.14, 2)
        st.markdown(
            f"**Max Price Specified:** {max_price:.2f} CNY ≈ {price_eur:.2f} EUR ≈ {price_usd:.2f} USD (using static rates)"
        )

    if st.button("Search"):
        if not keyword.strip():
            st.warning("Please enter a search keyword before searching.")
            return

        with st.spinner("🔎 Searching CNFans.com and scanning for spreadsheets... (this may take some seconds)"):
            results = search_cnfans(keyword, max_price=max_price if max_price > 0 else None, max_results=max_results)

        if not results:
            st.info("No products found matching the criteria.")
            return

        st.markdown("### Search Results")

        for item in results:
            cols = st.columns([1, 5])
            if item["ImgURL"]:
                with cols[0]:
                    st.image(item["ImgURL"], width=100, use_column_width=False)
            else:
                with cols[0]:
                    st.write("No Image")

            with cols[1]:
                st.markdown(f"### [{item['Title']}]({item['Link']})", unsafe_allow_html=True)
                st.write(f"Price: {item['Price (¥)']:.2f} CNY ≈ {item['Price (€)']:.2f} EUR ≈ {item['Price ($)']:.2f} USD")
                if item["Spreadsheet Links"]:
                    st.markdown("**Spreadsheet Links:**")
                    for url in item["Spreadsheet Links"]:
                        st.markdown(f"- [Google Sheet]({url})", unsafe_allow_html=True)
                else:
                    st.write("*No spreadsheet links found*")

        # Prepare dataframe for CSV export -- flatten spreadsheet list to comma-separated string
        df = pd.DataFrame(results)
        df["Spreadsheet Links"] = df["Spreadsheet Links"].apply(lambda links: ", ".join(links) if links else "")
        df_csv = df.drop(columns=["ImgURL"]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download results as CSV",
            data=df_csv,
            file_name=f"cnfans_search_results_{keyword}.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()
