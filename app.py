import streamlit as st
import requests

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

st.title("🥗 Food Category Lookup (Open Food Facts)")

query = st.text_input("Enter a food (e.g. apple, milk, cheerios):")

if st.button("Search") and query:
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 20  # limit results
    }
    r = requests.get(OFF_SEARCH_URL, params=params)

    if r.status_code != 200:
        st.error("Failed to fetch data from Open Food Facts.")
    else:
        data = r.json()
        products = data.get("products", [])

        # Filter out foods with no categories
        filtered = [p for p in products if p.get("categories")]

        if not filtered:
            st.warning("No foods with categories found.")
        else:
            # Build dropdown list
            names = [p.get("product_name", "Unknown") for p in filtered]
            choice = st.selectbox("Pick a food:", names)

            # Get selected product
            idx = names.index(choice)
            product = filtered[idx]

            st.subheader(choice)
            st.write("**Categories:**", product.get("categories", "Unknown"))

            nutriments = product.get("nutriments", {})
            kcal = nutriments.get("energy-kcal_100g")
            if kcal:
                st.write(f"**Calories per 100g:** {kcal} kcal")
            else:
                st.write("Calories: Not available")
