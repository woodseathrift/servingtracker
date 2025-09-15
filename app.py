import streamlit as st
import requests

# --- CONFIG ---
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

NUTRIENT_DENSE_CATEGORIES = [
    "Fruits and Fruit Juices",
    "Vegetables and Vegetable Products",
]

# --- APP TITLE ---
st.title("🥗 Serving Tracker (USDA)")

# --- SEARCH BAR ---
query = st.text_input("Search for a food (e.g. 'apple', 'pizza')")

if st.button("Search") and query:
    params = {
        "api_key": FDC_API_KEY,
        "query": query,
        "pageSize": 25,
        "dataType": ["Foundation", "SR Legacy"],
    }
    r = requests.get(SEARCH_URL, params=params)

    if r.status_code != 200:
        st.error("API call failed")
    else:
        foods = r.json().get("foods", [])

        # Keep only foods that have a category
        filtered = [f for f in foods if f.get("foodCategory")]

        if not filtered:
            st.warning("No foods with a category found.")
        else:
            # Save results in session_state for persistence
            st.session_state["search_results"] = filtered

# --- RESULTS DROPDOWN ---
if "search_results" in st.session_state:
    foods = st.session_state["search_results"]
    food_names = [f"{f['description']} ({f['foodCategory']})" for f in foods]

    selected = st.selectbox("Pick a food", food_names)

    if selected:
        chosen = foods[food_names.index(selected)]
        desc = chosen["description"]
        cat = chosen["foodCategory"]

        st.write("**USDA Food Found:**", desc)
        st.write("**Category:**", cat)

        # Nutrient vs Energy Dense classification
        if cat in NUTRIENT_DENSE_CATEGORIES:
            st.success("✅ Classified as **Nutrient-Dense Serving**")
        else:
            st.warning("⚡ Classified as **Energy-Dense Serving**")

        # Optional: show full JSON for debugging
        # st.json(chosen)
