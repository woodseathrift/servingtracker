import streamlit as st
import pandas as pd
import datetime

# --- FILES (adjust names if different) ---
FOODS_FILE = "2017-2018 FNDDS At A Glance - Foods and Beverages.csv"
NUTRIENTS_FILE = "2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv"
PORTIONS_FILE = "2017-2018 FNDDS At A Glance - Portions and Weights.csv"

# --- HELPER: load with auto-skip ---
def load_fndds_file(path):
    # Read first 5 rows to detect header
    preview = pd.read_csv(path, nrows=5)
    if "Food code" in preview.columns:
        df = pd.read_csv(path)
    else:
        df = pd.read_csv(path, skiprows=1)
        if "Food code" not in df.columns:
            df = pd.read_csv(path, skiprows=2)
    df.columns = df.columns.str.strip()
    return df

# --- LOAD FILES ---
foods_df = load_fndds_file(FOODS_FILE)
nutrients_df = load_fndds_file(NUTRIENTS_FILE)
portions_df = load_fndds_file(PORTIONS_FILE)

# Normalize columns (lowercase + underscores)
foods_df.columns = foods_df.columns.str.lower().str.replace(" ", "_")
nutrients_df.columns = nutrients_df.columns.str.lower().str.replace(" ", "_")
portions_df.columns = portions_df.columns.str.lower().str.replace(" ", "_")

# --- BUILD LOOKUPS ---
foodcode_to_desc = dict(zip(foods_df["food_code"], foods_df["main_food_description"]))

# --- SESSION RESET DAILY ---
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.selected_food = None

st.title("🥗 Food Tracker (FNDDS 2017–2018)")

# --- SEARCH ---
query = st.text_input("Search for a food:")

if query:
    matches = foods_df[foods_df["main_food_description"].str.contains(query, case=False, na=False)]
    if not matches.empty:
        options = [f"{row.food_code} – {row.main_food_description}" for row in matches.itertuples()]
        choice = st.selectbox("Pick a food:", options)
        chosen_code = int(choice.split("–")[0].strip())
        st.session_state.selected_food = chosen_code
    else:
        st.warning("No matches found.")

# --- DETAILS ---
if st.session_state.selected_food:
    code = st.session_state.selected_food
    desc = foodcode_to_desc.get(code, "Unknown food")
    st.subheader(desc)

    # Nutrients (just kcal for now)
    kcal_row = nutrients_df[(nutrients_df["food_code"] == code) & (nutrients_df["nutrient_name"].str.contains("Energy", case=False))]
    kcal = kcal_row["nutrient_value"].values[0] if not kcal_row.empty else None
    if kcal:
        st.write(f"~{kcal:.0f} kcal per 100 g")

    # Portions
    portions = portions_df[portions_df["food_code"] == code]
    if not portions.empty:
        portion_choices = [
            f"{row.portion_description} ({row.portion_weight_g:.1f} g)"
            for row in portions.itertuples()
            if row.portion_weight_g > 0
        ]
        choice = st.selectbox("Choose a portion size:", portion_choices)
        servings = st.selectbox("How many servings?", [0.25,0.5,0.75,1,2], index=3)
        st.write(f"= {servings} × {choice}")
        if st.button(f"Add {desc}"):
            st.session_state.energy_servings += servings
    else:
        st.info("No portion equivalents found — defaulting to 100 g.")

# --- TOTALS ---
st.sidebar.header("Today's totals")
st.sidebar.metric("Energy-dense servings", round(st.session_state.energy_servings*4)/4)
st.sidebar.metric("Nutrient-dense servings", round(st.session_state.nutrient_servings*4)/4)
