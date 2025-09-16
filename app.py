import streamlit as st
import pandas as pd
import datetime

# --- FILE PATHS (must match your local filenames) ---
FOODS_FILE = "2017-2018 FNDDS At A Glance - Foods and Beverages.csv"
NUTRIENTS_FILE = "2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv"
PORTIONS_FILE = "2017-2018 FNDDS At A Glance - Portions and Weights.csv"

st.write("Foods file columns:", list(foods_df.columns))
st.write("Nutrients file columns:", list(nutrients_df.columns))
st.write("Portions file columns:", list(portions_df.columns))

# --- RESET DAILY SERVINGS ---
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0

# --- LOAD DATA ---
@st.cache_data
def load_data():
    foods_df = pd.read_csv(FOODS_FILE)
    nutrients_df = pd.read_csv(NUTRIENTS_FILE, skiprows=1)  # skip the title row
    portions_df = pd.read_csv(PORTIONS_FILE)
    return foods_df, nutrients_df, portions_df

foods_df, nutrients_df, portions_df = load_data()

# Normalize column names
foods_df.columns = foods_df.columns.str.strip().str.lower().str.replace(" ", "_")
nutrients_df.columns = nutrients_df.columns.str.strip().str.lower().str.replace(" ", "_")
portions_df.columns = portions_df.columns.str.strip().str.lower().str.replace(" ", "_")

# --- APP TITLE ---
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

            # --- Calories per 100 g ---
            kcal_col = "energy_(kcal)"
            if kcal_col in nutrients_df.columns:
                kcal_row = nutrients_df[nutrients_df["food_code"] == code]
                kcal = kcal_row[kcal_col].values[0] if not kcal_row.empty else None
            else:
                kcal = None

            if kcal:
                st.write(f"~{kcal:.0f} kcal per 100 g")

            # --- Portion equivalents ---
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

                    # classify serving type
                    category = food_row.get("wweia_category_description", "").lower()
                    if any(x in category for x in ["fruit", "vegetable"]):
                        serving_type = "Nutrient-dense"
                        base_serving = 50
                        kcal_range = (40, 60)
                    else:
                        serving_type = "Energy-dense"
                        base_serving = 100
                        kcal_range = (80, 120)

                    # adjust serving size
                    if kcal and kcal > 0:
                        factor = base_serving / kcal
                        adj_qty = round((100 * factor) * 4) / 4
                    else:
                        adj_qty = base_serving

                    st.write(
                        f"👉 1 {serving_type} serving ≈ {adj_qty} g "
                        f"({kcal_range[0]}–{kcal_range[1]} kcal target)"
                    )

                    servings = st.selectbox(
                        "How many servings?",
                        [0.25, 0.5, 0.75, 1, 2],
                        index=3,
                        key=f"{code}_servings"
                    )

                    total_qty = round(adj_qty * servings * 4) / 4
                    st.write(f"= {total_qty} g")

                    # --- Add to daily tally ---
                    if st.button(f"Add {food_row['main_food_description']}", key=f"add_{code}"):
                        if serving_type == "Energy-dense":
                            st.session_state.energy_servings += servings
                        else:
                            st.session_state.nutrient_servings += servings

            else:
                st.info("No portion equivalents available for this food.")

# --- DAILY TOTALS ---
st.sidebar.header("Today's totals")
st.sidebar.metric("Energy-dense servings", round(st.session_state.energy_servings * 4) / 4)
st.sidebar.metric("Nutrient-dense servings", round(st.session_state.nutrient_servings * 4) / 4)
