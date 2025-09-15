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

st.title("🥗 Food Tracker (Serving Based)")

# --- SEARCH BOX ---
food_input = st.text_input("Enter a food:")

if food_input:
    r = requests.get(SEARCH_URL, headers=headers, params={"query": food_input})
    if r.status_code == 200:
        results = r.json().get("common", [])[:10]
        options = [f["food_name"] for f in results]
        if options:
            choice = st.selectbox("Select a food:", options)
            if st.button("Get Nutrition"):
                data = {"query": choice}
                response = requests.post(NUTRITIONIX_URL, headers=headers, json=data)
                if response.status_code == 200:
                    food_data = response.json()
                    for item in food_data.get("foods", []):
                        name = item["food_name"].title()
                        calories = item["nf_calories"]
                        serving_qty = item["serving_qty"]
                        serving_unit = item["serving_unit"]

                        # --- Get food group safely ---
                        food_group = ""
                        tags = item.get("tags", {})
                        if tags and "food_group" in tags and tags["food_group"]:
                            food_group = str(tags["food_group"]).lower()

                        # --- Determine serving type ---
                        if "fruit" in food_group or "vegetable" in food_group:
                            base_serving = 50   # nutrient-dense
                            serving_type = "Nutrient-dense"
                        else:
                            base_serving = 100  # energy-dense
                            serving_type = "Energy-dense"

                        # --- Scale unit size to match base serving ---
                        unit_calories = calories / serving_qty
                        target_qty = base_serving / unit_calories
                        # round to nearest 0.25
                        target_qty = round(target_qty * 4) / 4

                        st.write(f"**{name}**")
                        st.write(
                            f"≈ {target_qty} {serving_unit} "
                            f"= ~{base_serving} kcal ({serving_type})"
                        )

                        # --- Serving selection ---
                        servings_choice = st.selectbox(
                            f"How many servings of {name}?",
                            [0.25, 0.5, 0.75, 1, 2, 3],
                            index=3,
                            key=f"{name}_choice"
                        )

                        if st.button(f"Add {name}", key=f"add_{name}"):
                            if serving_type == "Energy-dense":
                                st.session_state.energy_servings += servings_choice
                            else:
                                st.session_state.nutrient_servings += servings_choice

# --- MANUAL ENTRY ---
st.sidebar.subheader("➕ Add Servings Manually")
manual_type = st.sidebar.selectbox(
    "Serving type:",
    ["Nutrient-dense", "Energy-dense"]
)
manual_qty = st.sidebar.selectbox(
    "How many servings?",
    [0.25, 0.5, 0.75, 1, 2, 3, 4],
    index=3
)
if st.sidebar.button("Add Manual Serving"):
    if manual_type == "Energy-dense":
        st.session_state.energy_servings += manual_qty
    else:
        st.session_state.nutrient_servings += manual_qty

# --- DISPLAY TALLY ---
st.sidebar.header("📊 Today's Totals")
st.sidebar.metric("Energy-dense Servings", round(st.session_state.energy_servings, 2))
st.sidebar.metric("Nutrient-dense Servings", round(st.session_state.nutrient_servings, 2))
