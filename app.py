import streamlit as st
import pandas as pd

# Load data (replace with your actual file paths)
foods = pd.read_csv("foods.csv")
nutrients = pd.read_csv("nutrients.csv")
portions = pd.read_csv("portions.csv")

COMMON_UNITS = ["cup", "tablespoon", "teaspoon", "slice", "package", "oz", "ounce"]

# ---- Serving size helpers ----
def pick_fractional_serving(food_row, target_cal):
    kcal_row = nutrients[nutrients["food_code"] == food_row["food_code"]]
    if kcal_row.empty:
        return "No kcal data", 0, 0, ""
    kcal_per_100g = kcal_row.iloc[0]["energy_kcal"]
    kcal_per_g = kcal_per_100g / 100

    portion_rows = portions[portions["food_code"] == food_row["food_code"]]
    usable_portions = []
    for _, row in portion_rows.iterrows():
        desc = str(row["portion_description"]).lower()
        if any(u in desc for u in COMMON_UNITS):
            usable_portions.append(row)

    if not usable_portions:
        grams = round(target_cal / kcal_per_g)
        return f"{grams} g (~{target_cal} kcal)", grams, target_cal, "g"

    chosen = None
    for _, row in pd.DataFrame(usable_portions).iterrows():
        grams = row["portion_weight_g"]
        kcal_per_portion = grams * kcal_per_g
        fraction = target_cal / kcal_per_portion
        fraction = round(fraction * 4) / 4
        if fraction >= 0.25:
            chosen = (row, fraction, kcal_per_portion, grams)
            break

    if not chosen:
        grams = round(target_cal / kcal_per_g)
        return f"{grams} g (~{target_cal} kcal)", grams, target_cal, "g"

    base, fraction, kcal_per_portion, grams = chosen
    desc = str(base["portion_description"]).lower()
    if desc.startswith("1 "):
        desc = desc[2:]
    elif desc.startswith("one "):
        desc = desc[4:]

    approx_cal = round(fraction * kcal_per_portion)
    total_grams = round(fraction * grams)

    return f"{fraction} {desc} (≈{total_grams} g, ~{approx_cal} kcal)", total_grams, approx_cal, desc


def serving_for_food(food_row):
    code = str(food_row["food_code"])
    nutrient_dense_prefixes = {"61", "63", "67", "72", "73", "74", "75", "76", "78"}
    if code.startswith(tuple(nutrient_dense_prefixes)):
        density = "Nutrient-dense"
        serving_text, grams, kcal, unit_desc = pick_fractional_serving(food_row, 50)
    else:
        density = "Energy-dense"
        serving_text, grams, kcal, unit_desc = pick_fractional_serving(food_row, 100)
    return density, serving_text, grams, kcal, unit_desc


# ---- UI ----
st.title("Food Serving Tracker")

# Input + button
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("Search food", key="food_search")
with col2:
    search_clicked = st.button("Search")

# Determine whether to search
do_search = search_clicked or (query and query.strip())

choice = "-- choose a food --"
if do_search:
    matches = foods[foods["main_food_description"].str.contains(query, case=False, na=False)]
    options = ["-- choose a food --"] + [
        f"{row['main_food_description']} (#{row['food_code']})"
        for _, row in matches.iterrows()
    ]
    choice = st.selectbox("Pick a food", options, key="food_choice")

# After the user picks a food
if choice and choice != "-- choose a food --":
    code = int(choice.split("#")[-1].strip(")"))
    food_row = foods.loc[foods["food_code"] == code].iloc[0]

    density, serving_text, base_grams, base_kcal, unit_desc = serving_for_food(food_row)

    # User amount choice (default = 1)
    amt = st.selectbox(
        "Number of servings",
        [0.25, 0.5, 0.75, 1, 2],
        index=3,
        key="amt_choice"
    )

    total_grams = round(base_grams * amt)
    total_kcal = round(base_kcal * amt)

    # Clean serving display
    if unit_desc == "g":
        display_serving = f"{total_grams} g (~{total_kcal} kcal)"
    else:
        display_serving = f"{amt} {unit_desc} (≈{total_grams} g, ~{total_kcal} kcal)"

    color = "#330000" if density == "Energy-dense" else "#003300"
    st.markdown(
        f"<div style='background-color:{color}; padding:8px; border-radius:8px;'>"
        f"<b>{food_row['main_food_description']}</b><br>{density}: {display_serving}</div>",
        unsafe_allow_html=True,
    )
