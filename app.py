import streamlit as st
import requests
import pandas as pd

# --- CONFIG ---
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"  # <-- replace with your USDA API key
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# --- LOAD FPED ---
@st.cache_data
def load_fped():
    fped = pd.read_csv("FPED_1718.csv")
    return fped

fped = load_fped()

st.title("🥗 USDA Food Classifier with FPED")

# --- SEARCH ---
query = st.text_input("Search for a food (e.g. 'apple', 'milk')")
if st.button("Search") and query:
    params = {
        "api_key": FDC_API_KEY,
        "query": query,
        "pageSize": 25,
        "dataType": ["Foundation", "SR Legacy"]  # avoid Branded for now
    }
    r = requests.get(SEARCH_URL, params=params)
    if r.status_code != 200:
        st.error("API call failed")
    else:
        results = r.json().get("foods", [])
        # 🔑 keep only foods that have a foodCode → usable with FPED
        filtered = [f for f in results if f.get("foodCode")]

        if not filtered:
            st.warning("No USDA foods found with FNDDS codes (so no FPED match possible).")
        else:
            food_names = [f"{f['description']} ({f['fdcId']})" for f in filtered]
            selected = st.selectbox("Pick a food", food_names)

            if selected:
                chosen = filtered[food_names.index(selected)]
                st.write("**USDA Food Found:**", chosen["description"])
                food_code = chosen.get("foodCode")

                if food_code:
                    st.write("FNDDS food code:", food_code)

                    # Lookup in FPED
                    row = fped.loc[fped["food_code"] == int(food_code)]
                    if not row.empty:
                        st.subheader("FPED Classification")
                        st.dataframe(row.T)  # show all FPED components
                    else:
                        st.warning("No FPED mapping found for this food.")
