import streamlit as st
import requests
import datetime
import math

# --- API SETUP ---
NUTRITIONIX_APP_ID = "5107911f"
NUTRITIONIX_APP_KEY = "39b7b779dbafa5fe4ae28af495a3c349"
SEARCH_URL = "https://trackapi.nutritionix.com/v2/search/instant"
NUTRITIONIX_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

headers = {
    "x-app-id": NUTRITIONIX_APP_ID,
    "x-app-key": NUTRITIONIX_APP_KEY,
    "Content-Type": "application/json",
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

# --- HELPER: round to nearest 0.25 ---
def round_quarter(x):
    return round(x * 4) / 4

# --- USER SEARCH ---
food_input = st.text_input("Enter a food:")

if food_input:
    r = requests.get(SEARCH_URL, headers=headers, params={"query": food_input})
    if r.status_code == 200:
        results = r.json().get("common", [])[:10]
        st.session_state.search_results = [f["food_name"] for f in results]
        if st.session_state.search_results:
            st.session_state.selected_food = st.session_state.search_results[0]

if st.session_state.search_results:
    choice = st.selectbox(
        "Select a food:",
        st.session_state.search_results,
        index=0,
        key="food_choice",
    )
    st.session_state.selected_food = choice

# --- FETCH NUTRITION INFO ---
if st.session_state.selected_food:
    data = {"query": st.session_state.selected_food}
    response = requests.post(NUTRITIONIX_URL, headers=headers, json=data)
    if response.status_code == 200:
        food_data = response.json()
        for item in food_data.get("foods", []):
            name = item["food_name"].title()
            calories = item["nf_calories"]
            qty = item["serving_qty"]
            unit = item["serving_unit"]

            st.write(f"### {name}")
            st.write(f"Nutritionix says: {qty} {unit} = {calories:.0f} kcal")

            # --- CLASSIFY SERVING ---
            tags = item.get("tags", {})
            food_group = tags.get("food_group") or ""
            name_lower = name.lower()

            if (
                "fruit" in food_group
                or "vegetable" in food_group
                or "fruit" in name_lower
                or "vegetable" in name_lower
            ):
                base_serving = 50
                serving_type = "Nutrient-dense"
                lower, upper = 40, 60
            else:
                if calories >= 80:
                    base_serving = 100
                    serving_type = "Energy-dense"
                    lower, upper = 80, 120
                else:
                    base_serving = 50
                    serving_type = "Nutrient-dense"
                    lower, upper = 40, 60

            # --- ADJUST SERVING SIZE TO SIMPLE VOLUME ---
            factor = 100 / calories if serving_type == "Energy-dense" else 50 / calories
            adjusted_qty = qty * factor
            adjusted_qty = round_quarter(adjusted_qty)  # force 0.25 increments

            st.write(
                f"👉 Defined 1 {serving_type} serving ≈ {adjusted_qty} {unit} "
                f"({lower}-{upper} kcal target)"
            )

            # --- USER CHOICE ---
            chosen_servings = st.selectbox(
                f"How many servings of {name}?",
                [0.25, 0.5, 0.75, 1, 2],
                index=3,  # default to 1
                key=f"{name}_choice",
            )

            actual_qty = round_quarter(adjusted_qty * chosen_servings)
            st.write(f"→ {chosen_servings} serving(s) = {actual_qty} {unit}")

            if st.button(f"Add {name}", key=f"{name}_add"):
                if serving_type == "Energy-dense":
                    st.session_state.energy_servings += chosen_servings
                else:
                    st.session_state.nutrient_servings += chosen_servings

# --- DISPLAY TALLY ---
st.sidebar.header("Today's Totals")
st.sidebar.metric(
    "Energy-dense Servings", round(st.session_state.energy_servings, 2)
)
st.sidebar.metric(
    "Nutrient-dense Servings", round(st.session_state.nutrient_servings, 2)
)
