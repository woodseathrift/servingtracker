import streamlit as st
import requests

# --- API SETUP ---
NUTRITIONIX_APP_ID = "5107911f"   # replace with your own
NUTRITIONIX_APP_KEY = "39b7b779dbafa5fe4ae28af495a3c349"  # replace with your own
NUTRITIONIX_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

headers = {
    "x-app-id": NUTRITIONIX_APP_ID,
    "x-app-key": NUTRITIONIX_APP_KEY,
    "Content-Type": "application/json"
}

st.title("🔎 Nutritionix Category Tester")

food_input = st.text_input("Enter a food (e.g. 'apple', 'milk')")

if st.button("Lookup") and food_input:
    payload = {"query": food_input}
    r = requests.post(NUTRITIONIX_URL, headers=headers, json=payload)

    if r.status_code != 200:
        st.error(f"API Error: {r.status_code}")
    else:
        foods = r.json().get("foods", [])
        if not foods:
            st.warning("No results found.")
        else:
            for f in foods:
                st.write(f"**Food Name:** {f.get('food_name')}")
                st.json(f)  # dump the full JSON so you can see all keys
                st.write("---")
