import streamlit as st
import requests
import pandas as pd

# --- CONFIG ---
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"  # replace with your USDA API key
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# --- LOAD FPED ---
@st.cache_data
def load_fped():
    return pd.read_csv("FPED_1718.csv")  # local file in your repo

fped = load_fped()

st.title("🥗 USDA Food Classifier with FPED")

# --- SEARCH BAR ---
query = st.text_input("Search for a food (e.g. 'apple', 'milk')")

if st.button("Search") and query:
    params = {
        "api_key": FDC_API_KEY,
        "query": query,
        "pageSize": 20,
        "dataType": ["Foundation", "SR Legacy"]  # avoid Branded
    }
    r = requests.get(SEARCH_URL, params=params)

    if r.status_code != 200:
        st.error("API call failed")
    else:
        results = r.json().get("foods", [])
        filtered = [f for f in results if f.get("foodCategory")]

        if not filtered:
            st.warning("No foods with a foodCategory available.")
        else:
            # Store results in session_state so dropdown persists
            st.session_state["search_results"] = filtered

# --- SHOW RESULTS ---
if "search_results" in st.session_state:
    foods = st.session_state["search_results"]
    food_names = [f"{f['description']} ({f['foodCategory']})" for f in foods]

    selected = st.selectbox("Pick a food", food_names)

    if selected:
        chosen = foods[food_names.index(selected)]
        st.write("**USDA Food Found:**", chosen["description"])
        st.write("**Category:**", chosen.get("foodCategory"))

        # Example FPED matching (placeholder)
        category = chosen.get("foodCategory")
        if "food_category" in fped.columns:
            row = fped.loc[fped["food_category"] == category]
        else:
            row = None

        if row is not None and not row.empty:
            st.subheader("FPED Classification")
            st.dataframe(row.T)
        else:
            st.info("No FPED mapping found for this foodCategory.")
