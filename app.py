import streamlit as st
import requests
import datetime

# --- API SETUP ---
NUTRITIONIX_APP_ID = "5107911f"
NUTRITIONIX_APP_KEY = "39b7b779dbafa5fe4ae28af495a3c349"
NUTRITIONIX_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"
SEARCH_URL = "https://trackapi.nutritionix.com/v2/search/instant"

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
    st.session_state.selected_food_name = None
    st.session_state.selected_item = None

st.title("🥗 Food Tracker (Serving Based)")

# -----------------------
# SEARCH UI
# -----------------------
st.subheader("Search Nutritionix Foods")
search_text = st.text_input("Type a food name (e.g. 'cheerios', 'banana')")

if st.button("Search") and search_text:
    r = requests.get(SEARCH_URL, headers=headers, params={"query": search_text})
    if r.status_code != 200:
        st.error("Search failed. Check API key or rate limits.")
        st.session_state.search_results = []
    else:
        data = r.json()
        common = data.get("common", []) or []
        branded = data.get("branded", []) or []
        options = []

        for c in common:
            name = c.get("food_name")
            if name and name not in options:
                options.append(name)
            if len(options) >= 10:
                break
        for b in branded:
            name = b.get("food_name")
            if name and name not in options:
                options.append(name)
            if len(options) >= 10:
                break

        st.session_state.search_results = options
        st.session_state.selected_food_name = options[0] if options else None
        st.session_state.selected_item = None

if st.session_state.get("search_results"):
    sel = st.selectbox(
        "Pick a result",
        st.session_state.search_results,
        index=0,
        key="food_picker"
    )
    st.session_state.selected_food_name = sel

    if st.button("Load nutrition"):
        payload = {"query": st.session_state.selected_food_name}
        r2 = requests.post(NUTRITIONIX_URL, headers=headers, json=payload)
        if r2.status_code == 200:
            results = r2.json().get("foods", [])
            if results:
                st.session_state.selected_item = results[0]
            else:
                st.warning("No nutrition info found for that food.")
        else:
            st.error("Nutrition lookup failed.")

# -----------------------
# SERVING CALCULATOR
# -----------------------
def round_to_quarter(x: float) -> float:
    return round(x * 4) / 4.0

if st.session_state.get("selected_item"):
    item = st.session_state.selected_item
    name = item.get("food_name", "Unknown").title()
    calories = item.get("nf_calories", 0)
    qty = item.get("serving_qty", 1)
    unit = item.get("serving_unit", "unit")

    st.markdown(f"**{name}**")
    st.write(f"Nutritionix: {qty} {unit} = {calories:.0f} kcal")

    # classify food safely
    tags = item.get("tags", {})
    if isinstance(tags, dict):
        food_group = (tags.get("food_group") or "").lower()
    else:
        food_group = ""
    is_fruitveg = any(x in food_group for x in ["fruit", "vegetable", "veg"])

    if is_fruitveg:
        base_serving = 50
        serving_type = "Nutrient-dense"
    else:
        base_serving = 100
        serving_type = "Energy-dense"

    if calories > 0 and qty > 0:
        ratio = base_serving / calories
        adj_qty = round_to_quarter(qty * ratio)
        adj_calories = calories * (adj_qty / qty)

        st.write(f"**1 serving = {adj_qty} {unit} (~{adj_calories:.0f} kcal)** [{serving_type}]")

        with st.form(key=f"{name}_form"):
            choice = st.selectbox(
                f"How many servings of {name}?",
                [0.25, 0.5, 0.75, 1, 1.5, 2],
                index=3
            )
            submitted = st.form_submit_button("Add")
            if submitted:
                if serving_type == "Energy-dense":
                    st.session_state.energy_servings += choice
                else:
                    st.session_state.nutrient_servings += choice
                st.success(f"Added {choice} {serving_type} serving(s) of {name}!")

# -----------------------
# MANUAL ENTRY
# -----------------------
st.subheader("Manual Add")
with st.form("manual_add"):
    serving_type = st.selectbox("Serving type", ["Energy-dense", "Nutrient-dense"])
    amount = st.selectbox("How many?", [0.25, 0.5, 0.75, 1, 1.5, 2], index=3)
    submitted = st.form_submit_button("Add Manual")
    if submitted:
        if serving_type == "Energy-dense":
            st.session_state.energy_servings += amount
        else:
            st.session_state.nutrient_servings += amount
        st.success(f"Added {amount} {serving_type} serving(s) manually!")

# -----------------------
# DISPLAY TALLY
# -----------------------
st.sidebar.header("Today's Totals")
st.sidebar.metric("Energy-dense Servings", round(st.session_state.energy_servings, 2))
st.sidebar.metric("Nutrient-dense Servings", round(st.session_state.nutrient_servings, 2))
