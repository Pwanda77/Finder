import streamlit as st
import requests

# Cache the exchange rates for 1 hour to minimize API calls
@st.cache_data(ttl=3600)
def get_exchange_rates():
    url = "https://api.exchangerate.host/latest?base=CNY&symbols=USD,EUR"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        rates = data.get('rates', {})
        return rates
    except requests.RequestException:
        return {}

def main():
    st.title("Your App Title Here")

    # ------------------
    # YOUR EXISTING LOGIC TO CALCULATE max_price_cny
    # For demo, I put a static example price:
    max_price_cny = 1234.56
    # ------------------

    # Fetch exchange rates
    rates = get_exchange_rates()

    # Display prices with conversions if possible
    st.markdown("### Maximum Price")

    if rates:
        price_usd = max_price_cny * rates.get('USD', 0)
        price_eur = max_price_cny * rates.get('EUR', 0)

        st.write(f"**{max_price_cny:.2f} CNY**")
        st.write(f"≈ {price_eur:.2f} EUR")
        st.write(f"≈ {price_usd:.2f} USD")
    else:
        st.error("Failed to fetch exchange rates. Showing only CNY price.")
        st.write(f"**{max_price_cny:.2f} CNY**")


if __name__ == "__main__":
    main()
