import streamlit as st
import pandas as pd
import re
import datetime

# --- FILE PATHS ---
FOODS_FILE = "2017-2018 FNDDS At A Glance - Foods and Beverages.csv"
NUTRIENTS_FILE = "2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv"
PORTIONS_FILE = "2017-2018 FNDDS At A Glance - Portions and Weights.csv"

# --- LOAD DATA ---
@st.cache_data
def load_data():
    foods_df = pd.read_csv(FOODS_FILE, skiprows=1)
    nutrients_df = pd.read_csv(NUTRIENTS_FILE, skiprows=1)
    portions_df = pd.read_csv(PORTIONS_FILE, skiprows=1)

    # Normalize column names
    for df in [foods_df, nutrients_df, portions_df]:
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(r"[()]", "", regex=True)
        )
    return foods_df, nutrients_df, portions_df

foods_df, nutrients_df, portions_df = load_data()

# --- CLASSIFICATION ---
nutrient_dense_prefixes = {"61", "63", "67", "72", "73", "74", "75", "76", "78"}

def classify_food(code: int) -> str:
    prefix = str(code)[:2]
    return "Nutrient-dense" if prefix in nutrient_dense_prefixes else "Energy-dense"

foods_df["density_category"] = foods_df["food_code"].apply(classify_food)

# --- DAILY TALLY ---
today = datetime.date.today().isoformat()
if "tally_date" not in st.session_state or st.session_state.tally_date != today:
    st.session_state.tally_date = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0

def add_serving(density_type, amount=1.0):
    if density_type == "Energy-dense":
        st.session_state.energy_servings += amount
    else:
        st.session_state.nutrient_servings += amount

# --- UI HEADER ---
st.markdown("### 📊 Daily Tally")

# Color-coded pill style
st.markdown(
    f"""
    <div style="display:flex; gap:10px; margin-bottom:10px;">
      <div style="background-color:#FFB347; padding:5px 10px; border-radius:12px;">
        <span style="color:black; font-weight:bold;">Energy-dense: {st.session_state.energy_servings:.2f}</span>
      </div>
      <div style="background-color:#90EE90; padding:5px 10px; border-radius:12px;">
        <span style="color:black; font-weight:bold;">Nutrient-dense: {st.session_state.nutrient_servings:.2f}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Manual add buttons
col1, col2 = st.columns(2)
with col1:
    st.write("➕ Energy")
    for amt in [0.25, 0.5, 0.75, 1.0]:
        if st.button(f"Add {amt}", key=f"manual_energy_{amt}"):
            add_serving("Energy-dense", amt)

with col2:
    st.write("➕ Nutrient")
    for amt in [0.25, 0.5, 0.75, 1.0]:
        if st.button(f"Add {amt}", key=f"manual_nutrient_{amt}"):
            add_serving("Nutrient-dense", amt)

st.markdown("---")

# --- FOOD SEARCH ---
query = st.text_input("Search for a food:")

filter_choice = st.selectbox(
    "Filter by type:",
    ["All", "Nutrient-dense", "Energy-dense"],
    index=0,
)

if query:
    matches = foods_df[foods_df["main_food_description"].str.contains(query, case=False, na=False)]
    if filter_choice != "All":
        matches = matches[matches["density_category"] == filter_choice]

    if matches.empty:
        st.warning("No matches found.")
    else:
        options = {
            f"{row['main_food_description']} (#{int(row['food_code'])})": int(row['food_code'])
            for _, row in matches.iterrows()
        }
        choice = st.selectbox("Select a food:", list(options.keys()))

        if choice:
            code = options[choice]
            food_row = matches[matches["food_code"] == code].iloc[0]
            category = food_row["density_category"]

            st.markdown(
                f"<h4 style='margin-bottom:0;'>{food_row['main_food_description']}</h4>",
                unsafe_allow_html=True,
            )
            st.write(f"Category: {category}")

            # Nutrients
            nut_row = nutrients_df[nutrients_df["food_code"] == code]
            kcal = None
            if not nut_row.empty:
                nut_row = nut_row.iloc[0]
                kcal = nut_row.get("energy_kcal")
                if pd.notna(kcal):
                    st.write(f"Calories (100 g): {kcal:.0f} kcal")

            # Portions
            portions = portions_df[portions_df["food_code"] == code]
            if kcal and not portions.empty:
                # Build structured options
                portion_options = []
                for _, row in portions.iterrows():
                    grams_val = row["portion_weight_g"]
                    kcal_val = (grams_val / 100) * kcal
                    label = f"{row['portion_description']} ({grams_val:.0f} g, ~{kcal_val:.0f} kcal)"
                    portion_options.append((label, grams_val, kcal_val))

                labels = [p[0] for p in portion_options]
                portion_choice = st.selectbox("Choose portion:", labels)

                if portion_choice:
                    grams, kcal_val = [
                        (g, k) for (lbl, g, k) in portion_options if lbl == portion_choice
                    ][0]

                    # Quick serving add buttons
                    cols = st.columns(4)
                    for i, amt in enumerate([0.25, 0.5, 0.75, 1.0]):
                        color = "#FF8C00" if category == "Energy-dense" else "#228B22"
                        if cols[i].button(f"+{amt}", key=f"{code}_{category}_{amt}"):
                            add_serving(category, amt)
                        cols[i].markdown(
                            f"<div style='color:{color}; font-size:12px;'>{amt}x</div>",
                            unsafe_allow_html=True,
                        )
            else:
                st.info("No portion data available for this food.")
