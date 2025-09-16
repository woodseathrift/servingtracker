import streamlit as st
import requests
import datetime
import pandas as pd
from difflib import get_close_matches

# --- CONFIG ---
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# --- LOAD FNDDS FILES ---
FOODS_FILE = "2017-2018 FNDDS At A Glance - Foods and Beverages.csv"
PORTIONS_FILE = "2017-2018 FNDDS At A Glance - Portions and Weights.csv"

foods_df = pd.read_csv(FOODS_FILE)
portions_df = pd.read_csv(PORTIONS_FILE)

# Make lookup dictionaries
foodcode_to_desc = dict(zip(foods_df["Food code"], foods_df["Main food description"]))
desc_to_foodcode = {v.lower(): k for k, v in foodcode_to_desc.items()}

# Portion lookup: food code → list of portion options
def get_portions(food_code, description):
    """Return portion choices for a given food code or description"""
    # Try direct food code match
    if food_code in portions_df["Food code"].values:
        subset = portions_df[portions_df["Food code"] == food_code]
    else:
        # Fuzzy match by description if foodCode not aligned
        matches = get_close_matches(description.lower(), desc_to_foodcode.keys(), n=1, cutoff=0.6)
        if matches:
            match_code = desc_to_foodcode[matches[0]]
            subset = portions_df[portions_df["Food code"] == match_code]
        else:
            return []

    portions = []
    for _, row in subset.iterrows():
        desc = row["Portion description"]
        grams = row["Portion weight (g)"]
        portions.append(f"{desc} ({grams:.0f} g)")
    return portions


# --- RESET DAILY STATE ---
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.search_results = []
    st.session_state.selected_food = None

st.title("🥗 Food Tracker (USDA + FNDDS)")

# --- HELPERS ---
def round_quarter(x):
    return round(x * 4) / 4

# --- SEARCH ---
query = st.text_input("Enter a food:")

if query and st.button("Search"):
    params = {
        "api_key": FDC_API_KEY,
        "query": query,
        "pageSize": 15,
        "dataType": "Foundation,SR Legacy"
    }
    r = requests.get(SEARCH_URL, params=params)
    if r.ok:
        foods = r.json().get("foods", [])
        filtered = [f for f in foods if f.get("foodCategory")]
        st.session_state.search_results = filtered
        if filtered:
            st.session_state.selected_food = filtered[0]
    else:
        st.error(f"USDA API error: {r.status_code}")

# --- PICKER ---
if st.session_state.search_results:
    labels = [
        f"{f['description']} ({f.get('foodCategory','Unknown')})"
        for f in st.session_state.search_results
    ]
    choice = st.selectbox("Pick a food:", labels, index=0, key="choice_box")
    st.session_state.selected_food = st.session_state.search_results[labels.index(choice)]

# --- DETAILS ---
if st.session_state.selected_food:
    food = st.session_state.selected_food
    desc = food.get("description", "Unknown").title()
    cat = food.get("foodCategory", "Unknown")

    st.subheader(desc)
    st.write(f"Category: {cat}")

    # --- USDA kcal/100g ---
    kcal = None
    for n in food.get("foodNutrients", []):
        if isinstance(n, dict):
            name = n.get("nutrientName") or n.get("nutrient", {}).get("name", "")
            if name and "energy" in name.lower() and "kj" not in name.lower():
                kcal = n.get("value")
                break
    if kcal:
        st.write(f"USDA: ~{kcal:.0f} kcal per 100 g")

    # --- FNDDS portion lookup ---
    food_code = food.get("foodCode")  # sometimes USDA has this
    portions = get_portions(food_code, desc)

    if portions:
        portion_choice = st.selectbox("Choose a portion size:", portions)
    else:
        st.info("No FNDDS portion found — defaulting to 100 g.")
        portion_choice = "100 g"

    # --- Number of servings ---
    servings = st.selectbox(
        "How many servings?", [0.25, 0.5, 0.75, 1, 2], index=3, key=f"{desc}_servings"
    )
    st.write(f"= {servings} × {portion_choice}")

    # --- Totals update ---
    if st.button(f"Add {desc}", key=f"add_{desc}"):
        if "Fruit" in cat or "Vegetable" in cat:
            st.session_state.nutrient_servings += servings
        else:
            st.session_state.energy_servings += servings

# --- SIDEBAR TOTALS ---
st.sidebar.header("Today's totals")
st.sidebar.metric("Energy-dense servings", round(st.session_state.energy_servings * 4) / 4)
st.sidebar.metric("Nutrient-dense servings", round(st.session_state.nutrient_servings * 4) / 4)
