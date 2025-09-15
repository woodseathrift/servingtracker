import streamlit as st
import requests
import datetime
import re

# -----------------------
# API KEYS (secrets fallback)
# -----------------------
try:
    NUTRITIONIX_APP_ID = st.secrets["NUTRITIONIX_APP_ID"]
    NUTRITIONIX_APP_KEY = st.secrets["NUTRITIONIX_APP_KEY"]
except Exception:
    # fallback (replace with your keys or keep these if they are yours)
    NUTRITIONIX_APP_ID = "5107911f"
    NUTRITIONIX_APP_KEY = "39b7b779dbafa5fe4ae28af495a3c349"

SEARCH_URL = "https://trackapi.nutritionix.com/v2/search/instant"
NUTRITIONIX_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

headers = {
    "x-app-id": NUTRITIONIX_APP_ID,
    "x-app-key": NUTRITIONIX_APP_KEY,
    "Content-Type": "application/json",
}

# -----------------------
# helpers
# -----------------------
def round_quarter(x):
    return round(x * 4) / 4

def sanitize_key(s: str) -> str:
    if not s:
        return "k"
    return re.sub(r"\W+", "_", s).strip("_").lower()

# -----------------------
# session state init (daily reset)
# -----------------------
today = datetime.date.today().isoformat()
if "day" not in st.session_state or st.session_state.day != today:
    st.session_state.day = today
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.search_results = []   # list of strings
    st.session_state.selected_food_name = None   # the chosen display name
    st.session_state.selected_item = None  # full nutritionix item dict (cached)

st.title("🥗 Serving-based Food Tracker")

# -----------------------
# SEARCH UI
# -----------------------
st.markdown("### Search foods (Nutritionix)")
search_text = st.text_input("Type a food name (e.g. 'cheerios', 'banana')")

if st.button("Search") and search_text:
    r = requests.get(SEARCH_URL, headers=headers, params={"query": search_text})
    if r.status_code != 200:
        st.error("Search failed (Nutritionix). Check API key / rate limits.")
        st.session_state.search_results = []
    else:
        data = r.json()
        common = data.get("common", []) or []
        branded = data.get("branded", []) or []
        options = []

        # pull up to 10 names
        for c in common:
            name = c.get("food_name")
            if name and name not in options:
                options.append(name)
            if len(options) >= 10:
                break
        for b in branded:
            name = b.get("food_name")
            if name and name not in options:
                options.append(name)
            if len(options) >= 10:
                break

        st.session_state.search_results = options
        st.session_state.selected_food_name = options[0] if options else None
        st.session_state.selected_item = None

# --- show dropdown if we have results ---
if st.session_state.search_results:
    sel = st.selectbox(
        "Pick a result to load nutrition for",
        st.session_state.search_results,
        index=0,
        key="search_results_select"
    )
    st.session_state.selected_food_name = sel

    if st.button("Load nutrition for selection"):
        payload = {"query": st.session_state.selected_food_name}
        r2 = requests.post(NUTRITIONIX_URL, headers=headers, json=payload)
        if r2.status_code == 200:
            results = r2.json().get("foods", [])
            if results:
                st.session_state.selected_item = results[0]
            else:
                st.warning("No nutrition info found for that selection.")
        else:
            st.error("Nutrition lookup failed. Try again.")


# -----------------------
# SHOW selected nutrition and add form
# -----------------------
item = st.session_state.selected_item
if item:
    # safe reads with defaults
    name = item.get("food_name", "Unknown").title()
    calories = item.get("nf_calories", 0) or 0
    serving_qty = item.get("serving_qty", 1) or 1
    serving_unit = item.get("serving_unit", "") or "unit"

    st.markdown(f"## {name}")
    st.write(f"Nutritionix: {serving_qty} {serving_unit} = {calories:.0f} kcal")

    # safe food_group check
    food_group = ""
    tags = item.get("tags", {}) or {}
    if tags and "food_group" in tags and tags["food_group"]:
        food_group = str(tags["food_group"]).lower()

    # classify: only fruits & vegetables => nutrient-dense; everything else => energy-dense
    if "fruit" in food_group or "vegetable" in food_group:
        base_serving = 50
        serving_type = "Nutrient-dense"
        lower, upper = 40, 60
    else:
        base_serving = 100
        serving_type = "Energy-dense"
        lower, upper = 80, 120

    # If Nutritionix's serving is already inside the target range, keep it; otherwise rescale
    in_range = (lower <= calories <= upper)
    if in_range or calories == 0:
        adjusted_qty = round_quarter(serving_qty)
    else:
        # compute calories per serving_qty unit (guard divide-by-zero)
        unit_calories = calories / serving_qty if serving_qty != 0 else calories
        if unit_calories <= 0:
            adjusted_qty = round_quarter(serving_qty)
        else:
            needed_qty = base_serving / unit_calories
            adjusted_qty = round_quarter(needed_qty)

    st.info(f"Defined 1 {serving_type} serving ≈ **{adjusted_qty} {serving_unit}** (target {lower}-{upper} kcal)")

    # create a stable key for this food's form
    base_key = sanitize_key(name)

    # form for adding servings (bundles select + submit so rerun is clean)
    with st.form(key=f"form_{base_key}"):
        chosen = st.selectbox(
            "How many servings?",
            [0.25, 0.5, 0.75, 1, 2],
            index=3,
            key=f"select_{base_key}"
        )

        actual_qty = round_quarter(adjusted_qty * chosen)
        st.write(f"→ {chosen} serving(s) = **{actual_qty} {serving_unit}**")

        submitted = st.form_submit_button("Add to tally")
        if submitted:
            if serving_type == "Energy-dense":
                st.session_state.energy_servings += chosen
            else:
                st.session_state.nutrient_servings += chosen
            st.success(f"Added {chosen} {serving_type} serving(s) of {name}")

# -----------------------
# MANUAL ENTRY IN SIDEBAR
# -----------------------
st.sidebar.header("➕ Manual add")
manual_type = st.sidebar.selectbox("Serving type", ["Nutrient-dense", "Energy-dense"])
manual_qty = st.sidebar.selectbox("Servings", [0.25, 0.5, 0.75, 1, 2, 3], index=3)
if st.sidebar.button("Add manual"):
    if manual_type == "Energy-dense":
        st.session_state.energy_servings += manual_qty
    else:
        st.session_state.nutrient_servings += manual_qty
    st.sidebar.success(f"Added {manual_qty} {manual_type} serving(s)")

# -----------------------
# DISPLAY TALLY (rounded to nearest 0.25)
# -----------------------
def display_round_quarter(x):
    return round_quarter(x)

st.sidebar.markdown("### Today's totals")
st.sidebar.write(f"Energy-dense servings: **{display_round_quarter(st.session_state.energy_servings)}**")
st.sidebar.write(f"Nutrient-dense servings: **{display_round_quarter(st.session_state.nutrient_servings)}**")

