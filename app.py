import streamlit as st
import pandas as pd
import datetime

# --- RESET SERVINGS DAILY ---
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.selected_food = None

st.title("🥗 FNDDS Food Tracker (2017–2018)")

# --- HELPER: round to nearest 0.25 ---
def round_quarter(x):
    return round(x * 4) / 4

# --- LOAD FNDDS ---
@st.cache_data
def load_fndds():
    foods = pd.read_csv("2017-2018 FNDDS At A Glance - Foods and Beverages.csv")
    nutrients = pd.read_csv("2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv")
    portions = pd.read_csv("2017-2018 FNDDS At A Glance - Portions and Weights.csv")
    return foods, nutrients, portions

foods, nutrients, portions = load_fndds()

# --- USER SEARCH ---
query = st.text_input("Search for a food (e.g. 'apple', 'pizza')")

if query:
    results = foods[foods["Main food description"].str.contains(query, case=False, na=False)]
    if results.empty:
        st.warning("No foods found.")
    else:
        food_choice = st.selectbox(
            "Select a food:",
            results["Main food description"].tolist(),
            key="food_choice",
        )

        if food_choice:
            chosen = results[results["Main food description"] == food_choice].iloc[0]
            food_code = chosen["Food code"]
            st.write(f"**Selected Food:** {food_choice}")
            st.write(f"**Category:** {chosen['WWEIA Category description']}")

            # --- Calories per 100g ---
            nut = nutrients[nutrients["Food code"] == food_code]
            if "Energy (kcal)" in nut.columns:
                kcal_per100g = nut["Energy (kcal)"].values[0]
            else:
                st.error("Energy (kcal) column not found in nutrient file.")
                kcal_per100g = None

            # --- Portion options ---
            portion_rows = portions[portions["Food code"] == food_code]
            if not portion_rows.empty and kcal_per100g:
                portion_options = {
                    row["Portion description"]: row["Portion weight"] for _, row in portion_rows.iterrows()
                }

                portion_choice = st.selectbox(
                    "Choose a portion:",
                    list(portion_options.keys()),
                    key="portion_choice",
                )

                grams = portion_options[portion_choice]
                calories = grams * (kcal_per100g / 100)

                st.write(f"📏 {portion_choice} = {grams:.0f} g ≈ {calories:.0f} kcal")

                # --- Classify serving ---
                category = chosen["WWEIA Category description"].lower()
                if "fruit" in category or "vegetable" in category:
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

                factor = base_serving / calories if calories > 0 else 1
                adjusted_qty = round_quarter(factor)

                st.write(
                    f"👉 Defined 1 {serving_type} serving ≈ {adjusted_qty} × {portion_choice} "
                    f"({lower}-{upper} kcal target)"
                )

                chosen_servings = st.selectbox(
                    f"How many servings of {food_choice}?",
                    [0.25, 0.5, 0.75, 1, 2],
                    index=3,
                    key=f"{food_choice}_choice",
                )

                if st.button(f"Add {food_choice}", key=f"{food_choice}_add"):
                    if serving_type == "Energy-dense":
                        st.session_state.energy_servings += chosen_servings
                    else:
                        st.session_state.nutrient_servings += chosen_servings

# --- DISPLAY TALLY ---
st.sidebar.header("Today's Totals")
st.sidebar.metric(
    "Energy-dense Servings", round_quarter(st.session_state.energy_servings)
)
st.sidebar.metric(
    "Nutrient-dense Servings", round_quarter(st.session_state.nutrient_servings)
)
