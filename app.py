import streamlit as st
import requests

# USDA API base
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
DETAIL_URL = "https://api.nal.usda.gov/fdc/v1/food/{}"
API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"  # <-- replace with your USDA API key

st.title("🍎 USDA Food Category Lookup")

# Search input
query = st.text_input("Enter a food (e.g. 'apple', 'chicken'):")

if st.button("Search") and query:
    params = {
        "api_key": API_KEY,
        "query": query,
        "pageSize": 20
    }
    r = requests.get(SEARCH_URL, params=params)
    if r.status_code != 200:
        st.error("Search failed.")
    else:
        results = r.json().get("foods", [])
        
        # Filter out those with no category
        filtered = [f for f in results if f.get("foodCategory")]
        
        if not filtered:
            st.warning("No foods found with a category.")
        else:
            # Show dropdown of descriptions
            options = {f["description"]: f["fdcId"] for f in filtered}
            sel_desc = st.selectbox("Pick a food", list(options.keys()))
            
            if st.button("Show details"):
                fdc_id = options[sel_desc]
                d = requests.get(DETAIL_URL.format(fdc_id), params={"api_key": API_KEY})
                if d.status_code == 200:
                    detail = d.json()
                    st.json({
                        "description": detail.get("description"),
                        "fdcId": detail.get("fdcId"),
                        "foodCategory": detail.get("foodCategory"),
                        "servingSize": detail.get("servingSize"),
                        "servingSizeUnit": detail.get("servingSizeUnit"),
                    })
                else:
                    st.error("Failed to fetch details.")
