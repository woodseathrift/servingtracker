import streamlit as st
import pandas as pd
import datetime

# --- FILE PATHS ---
NUTRIENTS_FILE = "2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv"
PORTIONS_FILE = "2017-2018 FNDDS At A Glance - Portions and Weights.csv"

# --- LOAD DATA ---
@st.cache_data
def load_data():
    nutrients_df = pd.read_csv(NUTRIENTS_FILE, skiprows=1)
    portions_df = pd.read_csv(PORTIONS_FILE, skiprows=2)
    return nutrients_df, portions_df

nutrients_df, portions_df = load_data()

# Normalize column names
nutrients_df.columns = nutrients_df.columns.str.strip().str.lower().str.replace(" ", "_")
portions_df.columns = portions_df.columns.str.strip().str.lower().str.replace(" ", "_")

# --- RESET DAILY SERVINGS ---
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0

# --- APP TITLE ---
st.title("🥗 Food Tracker (FNDDS 2017–2018)")

# --- SEARCH ---
query = st.text_input("Search for a food:")

if query:
    if "main_food_description" not in nutrients_df.columns:
        st.error("Could not find 'main_food_description' in Nutrients file. Check headers.")
    else:
        matches = nutrients_df[nutrients_df["main_food_description"].str.contains(query, case=False, na=False)]
        if matches.empty:
            st.warning("No matches found.")
        else:
            options = [f"{row['main_food_description']} (#{row['food_code']})" for _, row in matches.iterrows()]
            choice = st.selectbox("Select a food:", options)

            if choice:
                code = int(choice.split("#")[-1].strip())
                food_row = matches[matches["food_code"] == code].iloc[0]

                st.subheader(food_row["main_food_description"])
                st.write(f"Category: {food_row.get('wweia_category_description', 'Unknown')}")

                # --- CALORIES ---
                kcal = food_row.get("energy_(kcal)", None)
                if pd.notnull(kcal):
                    st.write(f"~{kcal:.0f} kcal per 100 g")
                else:
                    st.write("No kcal data available.")

                # --- PORTION SELECTION ---
                portions = portions_df[portions_df["food_code"] == code]
                if not portions.empty:
                    portion_options = [
                        f"{row['portion_description']} ({row['portion_weight_(g)']} g)"
                        for _, row in portions.iterrows()
                    ]
                    portion_choice = st.selectbox("Choose a portion size:", portion_options)
                    grams = None
                    if portion_choice:
                        grams = float(portion_choice.split("(")[-1].replace("g)", "").strip())
                        st.write(f"You selected: {portion_choice} → {grams} g")

                    # --- CLASSIFY SERVING TYPE ---
                    cat = food_row.get("wweia_category_description", "")
                    if isinstance(cat, str) and any(word in cat.lower() for word in ["fruit", "vegetable"]):
                        serving_type = "Nutrient-dense"
                        base_serving = 50
                    else:
                        serving_type = "Energy-dense"
                        base_serving = 100

                    if kcal and grams:
                        kcal_per_g = kcal / 100
                        kcal_in_portion = grams * kcal_per_g
                        factor = base_serving / kcal_in
