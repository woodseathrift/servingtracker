import streamlit as st
import pandas as pd

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
nutrient_dense_prefixes = {"61", "63", "72", "73", "74", "75", "78"}

def classify_food(code: int) -> str:
    prefix = str(code)[:2]
    return "Nutrient-dense" if prefix in nutrient_dense_prefixes else "Energy-dense"

foods_df["density_category"] = foods_df["food_code"].apply(classify_food)

# --- UI ---
st.title("🥗 Food Tracker (FNDDS 2017–2018)")

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

            # Portions
            portions = portions_df[portions_df["food_code"] == code]
            if not portions.empty:
                portion_options = [
                    f"{row['portion_description']} ({row['portion_weight_g']} g)"
                    for _, row in portions.iterrows()
                ]
                portion_choice = st.selectbox("Choose a portion size:", portion_options)
                if portion_choice and pd.notna(kcal):
                    grams = float(portion_choice.split("(")[-1].replace("g)", "").strip())
                    st.write(f"You selected: {portion_choice} → {grams} g")
                    st.write(f"Estimated energy: ~{(grams/100)*kcal:.0f} kcal")
            else:
                st.info("No portion equivalents available for this food.")
