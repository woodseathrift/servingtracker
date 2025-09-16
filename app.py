import streamlit as st
import pandas as pd
import datetime

# --- FILES (put in same folder as app.py) ---
FOODS_FILE = "2017-2018 FNDDS At A Glance - Foods and Beverages.csv"
NUTRIENTS_FILE = "2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv"
PORTIONS_FILE = "2017-2018 FNDDS At A Glance - Portions and Weights.csv"

# --- LOAD DATA ---
@st.cache_data
def load_data():
    foods = pd.read_csv(FOODS_FILE)
    nutrients = pd.read_csv(NUTRIENTS_FILE)
    portions = pd.read_csv(PORTIONS_FILE)

    # Clean column names
    foods.columns = [c.strip() for c in foods.columns]
    nutrients.columns = [c.strip() for c in nutrients.columns]
    portions.columns = [c.strip() for c in portions.columns]

    return foods, nutrients, portions

foods_df, nutrients_df, portions_df = load_data()

# --- RESET DAILY ---
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.selected_food = None

st.title("🥗 Food Tracker (FNDDS 2017-2018)")

# --- SEARCH ---
query = st.text_input("Search for a food:")

if query:
    matches = foods_df[foods_df["Main food description"].str.contains(query, case=False, na=False)]
    if not matches.empty:
        labels = [
            f"{row['Main food description']} ({row['WWEIA Category description']})"
            for _, row in matches.iterrows()
        ]
        choice = st.selectbox("Pick a food:", labels)
        st.session_state.selected_food = matches.iloc[labels.index(choice)]
    else:
        st.warning("No matches found.")

# --- DETAILS ---
if st.session_state.selected_food is not None:
    food = st.session_state.selected_food
    food_code = int(food["Food code"])
    desc = food["Main food description"].title()
    category = food["WWEIA Category description"]

    st.subheader(desc)
    st.write(f"Category: {category}")

    # --- Nutrients (get kcal) ---
    kcal = None
    kcal_row = nutrients_df[(nutrients_df["Food code"] == food_code) &
                            (nutrients_df["Nutrient description"].str.contains("Energy", case=False))]
    if not kcal_row.empty:
        kcal = kcal_row.iloc[0]["Nutrient value"]
        st.write(f"Energy: ~{kcal:.0f} kcal per 100 g")
    else:
        st.write("No kcal data found.")

    # --- Portions ---
    portion_rows = portions_df[portions_df["Food code"] == food_code]
    if not portion_rows.empty:
        portion_options = [
            f"{row['Portion description']} ({row['Portion weight (g)']} g)"
            for _, row in portion_rows.iterrows()
            if row["Portion weight (g)"] > 0
        ]
        portion_choice = st.selectbox("Choose a portion size:", portion_options)
    else:
        portion_choice = "100 g (default)"
        st.info("No portion equivalents found — using 100 g default.")

    # --- Serving classification (simple heuristic) ---
    if "vegetable" in category.lower() or "fruit" in category.lower():
        serving_type = "Nutrient-dense"
    else:
        serving_type = "Energy-dense"
    st.write(f"👉 Classified as: {serving_type}")

    # --- How many servings ---
    servings = st.selectbox("How many servings?", [0.25, 0.5, 0.75, 1, 2], index=3)
    st.write(f"= {servings} × {portion_choice}")

    if st.button(f"Add {desc}", key=f"add_{food_code}"):
        if serving_type == "Energy-dense":
            st.session_state.energy_servings += servings
        else:
            st.session_state.nutrient_servings += servings

# --- TOTALS ---
st.sidebar.header("Today's totals")
st.sidebar.metric("Energy-dense servings",
    round(st.session_state.energy_servings*4)/4)
st.sidebar.metric("Nutrient-dense servings",
    round(st.session_state.nutrient_servings*4)/4)
