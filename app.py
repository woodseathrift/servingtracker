import streamlit as st
import pandas as pd
import datetime

# --- FILE PATHS (must exactly match your filenames) ---
FOODS_FILE = "2017-2018 FNDDS At A Glance - Foods and Beverages.csv"
NUTRIENTS_FILE = "2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv"
PORTIONS_FILE = "2017-2018 FNDDS At A Glance - Portions and Weights.csv"

# --- LOAD DATA ---
@st.cache_data
def load_data():
    foods_df = pd.read_csv(FOODS_FILE, skiprows=2)      # skip title + blank
    nutrients_df = pd.read_csv(NUTRIENTS_FILE, skiprows=1)
    portions_df = pd.read_csv(PORTIONS_FILE, skiprows=2)
    return foods_df, nutrients_df, portions_df

foods_df, nutrients_df, portions_df = load_data()

# Normalize column names
foods_df.columns = foods_df.columns.str.strip().str.lower().str.replace(" ", "_")
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
    if "main_food_description" not in foods_df.columns:
        st.error("Could not find 'main_food_description' in Foods file. Check headers.")
    else:
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

                # --- CALORIES ---
                kcal = None
                if "energy_(kcal)" in nutrients_df.columns:
                    kcal_row = nutrients_df[nutrients_df["food_code"] == code]
                    if not kcal_row.empty:
                        kcal = kcal_row["energy_(kcal)"].values[0]

                if kcal:
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
                        factor = base_serving / kcal_in_portion if kcal_in_portion > 0 else 1
                        adj_qty = round((grams * factor), 1)
                        st.write(f"👉 1 {serving_type} serving ≈ {adj_qty} g")
                    else:
                        adj_qty = base_serving

                    servings = st.selectbox("How many servings?", [0.25, 0.5, 0.75, 1, 2], index=3)
                    total_qty = round(adj_qty * servings, 1)
                    st.write(f"= {total_qty} g")

                    if st.button(f"Add {food_row['main_food_description']}"):
                        if serving_type == "Energy-dense":
                            st.session_state.energy_servings += servings
                        else:
                            st.session_state.nutrient_servings += servings
                else:
                    st.info("No portion equivalents available for this food.")

# --- SIDEBAR TOTALS ---
st.sidebar.header("Today's totals")
st.sidebar.metric("Energy-dense servings", round(st.session_state.energy_servings * 4) / 4)
st.sidebar.metric("Nutrient-dense servings", round(st.session_state.nutrient_servings * 4) / 4)
