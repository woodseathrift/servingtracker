import streamlit as st
import pandas as pd
import datetime
import re

# ------------------- Load Food Data -------------------
@st.cache_data
def load_data():
    foods_df = pd.read_csv("2017-2018 FNDDS At A Glance - Foods and Beverages.csv", skiprows=1)
    nutrients_df = pd.read_csv("2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv", skiprows=1)
    portions_df = pd.read_csv("2017-2018 FNDDS At A Glance - Portions and Weights.csv", skiprows=1)

    # Normalize column names
    for df in [foods_df, nutrients_df, portions_df]:
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(r"[()]", "", regex=True)
        )

    return foods_df, nutrients_df, portions_df


# Unpack correctly
foods_df, nutrients_df, portions_df = load_data()

# ------------------- Initialize State -------------------
if "energy_servings" not in st.session_state:
    st.session_state.energy_servings = 0.0
if "nutrient_servings" not in st.session_state:
    st.session_state.nutrient_servings = 0.0
if "date" not in st.session_state:
    st.session_state.date = datetime.date.today()
if "selected_foods" not in st.session_state:
    st.session_state.selected_foods = []
if "clear_search" not in st.session_state:
    st.session_state.clear_search = False
if "food_search" not in st.session_state:
    st.session_state.food_search = ""
if "food_choice" not in st.session_state:
    st.session_state.food_choice = "-- choose a food --"
if "amt_choice" not in st.session_state:
    st.session_state.amt_choice = 1

# reset daily
if st.session_state.date != datetime.date.today():
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.date = datetime.date.today()
    st.session_state.selected_foods = []

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
    kcal_row = nutrients_df[nutrients_df["food_code"] == food_row["food_code"]]
    if kcal_row.empty:
        return "No kcal data", 0, 0, "g"
    kcal_per_100g = kcal_row.iloc[0]["energy_kcal"]
    kcal_per_g = kcal_per_100g / 100

    portion_rows = portions_df[portions_df["food_code"] == food_row["food_code"]]
    usable_portions = []
    for _, row in portion_rows.iterrows():
        desc = str(row["portion_description"]).lower()
        if any(u in desc for u in COMMON_UNITS):
            usable_portions.append(row)

    if not usable_portions:
        grams = round(target_cal / kcal_per_g)
        return f"{grams} g (~{target_cal} kcal)", grams, target_cal, "g"

    chosen = None
    for _, row in pd.DataFrame(usable_portions).iterrows():
        grams = row["portion_weight_g"]
        kcal_per_portion = grams * kcal_per_g
        fraction = target_cal / kcal_per_portion
        fraction = round(fraction * 4) / 4
        if fraction >= 0.25:
            chosen = (row, fraction, kcal_per_portion, grams)
            break

    if not chosen:
        grams = round(target_cal / kcal_per_g)
        return f"{grams} g (~{target_cal} kcal)", grams, target_cal, "g"

    base, fraction, kcal_per_portion, grams = chosen
    desc = str(base["portion_description"]).lower()
    if desc.startswith("1 "):
        desc = desc[2:]
    elif desc.startswith("one "):
        desc = desc[4:]

    approx_cal = round(fraction * kcal_per_portion)
    total_grams = round(fraction * grams)

    return f"{fraction} {desc} (≈{total_grams} g, ~{approx_cal} kcal)", total_grams, approx_cal, desc


def serving_for_food(food_row):
    code = str(food_row["food_code"])
    if code.startswith(("61", "63", "67", "72", "73", "74", "75", "76", "78")):
        density = "Nutrient-dense"
        serving_text, grams, kcal, desc = pick_fractional_serving(food_row, 50)
    else:
        density = "Energy-dense"
        serving_text, grams, kcal, desc = pick_fractional_serving(food_row, 100)
    return density, serving_text, grams, kcal, desc

# ------------------- Add Servings -------------------
def add_serving(density_type, amount=1.0):
    if density_type == "Energy-dense":
        st.session_state.energy_servings += amount
    else:
        st.session_state.nutrient_servings += amount

# ------------------- UI -------------------
st.title("🥗 Serving Tracker")

# --- Search box with button ---
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("Search for a food", value="", key="food_search")
with col2:
    search_clicked = st.button("🔍 Search")

if query or search_clicked:
    q = query.strip().lower()
    tokens = re.findall(r'\S+', q)

    desc_series = foods_df['main_food_description'].fillna('').str.lower()
    mask = desc_series.apply(lambda s: all(tok in s for tok in tokens))
    matches = foods_df[mask]

    if not matches.empty:
        options = ["-- choose a food --"] + [
            f'{row["main_food_description"]} (#{row["food_code"]})'
            for _, row in matches.iterrows()
        ]

        choice = st.selectbox("Select a food", options, key="food_choice")

        if choice != "-- choose a food --":
            code = int(choice.split("#")[-1].strip(")"))
            food_row = foods_df[foods_df["food_code"] == code].iloc[0]

            density, serving_text, base_grams, base_kcal, unit_desc = serving_for_food(food_row)
            color = "#330000" if density == "Energy-dense" else "#003300"

            amt = st.selectbox(
                "Add servings",
                [0.25, 0.5, 0.75, 1, 2],
                index=3,
                key="amt_choice"
            )

            total_grams = round(base_grams * amt)
            total_kcal = round(base_kcal * amt)

            # Display string cleaned up
            if unit_desc == "g":
                display_serving = f"{total_grams} g (~{total_kcal} kcal)"
            else:
                display_serving = f"{amt} {unit_desc} (≈{total_grams} g, ~{total_kcal} kcal)"

            st.markdown(
                f"<div style='background-color:{color}; padding:8px; border-radius:8px;'>"
                f"<b>{food_row['main_food_description']}</b><br>{density}: {display_serving}</div>",
                unsafe_allow_html=True,
            )

            if st.button("Add to tally"):
                add_serving(density, amt)
                st.session_state.selected_foods.append({
                    "code": code,
                    "name": food_row["main_food_description"],
                    "density": density,
                    "amt": amt,
                })

                for k in ["food_search", "food_choice", "amt_choice"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

# ------------------- Manual tally section -------------------
st.subheader("Quick Add")
col1, col2 = st.columns(2)
with col1:
    amt = st.selectbox("Serving increment", [0.25, 0.5, 0.75, 1, 2], index=3, key="energy_inc")
    if st.button("⚡ Add Energy ⚡"):
        add_serving("Energy-dense", amt)
with col2:
    amt = st.selectbox("Serving increment", [0.25, 0.5, 0.75, 1, 2], index=3, key="nutrient_inc")
    if st.button("🌱 Add Nutrient 🌱"):
        add_serving("Nutrient-dense", amt)

# ------------------- Show tally -------------------
st.subheader("Tally")
col1, col2 = st.columns(2)
with col1:
    st.markdown(
        f"<div style='background-color:#FF6666; color:black; padding:10px; border-radius:8px;'>"
        f"⚡ Energy-dense servings: <b>{st.session_state.energy_servings:.2f}</b></div>",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"<div style='background-color:#66FF66; color:black; padding:10px; border-radius:8px;'>"
        f"🌱 Nutrient-dense servings: <b>{st.session_state.nutrient_servings:.2f}</b></div>",
        unsafe_allow_html=True,
    )
