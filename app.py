import streamlit as st
import requests
import pandas as pd

# --- CONFIG ---
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"  # <-- replace with your USDA API key
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# Load FPED from local repo
@st.cache_data
def load_fped():
    # Adjust path if you put it in a subfolder (e.g. "data/FPED_1718.xls")
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
        "pageSize": 10,
        "dataType": ["Foundation", "SR Legacy"]  # avoid Branded for now
    }
    r = requests.get(SEARCH_URL, params=params)
    if r.status_code != 200:
        st.error("API call failed")
    else:
        results = r.json().get("foods", [])
        if not results:
            st.warning("No foods found")
        else:
            food_names = [f"{f['description']} ({f['fdcId']})" for f in results]
            selected = st.selectbox("Pick a food", food_names)
            chosen = results[food_names.index(selected)]
            
            st.write("**USDA Food Found:**", chosen["description"])
            food_code = chosen.get("foodCode")  # FNDDS code
            
            if food_code:
                st.write("FNDDS food code:", food_code)
                
                # Lookup in FPED
                row = fped.loc[fped["food_code"] == int(food_code)]
                if not row.empty:
                    st.subheader("FPED Classification")
                    st.dataframe(row.T)  # show all food pattern equivalents
                else:
                    st.warning("No FPED mapping found for this food.")
            else:
                st.warning("This USDA food has no FNDDS code → cannot match FPED.")
