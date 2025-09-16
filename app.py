import streamlit as st
import requests
import datetime
import pandas as pd

FPED_FILE = "FPED_1718.csv"
fped_raw = pd.read_csv(FPED_FILE)

# Melt to long format
fped_long = fped_raw.melt(
    id_vars=["FOODCODE", "DESCRIPTION"],
    var_name="variable_name",
    value_name="amount"
)

# Full mapping (variable_name → description + units)
fped_meta = {
    "F_TOTAL": "Total fruits (cup eq.)",
    "F_CITMLB": "Citrus, melons & berries (cup eq.)",
    "F_OTHER": "Other fruits (cup eq.)",
    "F_JUICE": "Fruit juice (cup eq.)",
    "V_TOTAL": "Total vegetables (cup eq.)",
    "V_DRKGR": "Dark green vegetables (cup eq.)",
    "V_REDOR_TOTAL": "Red & orange vegetables (cup eq.)",
    "V_REDOR_TOMATO": "Tomatoes & tomato products (cup eq.)",
    "V_REDOR_OTHER": "Other red & orange vegetables (cup eq.)",
    "V_STARCHY_TOTAL": "Starchy vegetables (cup eq.)",
    "V_STARCHY_POTATO": "White potatoes (cup eq.)",
    "V_STARCHY_OTHER": "Other starchy vegetables (cup eq.)",
    "V_OTHER": "Other vegetables (cup eq.)",
    "V_LEGUMES": "Legumes as vegetables (cup eq.)",
    "G_TOTAL": "Total grains (oz. eq.)",
    "G_WHOLE": "Whole grains (oz. eq.)",
    "G_REFINED": "Refined grains (oz. eq.)",
    "PF_TOTAL": "Total protein foods (oz. eq.)",
    "PF_MPS_TOTAL": "Meat, poultry, seafood & cured meats (oz. eq.)",
    "PF_MEAT": "Meat (beef, pork, lamb, game) (oz. eq.)",
    "PF_CUREDMEAT": "Cured/luncheon meat (oz. eq.)",
    "PF_ORGAN": "Organ meats (oz. eq.)",
    "PF_POULT": "Poultry (oz. eq.)",
    "PF_SEAFD_HI": "Seafood high in n-3 (oz. eq.)",
    "PF_SEAFD_LOW": "Seafood low in n-3 (oz. eq.)",
    "PF_EGGS": "Eggs & substitutes (oz. eq.)",
    "PF_SOY": "Soy products (oz. eq.)",
    "PF_NUTSDS": "Nuts & seeds (oz. eq.)",
    "PF_LEGUMES": "Legumes as protein foods (oz. eq.)",
    "D_TOTAL": "Total dairy (cup eq.)",
    "D_MILK": "Milk & fortified soy milk (cup eq.)",
    "D_YOGURT": "Yogurt (cup eq.)",
    "D_CHEESE": "Cheese (cup eq.)",
    "OILS": "Oils (g)",
    "SOLID_FATS": "Solid fats (g)",
    "ADD_SUGARS": "Added sugars (tsp. eq.)",
    "A_DRINKS": "Alcoholic drinks"
}

# Add labels
fped_long["variable_label"] = fped_long["variable_name"].map(fped_meta)


# Dictionary: FOODCODE -> row of serving equivalents
fped_map = fped.set_index("FOODCODE").to_dict(orient="index")

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

    # USDA kcal/100g
    kcal = None
    for n in food.get("foodNutrients", []):
        if isinstance(n, dict):
            name = n.get("nutrientName") or n.get("nutrient", {}).get("name", "")
            if name and "energy" in name.lower() and "kj" not in name.lower():
                kcal = n.get("value")
                break
    if kcal:
        st.write(f"USDA: ~{kcal:.0f} kcal per 100 g")

    # --- FPED match ---
    food_code = food.get("foodCode")
    if food_code:
        fped_servings = get_fped_servings(food_code)
    else:
        fped_servings = []

    if fped_servings:
        choice = st.selectbox("Choose a portion size:", fped_servings)
    else:
        st.info("No FPED serving equivalents found — defaulting to 100 g.")
        choice = "100 g"


    # let user pick portion
    choice = st.selectbox("Choose a portion size:", servings_available)

    # How many portions
    servings = st.selectbox(
        "How many servings?", [0.25,0.5,0.75,1,2], index=3, key=f"{desc}_servings"
    )
    st.write(f"= {servings} × {choice}")

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
