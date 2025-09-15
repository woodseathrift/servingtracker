import streamlit as st
import requests

# --- CONFIG ---
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# --- APP ---
st.title("🥗 USDA Food Category Filter")

query = st.text_input("Search for a food (e.g. 'apple', 'carrot')")

if st.button("Search") and query:
    params = {
        "api_key": FDC_API_KEY,
        "query": query,
        "pageSize": 25,
        "dataType": ["Foundation", "SR Legacy"]
    }
    r = requests.get(SEARCH_URL, params=params)
    if r.status_code != 200:
        st.error("API call failed")
    else:
        foods = r.json().get("foods", [])
        # keep only Fruits & Vegetables
        filtered = [
            f for f in foods
            if f.get("foodCategory") in [
                "Fruits and Fruit Juices",
                "Vegetables and Vegetable Products"
            ]
        ]

        if not filtered:
            st.warning("No fruits or vegetables found in results.")
        else:
            names = [f"{f['description']} ({f['foodCategory']})" for f in filtered]
            selected = st.selectbox("Pick a food", names)
            if selected:
                chosen = filtered[names.index(selected)]
                st.write("**Food:**", chosen["description"])
                st.write("**Category:**", chosen["foodCategory"])
                st.json(chosen)  # show all USDA fields
