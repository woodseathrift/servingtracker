import streamlit as st
import requests

# --- API SETUP ---
NUTRITIONIX_APP_ID = "5107911f"   # replace with your own
NUTRITIONIX_APP_KEY = "39b7b779dbafa5fe4ae28af495a3c349"  # replace with your own
SEARCH_URL = "https://trackapi.nutritionix.com/v2/search/instant"

headers = {
    "x-app-id": NUTRITIONIX_APP_ID,
    "x-app-key": NUTRITIONIX_APP_KEY,
    "Content-Type": "application/json"
}

st.title("🔎 Nutritionix Category Tester (Search API)")

food_input = st.text_input("Enter a food (e.g. 'apple', 'coke')")

if st.button("Search") and food_input:
    params = {"query": food_input, "detailed": True}
    r = requests.get(SEARCH_URL, headers=headers, params=params)

    if r.status_code != 200:
        st.error(f"API Error: {r.status_code}")
    else:
        data = r.json()
        st.json(data)  # dump the full JSON so you can see categories/tags

        # Try to print categories in a cleaner way if available
        for section in ["common", "branded"]:
            for item in data.get(section, []):
                st.write(f"**Name:** {item.get('food_name')}")
                st.write(f"Category: {item.get('food_category')}")
                st.write("---")
