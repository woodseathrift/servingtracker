import streamlit as st
import requests

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
DETAIL_URL = "https://api.nal.usda.gov/fdc/v1/food/{}"
API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"  # replace with your USDA API key

st.title("🍎 USDA Food Category Lookup")

# Ensure session state keys
if "results" not in st.session_state:
    st.session_state.results = {}
if "selected" not in st.session_state:
    st.session_state.selected = None

# --- SEARCH BAR ---
query = st.text_input("Enter a food (e.g. 'apple', 'chicken'):")

if st.button("Search") and query:
    params = {"api_key": API_KEY, "query": query, "pageSize": 20}
    r = requests.get(SEARCH_URL, params=params)
    if r.status_code != 200:
        st.error("Search failed.")
    else:
        results = r.json().get("foods", [])
        # filter out foods with no category
        filtered = [f for f in results if f.get("foodCategory")]
        if not filtered:
            st.warning("No foods with categories found.")
            st.session_state.results = {}
        else:
            st.session_state.results = {
                f["description"]: f["fdcId"] for f in filtered
            }
            st.success(f"Found {len(st.session_state.results)} foods with categories!")

# --- DROPDOWN (persists after search) ---
if st.session_state.results:
    sel_desc = st.selectbox(
        "Pick a food",
        list(st.session_state.results.keys()),
        key="food_picker"
    )
    st.session_state.selected = sel_desc

# --- DETAILS ---
if st.session_state.selected:
    if st.button("Show details"):
        fdc_id = st.session_state.results[st.session_state.selected]
        d = requests.get(DETAIL_URL.format(fdc_id), params={"api_key": API_KEY})
        if d.status_code == 200:
            detail = d.json()
            st.json({
                "description": detail.get("description"),
                "fdcId": detail.get("fdcId"),
                "foodCategory": detail.get("foodCategory"),
                "servingSize": detail.get("servingSize"),
                "servingSizeUnit": detail.get("servingSizeUnit"),
            })
        else:
            st.error("Failed to fetch details.")
