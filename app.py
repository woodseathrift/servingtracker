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

def round_quarter(x):
    return round(x * 4) / 4

# --- LOAD FNDDS WITH COLUMN NORMALIZATION ---
@st.cache_data
def load_fndds():
    foods = pd.read_csv("2017-2018 FNDDS At A Glance - Foods and Beverages.csv")
    nutrients = pd.read_csv("2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv")
    portions = pd.read_csv("2017-2018 FNDDS At A Glance - Portions and Weights.csv")

    # normalize column names
    foods.columns = foods.columns.str.strip().str.lower()
    nutrients.columns = nutrients.columns.str.strip().str.lower()
    portions.columns = portions.columns.str.strip().str.lower()
    return foods, nutrients, portions

foods, nutrients, portions = load_fndds()

# --- USER SEARCH ---
query = st.text_input("Search for a food (e.g. 'apple', 'pizza')")

if query:
    # check actual colnames
    st.write("DEBUG: Foods file columns →", foods.columns.tolist())

    if "main food description" in foods.columns:
        results = foods[foods["main food description"].str.contains(query, case=False, na=False)]
    else:
        st.error("❌ Could not find 'main food description' column. Check CSV headers.")
        results = pd.DataFrame()

    if not results.empty:
        food_choice = st.selectbox(
            "Select a food:",
            results["main food description"].tolist(),
            key="food_choice",
        )
