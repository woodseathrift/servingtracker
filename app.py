import streamlit as st
import requests
import datetime

# --- API SETUP ---
NUTRITIONIX_APP_ID = "5107911f"
NUTRITIONIX_APP_KEY = "39b7b779dbafa5fe4ae28af495a3c349"
SEARCH_URL = "https://trackapi.nutritionix.com/v2/search/instant"
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
    st.session_state.search_results = []
    st.session_state.selected_food = None

st.title("🥗 Food Tracker (Serving Based)")

# --- SEARCH ---
food_input = st.text_input("Enter a food:")

if food_input:
    r = requests.get(SEARCH_URL, headers=headers, params={"query": food_input})
    if r.status_code == 200:
        results = r.json().get("common", [])[:10]
        st.session_state.search_results = [f["food_name"] for f in results]

# --- DROPDOWN FOR CHOICES ---
if st.session_state.search_results:
    choice = st.selectbox(
        "Choose a food:",
        st.session_state.search_results,
        key="food_choice"
    )
    st.session_state.selected_food = choice

# --- GET NUTRIENTS ---
if st.session_state.selected_food:
    data = {"query": st.session_state.selected_food}
    response = requests.post(NUTRITIONIX_URL, headers=headers, json=data)

    if response.status_code == 200:
        food_data = response.json()
        for item in food_data.get("foods", []):
            name = item["food_name"].title()
            calories = item["nf_calories"]
            serving_qty = item["serving_qty"]
            serving_unit = item["serving_unit"]

            # --- DEFINE SERVING ---
            if calories >= 80:
                base_serving = 100   # Energy-dense reference
                serving_type = "Energy-dense"
            else:
                base_serving = 50    # Nutrient-dense reference
                serving_type = "Nutrient-dense"

            # Scale serving so that 1 "serving" matches base_serving calories
            serving_ratio = base_serving / calories
            adjusted_qty = serving_qty * serving_ratio
            adjusted_unit = serving_unit

            st.write(f"**{name}**")
            st.write(
                f"1 {adjusted_qty:.2f} {adjusted_unit} = {base_serving} kcal "
                f"({serving_type} serving)"
            )

            # --- USER CHOICE ---
            chosen_servings = st.selectbox(
                f"How many servings of {name}?",
                [0.25, 0.5, 0.75, 1, 2],
                index=3,  # default to 1
                key=f"{name}_choice"
            )

            if st.button(f"Add {name}", key=f"{name}_add"):
                if serving_type == "Energy-dense":
                    st.session_state.energy_servings += chosen_servings
                else:
                    st.session_state.nutrient_servings += chosen_servings


# --- DISPLAY TALLY ---
def round_quarter(x):
    return round(x * 4) / 4

st.sidebar.header("Today's Totals")
st.sidebar.metric(
    "Energy-dense Servings",
    round_quarter(st.session_state.energy_servings)
)
st.sidebar.metric(
    "Nutrient-dense Servings",
    round_quarter(st.session_state.nutrient_servings)
)
