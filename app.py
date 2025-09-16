import streamlit as st
import pandas as pd
import datetime

# ------------------- Load Food Data -------------------
@st.cache_data
def load_data():
    foods_df = pd.read_csv("2017-2018 FNDDS At A Glance - Foods and Beverages.csv", skiprows=1)
    nutrients_df = pd.read_csv("2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv", skiprows=1)
    portions_df = pd.read_csv("2017-2018 FNDDS At A Glance - Portions and Weights.csv", skiprows=1)
    return df

foods_df, nutrients_df, portions_df = load_data()

# ------------------- Initialize State -------------------
if "energy_servings" not in st.session_state:
    st.session_state.energy_servings = 0.0
if "nutrient_servings" not in st.session_state:
    st.session_state.nutrient_servings = 0.0
if "date" not in st.session_state:
    st.session_state.date = datetime.date.today()

# reset daily
if st.session_state.date != datetime.date.today():
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.date = datetime.date.today()

# ------------------- Serving Picker -------------------
COMMON_UNITS = [
    "cup", "cups", "tbsp", "tablespoon", "tablespoons",
    "tsp", "teaspoon", "teaspoons", "slice", "slices",
    "piece", "pieces", "package", "can", "bottle", "link",
    "patty", "bar", "cookie", "egg", "container", "loaf",
    "bun", "muffin", "cake", "donut", "taco", "sandwich",
    "small", "medium", "large"
]

def pick_fractional_serving(food_row, target_cal):
    # Filter common unit portions
    portions = []
    for _, row in foods[foods["food_code"] == food_row["food_code"]].iterrows():
        desc = str(row["portion_description"]).lower()
        if any(u in desc for u in COMMON_UNITS):
            portions.append(row)
    if not portions:
        # fallback to grams
        kcal_per_g = food_row["kcal"] / food_row["gram_weight"]
        grams = round(target_cal / kcal_per_g)
        return f"{grams} g (~{target_cal} kcal)"

    # pick first common unit portion
    base = portions[0]
    kcal_per_portion = base["kcal"]
    desc = base["portion_description"]

    # compute fraction of this unit needed
    fraction = target_cal / kcal_per_portion
    fraction = round(fraction * 4) / 4  # nearest 0.25

    approx_cal = round(fraction * kcal_per_portion)
    return f"{fraction} {desc} (~{approx_cal} kcal)"

def serving_for_food(food_row):
    code = str(food_row["food_code"])
    if code.startswith(("61", "63", "67", "72", "73", "74", "75", "76", "78")):
        return "Nutrient-dense", pick_fractional_serving(food_row, 50)
    else:
        return "Energy-dense", pick_fractional_serving(food_row, 100)

# ------------------- Add Servings -------------------
def add_serving(density_type, amount=1.0):
    if density_type == "Energy-dense":
        st.session_state.energy_servings += amount
    else:
        st.session_state.nutrient_servings += amount
    st.rerun()  # force UI update

# ------------------- UI -------------------
st.title("🥗 Serving Tracker")

query = st.text_input("Search food")
if query:
    matches = foods[foods["main_food_description"].str.contains(query, case=False, na=False)]
    if not matches.empty:
        choice = st.selectbox(
            "Select a food",
            [f'{row["main_food_description"]} (#{row["food_code"]})'
             for _, row in matches.iterrows()]
        )
        if choice:
            code = int(choice.split("#")[-1].strip())
            food_row = foods[foods["food_code"] == code].iloc[0]
            density, serving_text = serving_for_food(food_row)

            color = "#FFCCCC" if density == "Energy-dense" else "#CCFFCC"
            st.markdown(
                f"<div style='background-color:{color}; padding:8px; border-radius:8px;'>"
                f"<b>{density}</b>: {serving_text}</div>",
                unsafe_allow_html=True,
            )

            amt = st.selectbox("Add servings", [0.25, 0.5, 0.75, 1.0], key="amt")
            if st.button("Add to tally"):
                add_serving(density, amt)

# Manual tally section
st.subheader("Quick Add")
col1, col2 = st.columns(2)
with col1:
    amt = st.selectbox("Energy increment", [0.25, 0.5, 0.75, 1.0], key="energy_inc")
    if st.button("Add Energy"):
        add_serving("Energy-dense", amt)
with col2:
    amt = st.selectbox("Nutrient increment", [0.25, 0.5, 0.75, 1.0], key="nutrient_inc")
    if st.button("Add Nutrient"):
        add_serving("Nutrient-dense", amt)

# Show tally
st.subheader("Tally")
col1, col2 = st.columns(2)
with col1:
    st.markdown(
        f"<div style='background-color:#FF6666; color:black; padding:10px; border-radius:8px;'>"
        f"Energy-dense: <b>{st.session_state.energy_servings:.2f}</b></div>",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"<div style='background-color:#66FF66; color:black; padding:10px; border-radius:8px;'>"
        f"Nutrient-dense: <b>{st.session_state.nutrient_servings:.2f}</b></div>",
        unsafe_allow_html=True,
    )
