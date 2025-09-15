import streamlit as st
import requests
import datetime

# --- CONFIG ---
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

NUTRIENT_DENSE_CATEGORIES = [
    "Fruits and Fruit Juices",
    "Vegetables and Vegetable Products",
]

# --- RESET SERVINGS DAILY ---
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.search_results = []
    st.session_state.selected_food = None

st.title("🥗 Food Tracker (USDA Serving Based)")

# --- HELPER: round to nearest 0.25 ---
def round_quarter(x):
    return round(x * 4) / 4

# --- USER SEARCH ---
food_input = st.text_input("Enter a food:")

if food_input and st.button("Search"):
    params = {
        "api_key": FDC_API_KEY,
        "query": food_input,
        "pageSize": 15,
        "dataType": ["Foundation", "SR Legacy"],  # avoid Branded
    }
    r = requests.get(SEARCH_URL, params=params)

    if r.status_code == 200:
        foods = r.json().get("foods", [])
        # only keep foods with category
        filtered = [f for f in foods if f.get("foodCategory")]
        st.session_state.search_results = filtered
        if filtered:
            st.session_state.selected_food = filtered[0]

# --- FOOD PICKER ---
if st.session_state.search_results:
    food_names = [
        f"{f['description']} ({f['foodCategory']})"
        for f in st.session_state.search_results
    ]
    choice = st.selectbox(
        "Select a food:",
        food_names,
        index=0,
        key="food_choice",
    )
    st.session_state.selected_food = st.session_state.search_results[
        food_names.index(choice)
    ]

# --- DISPLAY + SERVING LOGIC ---
if st.session_state.selected_food:
    chosen = st.session_state.selected_food
    desc = chosen["description"].title()
    cat = chosen.get("foodCategory", "Unknown")

    st.write(f"### {desc}")
    st.write(f"**Category:** {cat}")

    # --- CLASSIFY SERVING ---
    if cat in NUTRIENT_DENSE_CATEGORIES:
        base_serving = 50
        serving_type = "Nutrient-dense"
        lower, upper = 40, 60
    else:
        base_serving = 100
        serving_type = "Energy-dense"
        lower, upper = 80, 120

    # --- Calories (if available) ---
    nutrients = {
        n["nutrientName"].lower(): n["value"]
        for n in chosen.get("foodNutrients", [])
    }
    kcal = nutrients.get("energy", None)

    if kcal:
        st.write(f"USDA reports ~{kcal:.0f} kcal per 100 g")
        factor = base_serving / kcal if kcal > 0 else 1
        adjusted_qty = round_quarter(100 * factor)
        st.write(
            f"👉 Defined 1 {serving_type} serving ≈ {adjusted_qty} g "
            f"({lower}-{upper} kcal target)"
        )
    else:
        adjusted_qty = base_serving
        st.write(f"No calorie data — using default {base_serving} g")

    # --- USER INPUT ---
    chosen_servings = st.selectbox(
        f"How many servings of {desc}?",
        [0.25, 0.5, 0.75, 1, 2],
        index=3,
        key=f"{desc}_choice",
    )
    actual_qty = round_quarter(adjusted_qty * chosen_servings)
    st.write(f"→ {chosen_servings} serving(s) = {actual_qty} g")

    if st.button(f"Add {desc}", key=f"{desc}_add"):
        if serving_type == "Energy-dense":
            st.session_state.energy_servings += chosen_servings
        else:
            st.session_state.nutrient_servings += chosen_servings

# --- DAILY TOTALS ---
st.sidebar.header("Today's Totals")
st.sidebar.metric(
    "Energy-dense Servings", round(st.session_state.energy_servings * 4) / 4
)
st.sidebar.metric(
    "Nutrient-dense Servings", round(st.session_state.nutrient_servings * 4) / 4
)
