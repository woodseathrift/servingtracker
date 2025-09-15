import streamlit as st
import requests
import pandas as pd
import json

# --- CONFIG ---
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"  # <-- replace with your USDA API key
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# --- LOAD FPED ---
@st.cache_data
def load_fped():
    fped = pd.read_csv("FPED_1718.csv")
    return fped

fped = load_fped()

st.title("🥗 USDA Food Classifier with FPED (Debug Mode)")

# --- SEARCH ---
query = st.text_input("Search for a food (e.g. 'apple', 'milk')")
if st.button("Search") and query:
    params = {
        "api_key": FDC_API_KEY,
        "query": query,
        "pageSize": 10,
        "dataType": ["Foundation", "SR Legacy"]  # avoid Branded
    }
    r = requests.get(SEARCH_URL, params=params)
    if r.status_code != 200:
        st.error("API call failed")
    else:
        results = r.json().get("foods", [])

        if not results:
            st.warning("No foods found.")
        else:
            # 🔎 Debug: show first result’s structure
            st.subheader("First result (raw JSON)")
            st.json(results[0])

            # Try to filter on foodCode if it exists
            filtered = [f for f in results if f.get("foodCode")]
            if not filtered:
                st.warning("No foods with 'foodCode' field. Check JSON above for alternatives.")
            else:
                food_names = [f"{f['description']} ({f['fdcId']})" for f in filtered]
                selected = st.selectbox("Pick a food", food_names)

                if selected:
                    chosen = filtered[food_names.index(selected)]
                    st.write("**USDA Food Found:**", chosen["description"])
                    food_code = chosen.get("foodCode")
                    st.write("FNDDS food code:", food_code)

                    row = fped.loc[fped["food_code"] == int(food_code)]
                    if not row.empty:
                        st.subheader("FPED Classification")
                        st.dataframe(row.T)
                    else:
                        st.warning("No FPED mapping found for this food.")
