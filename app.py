import streamlit as st
import requests
import datetime

# --- API SETUP ---
NUTRITIONIX_APP_ID = "5107911f"
NUTRITIONIX_APP_KEY = "39b7b779dbafa5fe4ae28af495a3c349"
SEARCH_URL = "https://trackapi.nutritionix.com/v2/search/instant"
NUTR_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

headers = {
    "x-app-id": NUTRITIONIX_APP_ID,
    "x-app-key": NUTRITIONIX_APP_KEY,
    "Content-Type": "application/json"
}

# --- RESET SERVINGS DAILY ---
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.search_results = []  # clear old search
    st.session_state.selected_food = None

st.title("🥗 Food Tracker (Serving Based)")

# --- USER INPUT ---
food_input = st.text_input("Enter a food:")

if st.button("Search") and food_input:
    response = requests.get(
        SEARCH_URL,
        headers=headers,
        params={"query": food_input, "detailed": True}
    )
    if response.status_code == 200:
        data = response.json()
        # Grab up to 10 branded + common food names
        results = [f["food_name"] for f in data.get("common", [])[:10]]
        if results:
            st.session_state.search_results = results
        else:
            st.warning("No foods found. Try a different search.")

# --- DROPDOWN TO CHOOSE FROM SEARCH RESULTS ---
if st.session_state.search_results:
    food_choice = st.selectbox(
        "Select a food:",
        st.session_state.search_results
    )
    st.session_state.selected_food = food_choice

# --- NUTRITION LOOKUP + SERVINGS FORM ---
if st.session_state.selected_food:
    data = {"query": st.session_state.selected_food}
    response = requests.post(NUTR_URL, headers=headers, json=data)

    if response.status_code == 200:
        food_data = response.json()
        for item in food_data.get("foods", []):
            name = item["food_name"].title()
            calories = item["nf_calories"]
            serving_qty = item["serving_qty"]
            serving_unit = item["serving_unit"]

            st.write(f"**{name}**")
            st.write(f"1 {serving_qty} {serving_unit} = {calories:.0f} kcal")

            # --- CALCULATE SERVINGS ---
            if calories >= 80:
                base_serving_
