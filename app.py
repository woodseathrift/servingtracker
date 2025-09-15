import streamlit as st
import requests

# --- API Setup ---
API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"  # Get one free at https://fdc.nal.usda.gov/api-key-signup.html
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
DETAIL_URL = "https://api.nal.usda.gov/fdc/v1/food/{}"

st.title("🥦 USDA FoodData Central Explorer")

# --- Search box ---
query = st.text_input("Search for a food (e.g., 'apple', 'banana', 'cheerios')")

if st.button("Search") and query:
    params = {"api_key": API_KEY, "query": query, "pageSize": 10}
    r = requests.get(SEARCH_URL, params=params)

    if r.status_code != 200:
        st.error("Search failed. Check API key or network.")
    else:
        data = r.json()
        foods = data.get("foods", [])

        if not foods:
            st.warning("No foods found.")
        else:
            # Let user pick which result
            options = {f["description"]: f["fdcId"] for f in foods}
            choice = st.selectbox("Pick a food", list(options.keys()))

            if st.button("Load details"):
                fdc_id = options[choice]
                r2 = requests.get(DETAIL_URL.format(fdc_id), params={"api_key": API_KEY})
                if r2.status_code == 200:
                    food = r2.json()
                    st.subheader(food.get("description", "Unknown"))

                    # Category
                    category = food.get("foodCategory", {}).get("description", "Unknown")
                    st.write(f"**Category:** {category}")

                    # Nutrients (just calories for now)
                    nutrients = food.get("foodNutrients", [])
                    calories = next((n["amount"] for n in nutrients if n.get("nutrient", {}).get("name") == "Energy"), None)
                    if calories:
                        st.write(f"**Calories:** {calories} kcal per 100g")

                    # Measures
                    if "foodPortions" in food:
                        st.write("**Common Measures:**")
                        for portion in food["foodPortions"]:
                            measure = portion.get("modifier") or portion.get("portionDescription")
                            gram_weight = portion.get("gramWeight")
                            if measure and gram_weight:
                                st.write(f"- {measure}: {gram_weight} g")
                else:
                    st.error("Failed to load details.")
