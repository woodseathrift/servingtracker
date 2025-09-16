import streamlit as st
import requests
import datetime
import pandas as pd

# -------------------------------
# Load FNDDS At A Glance files
# -------------------------------
FOODS_FILE = "2017-2018 FNDDS At A Glance - Foods and Beverages.csv"
PORTIONS_FILE = "2017-2018 FNDDS At A Glance - Portions and Weights.csv"
NUTRIENTS_FILE = "2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv"

# Foods
foods_df = pd.read_csv(FOODS_FILE, skiprows=1)
foods_df.columns = foods_df.columns.str.strip().str.lower()

# Portions
portions_df = pd.read_csv(PORTIONS_FILE, skiprows=1)
portions_df.columns = portions_df.columns.str.strip().str.lower()

# Nutrients (not fully used yet, but available)
nutrients_df = pd.read_csv(NUTRIENTS_FILE, skiprows=1)
nutrients_df.columns = nutrients_df.columns.str.strip().str.lower()

# Lookup dicts
foodcode_to_desc = dict(zip(foods_df["food code"], foods_df["main food description"]))

# -------------------------------
# USDA API
# -------------------------------
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# -------------------------------
# Session State (daily reset)
# -------------------------------
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.search_results = []
    st.session_state.selected_food = None

# -------------------------------
# UI
# -------------------------------
st.title("🥗 Food Tracker (USDA + FNDDS)")

query = st.text_input("Enter a food:")

# -------------------------------
# Search USDA
# -------------------------------
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
        st.session_state.search_results = foods
        if foods:
            st.session_state.selected_food = foods[0]
    else:
        st.error(f"USDA API error: {r.status_code}")

# -------------------------------
# Picker
# -------------------------------
if st.session_state.search_results:
    labels = [
        f"{f['description']} ({f.get('foodCategory','Unknown')})"
        for f in st.session_state.search_results
    ]
    choice = st.selectbox(
        "Pick a food:", labels, index=0, key="choice_box"
    )
    st.session_state.selected_food = st.session_state.search_results[labels.index(choice)]

# -------------------------------
# Details
# -------------------------------
if st.session_state.selected_food:
    food = st.session_state.selected_food
    desc = food.get("description", "Unknown").title()
    cat = food.get("foodCategory", "Unknown")

    st.subheader(desc)
    st.write(f"Category: {cat}")

    # USDA kcal/100g
    kcal = None
    for n in food.get("foodNutrients", []):
        if isinstance(n, dict):
            name = n.get("nutrientName") or n.get("nutrient", {}).get("name", "")
            if name and "energy" in name.lower() and "kj" not in name.lower():
                kcal = n.get("value")
                break
    if kcal:
        st.write(f"USDA: ~{kcal:.0f} kcal per 100 g")

    # Try to match FNDDS food code
    foodcode = food.get("foodCode")
    portion_choices = []
    if foodcode and int(foodcode) in portions_df["food code"].values:
        p = portions_df[portions_df["food code"] == int(foodcode)]
        portion_choices = [
            f"{row['portion description']} ({row['portion weight (g)']} g)"
            for _, row in p.iterrows()
            if row["portion weight (g)"] > 0
        ]

    # Portion picker
    if portion_choices:
        portion_choice = st.selectbox("Choose a portion size:", portion_choices)
    else:
        st.info("No FNDDS portion equivalents found — defaulting to 100 g.")
        portion_choice = "100 g"

    # How many servings
    servings = st.selectbox(
        "How many servings?", [0.25,0.5,0.75,1,2], index=3, key=f"{desc}_servings"
    )
    st.write(f"= {servings} × {portion_choice}")

    if st.button(f"Add {desc}", key=f"add_{desc}"):
        if "vegetable" in cat.lower() or "fruit" in cat.lower():
            st.session_state.nutrient_servings += servings
        else:
            st.session_state.energy_servings += servings

# -------------------------------
# Totals
# -------------------------------
st.sidebar.header("Today's totals")
st.sidebar.metric("Energy-dense servings",
    round(st.session_state.energy_servings*4)/4)
st.sidebar.metric("Nutrient-dense servings",
    round(st.session_state.nutrient_servings*4)/4)

