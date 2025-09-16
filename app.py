import streamlit as st
import pandas as pd
import datetime

# --- FILE PATHS (must exactly match your filenames) ---
NUTRIENTS_FILE = "2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv"
PORTIONS_FILE = "2017-2018 FNDDS At A Glance - Portions and Weights.csv"

# --- LOAD DATA ---
@st.cache_data
def load_data():
    nutrients_df = pd.read_csv(NUTRIENTS_FILE, skiprows=2)  # skip metadata rows
    portions_df = pd.read_csv(PORTIONS_FILE, skiprows=2)
    return nutrients_df, portions_df

nutrients_df, portions_df = load_data()

# Normalize columns
nutrients_df.columns = nutrients_df.columns.str.strip().str.lower().str.replace(" ", "_")
portions_df.columns = portions_df.columns.str.strip().str.lower().str.replace(" ", "_")

# --- CATEGORY BUCKETS ---
NUTRIENT_DENSE_CATEGORIES = [
    "Fruits", "Fruit", "Vegetables", "Vegetable"
]

# --- RESET DAILY ---
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0

# --- UI ---
st.title("🥗 Food Tracker (FNDDS 2017–2018)")

query = st.text_input("Search for a food:")

if query:
    matches = nutrients_df[nutrients_df["main_food_description"].str.contains(query, case=False, na=False)]
    if matches.empty:
        st.warning("No matches found.")
    else:
        options = [f"{row['main_food_description']} (#{int(row['food_code'])})"
                   for _, row in matches.iterrows()]
        choice = st.selectbox("Select a food:", options)

        if choice:
            code = int(choice.split("#")[-1].strip())
            food_row = matches[matches["food_code"] == code].iloc[0]

            desc = food_row["main_food_description"]
            cat = food_row.get("wweia_category_description", "Unknown")

            st.subheader(desc)
            st.write(f"Category: {cat}")

            # kcal per 100 g
            kcal = food_row.get("energy_(kcal)", None)
            if pd.notna(kcal):
                st.write(f"~{kcal:.0f} kcal per 100 g")

            # classify as nutrient vs energy dense
            if any(word.lower() in str(cat).lower() for word in NUTRIENT_DENSE_CATEGORIES):
                serving_type = "Nutrient-dense"
            else:
                serving_type = "Energy-dense"

            # Portion equivalents
            portions = portions_df[portions_df["food_code"] == code]
            if not portions.empty:
                portion_options = [
                    f"{row['portion_description']} ({row['portion_weight_(g)']} g)"
                    for _, row in portions.iterrows()
                ]
                portion_choice = st.selectbox("Choose a portion size:", portion_options)

                grams = float(portion_choice.split("(")[-1].replace("g)", "").strip())

                # how many servings
                servings = st.selectbox(
                    "How many servings?",
                    [0.25, 0.5, 0.75, 1, 2],
                    index=3,
                    key=f"{desc}_servings"
                )
                total_qty = servings * grams
                st.write(f"= {total_qty:.1f} g total")

                if st.button(f"Add {desc}", key=f"add_{desc}"):
                    if serving_type == "Energy-dense":
                        st.session_state.energy_servings += servings
                    else:
                        st.session_state.nutrient_servings += servings
            else:
                st.info("No portion equivalents available for this food.")

# --- TOTALS ---
st.sidebar.header("Today's totals")
st.sidebar.metric("Energy-dense servings",
    round(st.session_state.energy_servings * 4) / 4)
st.sidebar.metric("Nutrient-dense servings",
    round(st.session_state.nutrient_servings * 4) / 4)
