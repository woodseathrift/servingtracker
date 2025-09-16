import streamlit as st
import pandas as pd

# --- FILE PATHS ---
FOODS_FILE = "2017-2018 FNDDS At A Glance - Foods and Beverages.csv"
NUTRIENTS_FILE = "2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv"
PORTIONS_FILE = "2017-2018 FNDDS At A Glance - Portions and Weights.csv"

# --- LOAD DATA ---
@st.cache_data
def load_data():
    foods_df = pd.read_csv(FOODS_FILE)
    nutrients_df = pd.read_csv(NUTRIENTS_FILE)
    portions_df = pd.read_csv(PORTIONS_FILE)
    return foods_df, nutrients_df, portions_df

foods_df, nutrients_df, portions_df = load_data()

# Normalize column names (strip spaces, lowercase, replace with _)
foods_df.columns = foods_df.columns.str.strip().str.lower().str.replace(" ", "_")
nutrients_df.columns = nutrients_df.columns.str.strip().str.lower().str.replace(" ", "_")
portions_df.columns = portions_df.columns.str.strip().str.lower().str.replace(" ", "_")

# --- UI ---
st.title("🥗 Food Tracker (FNDDS 2017–2018)")

query = st.text_input("Search for a food:")

if query:
    matches = foods_df[foods_df["main_food_description"].str.contains(query, case=False, na=False)]
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

            # Nutrients (kcal only for now)
            if "nutrient_description" in nutrients_df.columns:
                kcal_row = nutrients_df[
                    (nutrients_df["food_code"] == code) &
                    (nutrients_df["nutrient_description"].str.contains("Energy", case=False))
                ]
                kcal = kcal_row["nutrient_value_per_100_g"].values[0] if not kcal_row.empty else None
            else:
                kcal = None

            if kcal:
                st.write(f"~{kcal:.0f} kcal per 100 g")

            # Portion equivalents
            portions = portions_df[portions_df["food_code"] == code]
            if not portions.empty:
                portion_options = [
                    f"{row['portion_description']} ({row['portion_weight_(g)']} g)"
                    for _, row in portions.iterrows()
                ]
                portion_choice = st.selectbox("Choose a portion size:", portion_options)
                if portion_choice:
                    grams = float(portion_choice.split("(")[-1].replace("g)", "").strip())
                    st.write(f"You selected: {portion_choice} → {grams} g")
            else:
                st.info("No portion equivalents available for this food.")
