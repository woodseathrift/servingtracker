import streamlit as st
import requests
import datetime

# --- CONFIG ---
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

NUTRIENT_DENSE_CATEGORIES = [
    "Fruits and Fruit Juices",
    "Vegetables and Vegetable Products",
]

# --- RESET DAILY ---
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.search_results = []
    st.session_state.selected_food = None

st.title("🥗 Food Tracker (USDA)")

def round_quarter(x):
    return round(x * 4) / 4

# --- SEARCH ---
query = st.text_input("Enter a food:")

if query and st.button("Search"):
    params = {
        "api_key": FDC_API_KEY,
        "query": query,
        "pageSize": 15,
        "dataType": "Foundation,SR Legacy"
    }
    r = requests.get(SEARCH_URL, params=params)
    if r.ok:
        foods = r.json().get("foods", [])
        filtered = [f for f in foods if f.get("foodCategory")]
        st.session_state.search_results = filtered
        if filtered:
            st.session_state.selected_food = filtered[0]
    else:
        st.error(f"USDA API error: {r.status_code}")

# --- PICKER ---
if st.session_state.search_results:
    labels = [
        f"{f['description']} ({f.get('foodCategory','Unknown')})"
        for f in st.session_state.search_results
    ]
    choice = st.selectbox(
        "Pick a food:", labels, index=0, key="choice_box"
    )
    st.session_state.selected_food = st.session_state.search_results[labels.index(choice)]

# --- DETAILS ---
if st.session_state.selected_food:
    food = st.session_state.selected_food
    desc = food.get("description", "Unknown").title()
    cat = food.get("foodCategory", "Unknown")

    st.subheader(desc)
    st.write(f"Category: {cat}")

    # Extract kcal/100g
    kcal = None
    for n in food.get("foodNutrients", []):
        if isinstance(n, dict):
            name = n.get("nutrientName") or n.get("nutrient", {}).get("name", "")
            if name and "energy" in name.lower() and "kj" not in name.lower():
                kcal = n.get("value")
                break

    if kcal:
        st.write(f"USDA: ~{kcal:.0f} kcal per 100 g")
    else:
        st.write("No kcal data available.")

    # --- Household measures ---
    portions = food.get("foodPortions", [])
    if portions:
        labels = []
        gram_weights = []
        for p in portions:
            desc_p = p.get("portionDescription")
            grams = p.get("gramWeight")
            if desc_p and grams:
                labels.append(f"{desc_p} (~{grams:.0f} g)")
                gram_weights.append(grams)

        # let user pick portion size
        portion_choice = st.selectbox("Choose a portion:", labels, index=0)
        grams_per_portion = gram_weights[labels.index(portion_choice)]
    else:
        st.info("No household measures available — using 100 g as base.")
        grams_per_portion = 100
        portion_choice = "100 g"

    # number of portions
    servings = st.selectbox(
        "How many servings?", [0.25,0.5,0.75,1,2], index=3, key=f"{desc}_servings"
    )
    total_qty = round_quarter(grams_per_portion * servings)
    st.write(f"= {total_qty} g total ({portion_choice} × {servings})")

    if st.button(f"Add {desc}", key=f"add_{desc}"):
        if cat in NUTRIENT_DENSE_CATEGORIES:
            st.session_state.nutrient_servings += servings
        else:
            st.session_state.energy_servings += servings

# --- TOTALS ---
st.sidebar.header("Today's totals")
st.sidebar.metric("Energy-dense servings",
    round(st.session_state.energy_servings*4)/4)
st.sidebar.metric("Nutrient-dense servings",
    round(st.session_state.nutrient_servings*4)/4)
