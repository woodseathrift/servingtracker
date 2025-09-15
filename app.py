import streamlit as st
import requests

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

st.title("🥗 Food Category Lookup (Open Food Facts)")

# Initialize session state
if "results" not in st.session_state:
    st.session_state.results = []

query = st.text_input("Enter a food (e.g. apple, milk, cheerios):")

if st.button("Search") and query:
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 20
    }
    r = requests.get(OFF_SEARCH_URL, params=params)

    if r.status_code != 200:
        st.error("Failed to fetch data from Open Food Facts.")
        st.session_state.results = []
    else:
        data = r.json()
        products = data.get("products", [])

        # Filter out foods with no categories
        filtered = [p for p in products if p.get("categories")]
        st.session_state.results = filtered

if st.session_state.results:
    names = [p.get("product_name", "Unknown") for p in st.session_state.results]
    choice = st.selectbox("Pick a food:", names, key="food_picker")

    # Find the selected product
    idx = names.index(choice)
    product = st.session_state.results[idx]

    st.subheader(choice)
    st.write("**Categories:**", product.get("categories", "Unknown"))

    nutriments = product.get("nutriments", {})
    kcal = nutriments.get("energy-kcal_100g")
    if kcal:
        st.write(f"**Calories per 100g:** {kcal} kcal")
    else:
        st.write("Calories: Not available")
