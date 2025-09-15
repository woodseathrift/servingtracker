import streamlit as st
import requests

# --- API Setup ---
API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"  # Get one free at https://fdc.nal.usda.gov/api-key-signup.html
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
DETAIL_URL = "https://api.nal.usda.gov/fdc/v1/food/{}"

st.title("🥦 USDA Food Category Lookup")

# --- SEARCH INPUT ---
query = st.text_input("Enter a food name (e.g. 'apple', 'milk', 'bread')")

if st.button("Search") and query:
    params = {"query": query, "pageSize": 10, "api_key": API_KEY}
    r = requests.get(SEARCH_URL, params=params)
    if r.status_code != 200:
        st.error("Search failed. Check API key or USDA service.")
    else:
        data = r.json()
        foods = data.get("foods", [])

        if not foods:
            st.warning("No foods found.")
        else:
            # Store results in session so dropdown persists
            st.session_state.search_results = [
                {"name": f["description"], "fdcId": f["fdcId"]}
                for f in foods
            ]

# --- SHOW DROPDOWN IF RESULTS EXIST ---
if "search_results" in st.session_state and st.session_state.search_results:
    food_names = [f["name"] for f in st.session_state.search_results]
    selected_name = st.selectbox("Select a food:", food_names)

    # Get fdcId for selected food
    selected_food = next(
        (f for f in st.session_state.search_results if f["name"] == selected_name),
        None
    )

    if selected_food and st.button("Get Details"):
        fdc_id = selected_food["fdcId"]
        r2 = requests.get(DETAIL_URL.format(fdc_id), params={"api_key": API_KEY})
        if r2.status_code == 200:
            detail = r2.json()
            st.write(f"**Food:** {detail.get('description', 'Unknown')}")
            st.write(f"**Category:** {detail.get('foodCategory', 'Unknown')}")
        else:
            st.error("Failed to fetch details.")
