import streamlit as st
import pandas as pd
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

    for df in [foods_df, nutrients_df, portions_df]:
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(r"[()]", "", regex=True)
        )

    return foods_df, nutrients_df, portions_df


foods_df, nutrients_df, portions_df = load_data()

# --- CATEGORIES ---
NUTRIENT_CODES = {"61", "63", "72", "73", "74", "75", "78"}


def classify_food(code: int) -> str:
    return "Nutrient-dense" if str(code)[:2] in NUTRIENT_CODES else "Energy-dense"


foods_df["density_category"] = foods_df["food_code"].apply(classify_food)

# --- SESSION STATE ---
today = datetime.date.today()
if "last_date" not in st.session_state or st.session_state.last_date != today:
    st.session_state.tally = {"Energy-dense": 0, "Nutrient-dense": 0}
    st.session_state.last_date = today


def add_serving(category, amount=1.0):
    st.session_state.tally[category] += amount


# --- UI ---
st.title("🥗 Food Tracker (Compact)")

# --- Quick Manual Tally ---
st.markdown("### 📊 Quick Add")
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### ⚡ Energy-dense")
    for amt in [0.25, 0.5, 0.75, 1.0]:
        if st.button(f"+{amt}", key=f"energy_{amt}"):
            add_serving("Energy-dense", amt)

with col2:
    st.markdown("#### 🌱 Nutrient-dense")
    for amt in [0.25, 0.5, 0.75, 1.0]:
        if st.button(f"+{amt}", key=f"nutrient_{amt}"):
            add_serving("Nutrient-dense", amt)

# --- Food Search ---
st.markdown("### 🔍 Search Food")
query = st.text_input("Enter food:")

if query:
    matches = foods_df[
        foods_df["main_food_description"].str.contains(query, case=False, na=False)
    ]
    if matches.empty:
        st.warning("No matches found.")
    else:
        options = {
            f"{row['main_food_description']} (#{int(row['food_code'])})": int(
                row["food_code"]
            )
            for _, row in matches.iterrows()
        }
        choice = st.selectbox("Pick food:", list(options.keys()))

        if choice:
            code = options[choice]
            food_row = matches[matches["food_code"] == code].iloc[0]
            category = food_row["density_category"]

            # Calories from nutrient table
            nut_row = nutrients_df[nutrients_df["food_code"] == code]
            kcal = None
            if not nut_row.empty:
                kcal = nut_row.iloc[0].get("energy_kcal")

            # Portions
            portions = portions_df[portions_df["food_code"] == code]
            if not portions.empty and pd.notna(kcal):
                # Prefer non-gram units
                common = portions[
                    ~portions["portion_description"].str.contains("oz|g", case=False, na=False)
                ]
                if common.empty:
                    common = portions
                portion_options = [
                    f"{row['portion_description']} ({row['portion_weight_g']} g, ~{(row['portion_weight_g']/100)*kcal:.0f} kcal)"
                    for _, row in common.iterrows()
                ]
                portion_choice = st.selectbox("Choose portion:", portion_options)

                if portion_choice:
                    grams = float(
                        portion_choice.split("(")[1].split("g")[0].strip()
                    )
                    cols = st.columns(4)
                    for i, amt in enumerate([0.25, 0.5, 0.75, 1.0]):
                        if cols[i].button(
                            f"+{amt}", key=f"{code}_{category}_{amt}"
                        ):
                            add_serving(category, amt)
            else:
                st.info("No portion data available.")

# --- TALLY DISPLAY ---
st.markdown("### 📅 Today’s Tally")
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f"<div style='background:#ffe0e0;padding:10px;border-radius:10px;'>"
        f"<b>⚡ Energy-dense:</b> {st.session_state.tally['Energy-dense']:.2f} servings"
        f"</div>",
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"<div style='background:#e0ffe0;padding:10px;border-radius:10px;'>"
        f"<b>🌱 Nutrient-dense:</b> {st.session_state.tally['Nutrient-dense']:.2f} servings"
        f"</div>",
        unsafe_allow_html=True,
    )
