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

# --- SERVING PICKER ---
COMMON_UNITS = [
    "cup", "tablespoon", "tbsp", "teaspoon", "tsp",
    "slice", "piece", "serving", "packet", "bar", "stick", "bottle", "can"
]

def pick_serving(portions, kcal_per_100g, density_type):
    if pd.isna(kcal_per_100g) or kcal_per_100g == 0:
        return None, None

    if density_type == "Nutrient-dense":
        target_kcal, tol = 50, 10
    else:
        target_kcal, tol = 100, 20

    best_serving = None
    best_diff = float("inf")

    for _, row in portions.iterrows():
        grams = row["portion_weight_g"]
        kcal = (grams / 100) * kcal_per_100g
        desc = str(row["portion_description"]).lower()

        if abs(kcal - target_kcal) <= tol:
            is_common = any(unit in desc for unit in COMMON_UNITS)

            match = re.match(r"(\d+(\.\d+)?)\s+(.*)", desc)
            if match:
                qty = float(match.group(1))
                unit = match.group(3)
                qty_rounded = round(qty * 4) / 4
                desc = f"{qty_rounded} {unit}"

            diff = abs(kcal - target_kcal)

            if best_serving is None:
                best_diff = diff
                best_serving = (desc, kcal)
            else:
                current_desc = best_serving[0].lower()
                if (is_common and not any(u in current_desc for u in ["g", "gram", "oz"])) or diff < best_diff:
                    best_diff = diff
                    best_serving = (desc, kcal)

    # Fallback: grams only if nothing else worked
    if not best_serving:
        grams = (target_kcal / kcal_per_100g) * 100
        desc = f"{grams:.0f} g"
        best_serving = (desc, target_kcal)

    return best_serving

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

# --- UI ---
st.markdown("### 📊 Daily Tally")
st.write(f"**Energy-dense servings:** {st.session_state.energy_servings:.2f}")
st.write(f"**Nutrient-dense servings:** {st.session_state.nutrient_servings:.2f}")

# Manual add buttons (unique keys)
col1, col2 = st.columns(2)
with col1:
    st.write("➕ Energy-dense")
    for amt in [0.25, 0.5, 0.75, 1.0]:
        if st.button(f"Add {amt}", key=f"manual_energy_{amt}"):
            add_serving("Energy-dense", amt)

with col2:
    st.write("➕ Nutrient-dense")
    for amt in [0.25, 0.5, 0.75, 1.0]:
        if st.button(f"Add {amt}", key=f"manual_nutrient_{amt}"):
            add_serving("Nutrient-dense", amt)

st.markdown("---")

query = st.text_input("Search for a food:")

filter_choice = st.selectbox(
    "Filter by type:",
    ["All", "Nutrient-dense", "Energy-dense"]
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

            st.subheader(food_row["main_food_description"])
            st.write(f"Category: {food_row.get('wweia_category_description', 'Unknown')}")
            st.write(f"Density type: {food_row['density_category']}")

            # Nutrients
            nut_row = nutrients_df[nutrients_df["food_code"] == code]
            kcal = protein = carbs = fat = None
            if not nut_row.empty:
                nut_row = nut_row.iloc[0]
                kcal = nut_row.get("energy_kcal")
                protein = nut_row.get("protein_g")
                carbs = nut_row.get("carbohydrate_g")
                fat = nut_row.get("total_fat_g")

                st.markdown("**Nutrients per 100 g:**")
                if pd.notna(kcal): st.write(f"Energy: {kcal:.0f} kcal")
                if pd.notna(protein): st.write(f"Protein: {protein:.1f} g")
                if pd.notna(carbs): st.write(f"Carbs: {carbs:.1f} g")
                if pd.notna(fat): st.write(f"Fat: {fat:.1f} g")

            # Suggested serving
            portions = portions_df[portions_df["food_code"] == code]
            if pd.notna(kcal) and not portions.empty:
                serving = pick_serving(portions, kcal, food_row["density_category"])
                if serving:
                    desc, kcal_val = serving
                    st.markdown(f"**Suggested serving:** {desc} (~{kcal_val:.0f} kcal)")

                    st.write("Add to tally:")
                    cols = st.columns(4)
                    for i, amt in enumerate([0.25, 0.5, 0.75, 1.0]):
                        if cols[i].button(f"+{amt} serving", key=f"{code}_{food_row['density_category']}_{amt}"):
                            add_serving(food_row["density_category"], amt)

            elif pd.notna(kcal):
                target = 50 if food_row["density_category"] == "Nutrient-dense" else 100
                grams = (target / kcal) * 100
                st.markdown(f"**Suggested serving:** {grams:.0f} g (~{target} kcal)")
                if st.button("✅ Add this serving to tally", key=f"{code}_fallback"):
                    add_serving(food_row["density_category"])
            else:
                st.info("Nutrient data not available for this food.")
