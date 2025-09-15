import streamlit as st
import requests
import pandas as pd

# --- CONFIG ---
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"  # <-- replace with your USDA API key
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# --- LOAD FPED ---
@st.cache_data
def load_fped():
    fped = pd.read_csv("FPED_1718.csv")  # local file in your repo
    return fped

fped = load_fped()

st.title("🥗 USDA Food Classifier with FPED")

# --- SEARCH ---
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

        if not results:
            st.warning("No foods found.")
        else:
            # ✅ Keep only foods with a category
            filtered = [f for f in results if f.get("foodCategory")]

            if not filtered:
                st.warning("No foods with a foodCategory available.")
            else:
                food_names = [
                    f"{f['description']} ({f['foodCategory']})"
                    for f in filtered
                ]
                selected = st.selectbox("Pick a food", food_names)

                if selected:
                    chosen = filtered[food_names.index(selected)]
                    st.write("**USDA Food Found:**", chosen["description"])
                    st.write("**Category:**", chosen.get("foodCategory"))

                    # 👉 At this point, if you want to map foodCategory → FPED
                    # you’ll need a lookup table, because FPED uses food_code
                    # not foodCategory labels.
                    # Example:
                    category = chosen.get("foodCategory")
                    row = fped.loc[fped["food_category"] == category] if "food_category" in fped.columns else None
                    
                    if row is not None and not row.empty:
                        st.subheader("FPED Classification")
                        st.dataframe(row.T)
                    else:
                        st.info("No FPED mapping found for this foodCategory.")
