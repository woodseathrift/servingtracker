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
    if (
        st.session_state.selected_food
        and st.session_state.selected_food in st.session_state.search_results
    ):
        idx = st.session_state.search_results.index(st.session_state.selected_food)
    else:
        idx = 0

    choice = st.selectbox(
        "Choose a food:",
        st.session_state.search_results,
        index=idx,
        key="food_choice"
    )
    st.session_state.selected_food = choice

# --- NUTRITION LOOKUP + SERVINGS FORM ---
if st.session_state.selected_food:
    data = {"query": st.session_state.selected_food}
    response = requests.post(NUTR_URL, headers=headers, json=data)

    if response.status_code == 200:
        food_data = response.json()
        for item in food_data.get("foods", []):
            name = item.get("food_name", "Unknown").title()
            calories = item.get("nf_calories", 0) or 0
            serving_qty = item.get("serving_qty", 1)
            serving_unit = item.get("serving_unit", "")

            st.write(f"**{name}**")
            st.write(f"1 {serving_qty} {serving_unit} = {calories:.0f} kcal")

            # --- CALCULATE SERVINGS SAFELY ---
            if calories >= 80:
                base_serving = 100
                serving_type = "Energy-dense"
            else:
                base_serving = 50
                serving_type = "Nutrient-dense"

            servings = calories / base_serving if base_serving > 0 else 0

            # --- FORM FOR SERVING SIZE ---
            with st.form(key=f"{name}_form"):
                portion = st.selectbox(
                    f"How many servings of {name}?",
                    [0.25, 0.5, 1, 2]
                )
                submitted = st.form_submit_button(f"Add {name}")
                if submitted:
                    if serving_type == "Energy-dense":
                        st.session_state.energy_servings += servings * portion
                    else:
                        st.session_state.nutrient_servings += servings * portion
                    st.success(f"Added {portion} serving(s) of {name} ✅")

# --- DISPLAY TALLY ---
st.sidebar.header("Today's Totals")
st.sidebar.metric("Energy-dense Servings", round(st.session_state.energy_servings, 2))
st.sidebar.metric("Nutrient-dense Servings", round(st.session_state.nutrient_servings, 2))
