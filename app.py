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
            food_group = item.get("tags", {}).get("food_group", "").lower()

            st.write(f"**{name}**")
            st.write(f"Nutritionix serving: {serving_qty} {serving_unit} = {calories:.0f} kcal")

            # --- CALCULATE BASE SERVING ---
            if "fruit" in food_group or "vegetable" in food_group:
                base_serving = 50   # fruits/vegetables → nutrient-dense
                serving_type = "Nutrient-dense"
            else:
                base_serving = 100  # everything else → energy-dense
                serving_type = "Energy-dense"

            servings = calories / base_serving

            # round servings to nearest 0.25
            servings = round(servings * 4) / 4.0

            # --- USER CHOICE ---
            with st.form(key=f"{name}_form"):
                choice = st.selectbox(
                    f"How many servings of {name}? ({serving_type})",
                    [0.25, 0.5, 0.75, 1, 2, 3],
                    index=3  # default 1
                )
                submitted = st.form_submit_button(f"Add {name}")
                if submitted:
                    if serving_type == "Energy-dense":
                        st.session_state.energy_servings += servings * choice
                    else:
                        st.session_state.nutrient_servings += servings * choice

# --- MANUAL ENTRY ---
st.sidebar.subheader("➕ Add Servings Manually")
manual_type = st.sidebar.selectbox(
    "Serving type:",
    ["Nutrient-dense", "Energy-dense"]
)
manual_qty = st.sidebar.selectbox(
    "How many servings?",
    [0.25, 0.5, 0.75, 1, 2, 3, 4],
    index=3  # default 1
)
if st.sidebar.button("Add Manual Serving"):
    if manual_type == "Energy-dense":
        st.session_state.energy_servings += manual_qty
    else:
        st.session_state.nutrient_servings += manual_qty

# --- DISPLAY TALLY ---
st.sidebar.header("Today's Totals")
st.sidebar.metric("Energy-dense Servings", round(st.session_state.energy_servings, 2))
st.sidebar.metric("Nutrient-dense Servings", round(st.session_state.nutrient_servings, 2))
