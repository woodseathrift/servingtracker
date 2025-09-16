import streamlit as st
import requests
import datetime

# --- API SETUP ---
NUTRITIONIX_APP_ID = "5107911f"
NUTRITIONIX_APP_KEY = "39b7b779dbafa5fe4ae28af495a3c349"
NUTRITIONIX_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

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

st.title("🥗 Food Tracker (Serving Based)")

# --- USER INPUT ---
food_input = st.text_input("Enter a food:")
if st.button("Search") and food_input:
    data = {"query": food_input}
    response = requests.post(NUTRITIONIX_URL, headers=headers, json=data)
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
                base_serving = 100
                serving_type = "Energy-dense"
            else:
                base_serving = 50
                serving_type = "Nutrient-dense"

            servings = calories / base_serving

            choice = st.selectbox(
                f"How many servings of {name}?",
                [0.25, 0.5, 1, 2],
                key=name
            )

            if st.button(f"Add {name}"):
                if serving_type == "Energy-dense":
                    st.session_state.energy_servings += servings * choice
                else:
                    st.session_state.nutrient_servings += servings * choice

# --- DISPLAY TALLY ---
st.sidebar.header("Today's Totals")
st.sidebar.metric("Energy-dense Servings", round(st.session_state.energy_servings, 2))
st.sidebar.metric("Nutrient-dense Servings", round(st.session_state.nutrient_servings, 2))
