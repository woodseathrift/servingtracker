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
    st.session_state.search_results = []
    st.session_state.selected_food = None

st.title("🥗 Food Tracker (Serving Based)")

# --- USER SEARCH ---
food_input = st.text_input("Enter a food:")
if st.button("Search") and food_input:
    response = requests.get(SEARCH_URL, headers=headers, params={"query": food_input})
    if response.status_code == 200:
        results = response.json().get("common", [])[:10]  # limit to 10 choices
        st.session_state.search_results = [f["food_name"] for f in results]
        if st.session_state.search_results:
            st.session_state.selected_food = st.session_state.search_results[0]

# --- FOOD DROPDOWN ---
if st.session_state.search_results:
    choice = st.selectbox(
        "Choose a food:",
        st.session_state.search_results,
