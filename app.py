import streamlit as st
import pandas as pd
import datetime

# ---------------- Helpers ---------------- #
def round_quarter(x):
    return round(x * 4) / 4

# ---------------- Load FNDDS Data ---------------- #
@st.cache_data
def load_fndds():
    foods = pd.read_csv("2017-2018 FNDDS At A Glance - Foods and Beverages.csv")
    nutrients = pd.read_csv("2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv")
    portions = pd.read_csv("2017-2018 FNDDS At A Glance - Portions and Weights.csv")

    # Keep only calories for now
    calories = nutrients[nutrients["nutrient_desc"] == "Energy (kcal)"]
    calories = calories[["food_code", "nutrient_value"]]

    return foods, calories, portions


foods, calories, portions = load_fndds()

# ---------------- Reset Daily Session ---------------- #
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0

st.title("🥗 FNDDS Food Tracker (2017-2018)")

# ---------------- User Search ---------------- #
query = st.text_input("Search for a food (e.g. 'apple', 'rice')")

if query:
    matches = foods[foods["main_food_description"].str.contains(query, case=False, na=False)]
    if matches.empty:
        st.warning("No foods found.")
    else:
        options = [
            f"{row['main_food_description']} ({row['food_code']})"
            for _, row in matches.iterrows()
        ]
        choice = st.selectbox("Select a food:", options)
        if choice:
            code = int(choice.split("(")[-1].replace(")", ""))
            food_row = foods.loc[foods["food_code"] == code].iloc[0]
            st.subheader(food_row["main_food_description"])

            # Category
            category = food_row["food_category_desc"]
            st.write("**Category:**", category)

            # Calories per 100g
            kcal_row = calories.loc[calories["food_code"] == code]
            if not kcal_row.empty:
                kcal_per_100g = kcal_row["nutrient_value"].values[0]
                st.write(f"**Calories:** {round_quarter(kcal_per_100g)} kcal per 100 g")
            else:
                kcal_per_100g = None
                st.warning("No calorie data available.")

            # Portion options
            portion_rows = portions[portions["food_code"] == code]
            if portion_rows.empty:
                st.info("No household portion sizes available, using grams only.")
                grams = 100
                choice_portion = f"100 g"
            else:
                portion_options = []
                grams_lookup = {}
                for _, r in portion_rows.iterrows():
                    label = f"{r['portion_description']} ({round_quarter(r['gram_weight'])} g)"
                    portion_options.append(label)
                    grams_lookup[label] = r["gram_weight"]

                choice_portion = st.selectbox("Choose a portion:", portion_options)
                grams = grams_lookup[choice_portion]

            # Serving classification
            if "Vegetables" in category or "Fruits" in category:
                base_serving = 50  # kcal
                serving_type = "Nutrient-dense"
            else:
                base_serving = 100  # kcal
                serving_type = "Energy-dense"

            if kcal_per_100g:
                cal_per_g = kcal_per_100g / 100
                cal_this_portion = grams * cal_per_g
                cal_this_portion = round_quarter(cal_this_portion)

                servings = cal_this_portion / base_serving
                servings = round_quarter(servings)

                st.write(
                    f"👉 {choice_portion} ≈ {cal_this_portion} kcal "
                    f"= {servings} {serving_type} servings"
                )

                add = st.button("Add to tracker")
                if add:
                    if serving_type == "Energy-dense":
                        st.session_state.energy_servings = round_quarter(
                            st.session_state.energy_servings + servings
                        )
                    else:
                        st.session_state.nutrient_servings = round_quarter(
                            st.session_state.nutrient_servings + servings
                        )

# ---------------- Daily Totals ---------------- #
st.sidebar.header("Today's Totals")
st.sidebar.metric("Energy-dense Servings", st.session_state.energy_servings)
st.sidebar.metric("Nutrient-dense Servings", st.session_state.nutrient_servings)
