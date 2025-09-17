import streamlit as st
import pandas as pd
import numpy as np

# ---------- Load Data ----------
@st.cache_data
def load_foods():
    foods = pd.read_csv("foods.csv", dtype={"food_code": str})
    nutrients = pd.read_csv("nutrients.csv")
    portions = pd.read_csv("portions.csv")
    return foods, nutrients, portions

foods, nutrients, portions = load_foods()

# ---------- Settings ----------
nutrient_dense_prefixes = {"61", "63", "67", "72", "73", "74", "75", "76", "78"}

# ---------- Helper Functions ----------
def pick_fractional_serving(food_row, target_kcal=100):
    fcode = food_row["food_code"]
    portion_rows = portions[portions["food_code"] == fcode]
    nutrient_rows = nutrients[nutrients["food_code"] == fcode]

    energy = nutrient_rows.loc[nutrient_rows["nutrient_name"].str.contains("Energy", case=False), "amount"]
    if energy.empty:
        return "No energy data", 0, 0, 0
    kcal_per_100g = energy.iloc[0]
    
    best_diff = float("inf")
    best = None

    for _, row in portion_rows.iterrows():
        grams = row["gram_weight"]
        kcal = grams * kcal_per_100g / 100
        mult = round(target_kcal / kcal / 0.25) * 0.25
        adj_kcal = kcal * mult
        diff = abs(adj_kcal - target_kcal)
        if diff < best_diff and mult > 0:
            best_diff = diff
            best = (mult, row["portion_description"], grams * mult, adj_kcal)

    if not best:
        return "No valid portion", 0, 0, 0
    
    mult, desc, grams, kcal = best
    if mult == 1:
        serving_text = f"{desc} (≈{round(grams)} g, ~{round(kcal)} kcal)"
    else:
        serving_text = f"{mult} × {desc} (≈{round(grams)} g, ~{round(kcal)} kcal)"
    return serving_text, grams, kcal

def serving_for_food(food_row):
    prefix = food_row["food_code"][:2]
    serving_text, grams, kcal = pick_fractional_serving(food_row, 100 if prefix in nutrient_dense_prefixes else 200)
    density = "Nutrient-dense" if prefix in nutrient_dense_prefixes else "Energy-dense"
    return density, serving_text, grams, kcal

# ---------- Streamlit UI ----------
st.title("Serving Size Tracker")

# Search bar + button
col1, col2 = st.columns([4,1])
with col1:
    query = st.text_input("Search foods", key="food_search")
with col2:
    clicked = st.button("Enter")

# Food search
matches = []
if query or clicked:
    matches = foods[foods["main_food_description"].str.contains(query, case=False, na=False, regex=False)]

options = ["-- choose a food --"] + [f"{r['main_food_description']} #{r['food_code']}" for _, r in matches.iterrows()]
choice = st.selectbox("Results", options, key="food_choice", index=0)

# Amount choice
amt = st.selectbox("Amount", [0.25,0.5,0.75,1,1.25,1.5,2,3,4], key="amt_choice", index=3)

# After the user picks a food
if choice and choice != "-- choose a food --":
    code = int(choice.split("#")[-1].strip())
    food_row = foods.loc[foods["food_code"] == str(code)].iloc[0]

    density, serving_text, base_grams, base_kcal = serving_for_food(food_row)

    # Apply user amount choice
    total_grams = round(base_grams * amt)
    total_kcal = round(base_kcal * amt)

    # Build display string
    if amt == 1:
        display_serving = f"{density}: {serving_text}"
    else:
        display_serving = (
            f"{density}: {amt} × {serving_text} → (≈{total_grams} g, ~{total_kcal} kcal)"
        )

    st.write(display_serving)
