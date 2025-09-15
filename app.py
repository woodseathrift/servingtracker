import streamlit as st
import pandas as pd
import numpy as np

# Round to nearest 0.25
def round_quarter(x):
    try:
        return np.round(float(x) * 4) / 4
    except:
        return x

@st.cache_data
def load_fndds():
    foods = pd.read_csv("2017-2018 FNDDS At A Glance - Foods and Beverages.csv")
    nutrients = pd.read_csv("2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv")
    portions = pd.read_csv("2017-2018 FNDDS At A Glance - Portions and Weights.csv")

    # Normalize headers
    foods.columns = foods.columns.str.strip()
    nutrients.columns = nutrients.columns.str.strip()
    portions.columns = portions.columns.str.strip()

    return foods, nutrients, portions

foods, nutrients, portions = load_fndds()

st.title("🍎 FNDDS Food & Nutrient Tracker")

query = st.text_input("Enter a food (e.g. apple, bread, milk):")

if query:
    matches = foods[foods["Main food description"].str.contains(query, case=False, na=False)]
    
    if matches.empty:
        st.warning("No foods found.")
    else:
        choice = st.selectbox("Select a food:", matches["Main food description"].values)
        food_code = matches[matches["Main food description"] == choice]["Food code"].values[0]

        # Portion options
        food_portions = portions[portions["Food code"] == food_code]

        if food_portions.empty:
            st.warning("No portion data found — showing values per 100 g.")
            portion_size = 100
            portion_label = "100 g"
        else:
            portion_label = st.selectbox(
                "Select portion:",
                [f"{d} ({w} g)" for d, w in zip(food_portions["Portion description"], food_portions["Portion weight"])]
            )
            portion_size = float(portion_label.split("(")[-1].replace(" g)", ""))

        # Nutrients (per 100 g → scale to portion)
        food_nutrients = nutrients[nutrients["Food code"] == food_code].iloc[0]
        nutrient_values = food_nutrients.drop(["Food code", "Main food description", "WWEIA Category number", "WWEIA Category description"], errors="ignore")
        scaled = (nutrient_values * (portion_size / 100)).apply(round_quarter)

        # Display
        st.subheader(f"Nutrients for {choice} ({portion_label})")
        st.dataframe(scaled.reset_index().rename(columns={"index": "Nutrient", 0: "Amount"}))
