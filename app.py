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

# --- COMMON UNITS ---
COMMON_UNITS = [
    "cup", "tablespoon", "tbsp", "teaspoon", "tsp",
    "slice", "piece", "serving", "packet", "bar",
    "stick", "bottle", "can"
]

# --- SERVING PICKER ---
def pick_serving(portions, kcal_per_100g, density_type):
    """Pick serving closest to ~50 or ~100 kcal, preferring common units."""
    if pd.isna(kcal_per_100g) or kcal_per_100g == 0:
        return None, None, None

    if density_type == "Nutrient-dense":
        target_kcal, tol = 50, 10
    else:
        target_kcal, tol = 100, 20

    best = None
    best_diff = float("inf")

    for _, row in portions.iterrows():
        grams = row["portion_weight_g"]
        kcal_val = (grams / 100) * kcal_per_100g
        desc = str(row["portion_description"]).lower()

        is_common = any(unit in desc for unit in COMMON_UNITS)
        diff = abs(kcal_val - target_kcal)

        if diff <= tol:
            if best is None:
                best = (desc, grams, kcal_val)
                best_diff = diff
            else:
                # Prefer common units OR closer kcal match
                best_is_common = any(unit in best[0] for unit in COMMON_UNITS)
                if (is_common and not best_is_common) or diff < best_diff:
                    best = (desc, grams, kcal_val)
                    best_diff = diff

    if best:
        return best
    else:
        # Fallback: grams only
        grams = (target_kcal / kcal_per_100g) * 100
        return (f"{grams:.0f} g", grams, target_kcal)

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
    st.experimental_rerun()  # 🔑 show updated tally immediately

# --- UI ---
st.markdown("### 📊 Daily Tally")

col1, col2 = st.columns(2)
with col1:
    st.markdown(
        f"<div style='background-color:#ffcccc; padding:8px; border-radius:8px; text-align:center;'>"
        f"<span style='font-size:20px; color:black;'><b>Energy-dense:</b><br>{st.session_state.energy_servings:.2f}</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    amt = st.selectbox("Energy increment", [0.25, 0.5, 0.75, 1.0], key="energy_inc")
    if st.button("Add Energy", key="energy_btn"):
        add_serving("Energy-dense", amt)

with col2:
    st.markdown(
        f"<div style='background-color:#ccffcc; padding:8px; border-radius:8px; text-align:center;'>"
        f"<span style='font-size:20px; color:black;'><b>Nutrient-dense:</b><br>{st.session_state.nutrient_servings:.2f}</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    amt = st.selectbox("Nutrient increment", [0.25, 0.5, 0.75, 1.0], key="nutrient_inc")
    if st.button("Add Nutrient", key="nutrient_btn"):
        add_serving("Nutrient-dense", amt)

st.markdown("---")

# --- FOOD SEARCH ---
query = st.text_input("🔍 Search for a food:")
filter_choice = st.selectbox("Filter by type:", ["All", "Nutrient-dense", "Energy-dense"])

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

            st.subheader(food_row["main_food_description"])
            category = food_row["density_category"]
            st.write(f"**Density type:** {category}")

            # Nutrients
            nut_row = nutrients_df[nutrients_df["food_code"] == code]
            if not nut_row.empty:
                kcal = nut_row.iloc[0].get("energy_kcal")
            else:
                kcal = None

            # Suggested serving
            portions = portions_df[portions_df["food_code"] == code]
            if kcal and not portions.empty:
                serving = pick_serving(portions, kcal, category)
                if serving:
                    desc, grams_val, kcal_val = serving
                    st.markdown(f"**Suggested serving:** {desc} ({grams_val:.0f} g, ~{kcal_val:.0f} kcal)")

                    amt = st.selectbox("Add servings", [0.25, 0.5, 0.75, 1.0], key=f"add_{code}")
                    if st.button("➕ Add to tally", key=f"btn_{code}"):
                        add_serving(category, amt)

            elif kcal:
                target = 50 if category == "Nutrient-dense" else 100
                grams = (target / kcal) * 100
                st.markdown(f"**Suggested serving:** {grams:.0f} g (~{target} kcal)")
                if st.button("➕ Add to tally", key=f"btn_fallback_{code}"):
                    add_serving(category)
            else:
                st.info("Nutrient data not available for this food.")
