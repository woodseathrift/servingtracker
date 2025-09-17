import streamlit as st
import pandas as pd
import datetime
import re

# ------------------- Load Food Data -------------------
@st.cache_data
def load_data():
    foods_df = pd.read_csv("2017-2018 FNDDS At A Glance - Foods and Beverages.csv", skiprows=1)
    nutrients_df = pd.read_csv("2017-2018 FNDDS At A Glance - FNDDS Nutrient Values.csv", skiprows=1)
    portions_df = pd.read_csv("2017-2018 FNDDS At A Glance - Portions and Weights.csv", skiprows=1)

    # Normalize column names
    for df in [foods_df, nutrients_df, portions_df]:
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(r"[()]", "", regex=True)
        )

    return foods_df, nutrients_df, portions_df


# Unpack correctly
foods_df, nutrients_df, portions_df = load_data()

# ------------------- Initialize State -------------------
if "energy_servings" not in st.session_state:
    st.session_state.energy_servings = 0.0
if "nutrient_servings" not in st.session_state:
    st.session_state.nutrient_servings = 0.0
if "date" not in st.session_state:
    st.session_state.date = datetime.date.today()
if "selected_foods" not in st.session_state:
    st.session_state.selected_foods = []
if "clear_search" not in st.session_state:
    st.session_state.clear_search = False
if "food_search" not in st.session_state:
    st.session_state.food_search = ""
if "food_choice" not in st.session_state:
    st.session_state.food_choice = "-- choose a food --"
if "amt_choice" not in st.session_state:
    st.session_state.amt_choice = 1

# reset daily
if st.session_state.date != datetime.date.today():
    st.session_state.energy_servings = 0.0
    st.session_state.nutrient_servings = 0.0
    st.session_state.date = datetime.date.today()
    st.session_state.selected_foods = []

# ------------------- Serving Picker -------------------
COMMON_UNITS = [
    "cup", "cups", "tbsp", "tablespoon", "tablespoons",
    "tsp", "teaspoon", "teaspoons", "slice", "slices",
    "piece", "pieces", "package", "can", "bottle", "link",
    "patty", "bar", "cookie", "egg", "container", "loaf",
    "bun", "muffin", "cake", "donut", "taco", "sandwich",
    "small", "medium", "large"
]

BAD_PHRASES = [
    "guideline amount",
    "as consumed",
    "recipe",
    "per 100",
    "added",
    "on cereal",
    "with milk",
    "per cup of hot cereal",
    "100 calorie",
    "package",
    "serving"
]

def _fmt_decimal(x):
    # format numbers like 1.0 -> "1", 0.25 -> "0.25", 1.25 -> "1.25"
    if float(x).is_integer():
        return str(int(x))
    return f"{x:.2f}".rstrip("0").rstrip(".")

def pick_fractional_serving(food_row, target_cal):
    """
    Return (fraction, unit, grams_per_serving, kcal_per_serving)
    - fraction: numeric amount of `unit` in *one serving* (e.g. 0.25)
      if unit == 'g', fraction is grams (integer)
    - unit: string like 'cup' or 'g'
    - grams_per_serving: integer grams in one serving (rounded)
    - kcal_per_serving: integer kcal in one serving (rounded)
    The chosen serving is the fraction (0.25 step) of one of the known portions
    that gives kcal closest to target_cal.
    """
    kcal_row = nutrients_df[nutrients_df["food_code"] == food_row["food_code"]]
    if kcal_row.empty:
        return 1, "g", 0, 0  # fallback but handled below

    kcal_per_100g = kcal_row.iloc[0]["energy_kcal"]
    if pd.isna(kcal_per_100g) or kcal_per_100g == 0:
        return 1, "g", 0, 0
    kcal_per_g = kcal_per_100g / 100.0

    # get portion rows for this food
    portion_rows = portions_df[portions_df["food_code"] == food_row["food_code"]]
    usable_portions = []
    for _, row in portion_rows.iterrows():
        desc = str(row.get("portion_description", "")).lower()
        if any(u in desc for u in COMMON_UNITS) and not any(bad in desc for bad in BAD_PHRASES):
            usable_portions.append(row)

    # If no suitable common-unit portions, fallback to grams such that 1 serving ~ target_cal
    if not usable_portions:
        grams_for_target = max(1, round(target_cal / kcal_per_g))
        kcal_for_target = round(grams_for_target * kcal_per_g)
        return grams_for_target, "g", grams_for_target, kcal_for_target

    # try all fractions 0.25..4.0 across usable_portions, pick closest kcal to target
    best = None
    for _, row in pd.DataFrame(usable_portions).iterrows():
        portion_grams = row["portion_weight_g"]
        kcal_per_portion = portion_grams * kcal_per_g
        # test fraction multipliers (0.25 .. 4.0)
        for f in [i * 0.25 for i in range(1, 17)]:
            kcal_est = f * kcal_per_portion
            diff = abs(kcal_est - target_cal)
            if best is None or diff < best[0]:
                best = (diff, row, f, kcal_per_portion, portion_grams, kcal_est)

    if best is None:
        # extreme fallback
        grams_for_target = max(1, round(target_cal / kcal_per_g))
        kcal_for_target = round(grams_for_target * kcal_per_g)
        return grams_for_target, "g", grams_for_target, kcal_for_target

    _, chosen_row, fraction, kcal_per_portion, part_grams, kcal_est = best

    # clean unit name (strip leading numeric counts like "1 ", "0.25 ", etc.)
    raw_desc = str(chosen_row.get("portion_description", "")).lower().strip()
    # remove leading numeric tokens (numbers, fractions, decimals)
    unit = re.sub(r"^[\d\s\/\.]+", "", raw_desc).strip()
    if unit == "":
        unit = "unit"

    grams_per_serving = max(1, round(fraction * part_grams))
    kcal_per_serving = max(0, round(kcal_est))

    # if the "unit" we extracted is just a weight word like "g", handle it (rare)
    # Return: fraction (numeric count of unit per serving), unit string, grams_per_serving, kcal_per_serving
    return fraction, unit, grams_per_serving, kcal_per_serving

def serving_for_food(food_row):
    code = str(food_row["food_code"])
    if code.startswith(("61", "63", "67", "72", "73", "74", "75", "76", "78")):
        density = "Nutrient-dense"
        fraction, unit, grams, kcal = pick_fractional_serving(food_row, 50)
    else:
        density = "Energy-dense"
        fraction, unit, grams, kcal = pick_fractional_serving(food_row, 100)
    return density, fraction, unit, grams, kcal

# ------------------- Add Servings -------------------
def add_serving(density_type, amount=1.0):
    if density_type == "Energy-dense":
        st.session_state.energy_servings += amount
    else:
        st.session_state.nutrient_servings += amount

# ------------------- UI -------------------
st.title("🥗 Serving Tracker")

# ------------------- Show tally -------------------
st.subheader("Tally")
col1, col2 = st.columns(2)
with col1:
    st.markdown(
        f"<div style='background-color:#FF6666; color:black; padding:10px; border-radius:8px;'>"
        f"⚡ Energy-dense servings: <b>{st.session_state.energy_servings:.2f}</b></div>",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"<div style='background-color:#66FF66; color:black; padding:10px; border-radius:8px;'>"
        f"🌱 Nutrient-dense servings: <b>{st.session_state.nutrient_servings:.2f}</b></div>",
        unsafe_allow_html=True,
    )

# --- Search bar with inline button (mobile/desktop safe, single version) ---
st.markdown(
    """
    <style>
    .search-wrapper {
        display: flex;
        align-items: stretch;
        max-width: 600px;
        margin-bottom: 1em;
    }
    .search-wrapper > div:first-child {
        flex-grow: 1;
    }
    .search-wrapper > div:last-child {
        flex-shrink: 0;
    }
    div[data-testid="stTextInput"] > div > div > input {
        border-radius: 8px 0 0 8px !important;
    }
    div[data-testid="stButton"] button {
        border-radius: 0 8px 8px 0 !important;
        height: 100%;
        padding: 0.5em 0.75em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container():
    st.markdown('<div class="search-wrapper">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 0.15], gap="small")
    with col1:
        query = st.text_input(
            "Search for a food",
            value="",
            key="food_search",
            label_visibility="collapsed",
        )
    with col2:
        search_clicked = st.button("🔍")
    st.markdown('</div>', unsafe_allow_html=True)

if (query and query.strip()) or search_clicked:
    q = query.strip().lower()
    # --- Word-based search ---
    words = q.split()
    matches = foods_df.copy()
    for w in words:
        matches = matches[matches["main_food_description"].str.contains(w, case=False, na=False)]

    if matches.empty:
        st.warning("⚠️ No foods found. Try a different search term.")
    else:
        options = ["-- choose a food --"] + [
            f'{row["main_food_description"]} (#{row["food_code"]})'
            for _, row in matches.iterrows()
        ]
        choice = st.selectbox("Select a food", options, key="food_choice")

        if choice != "-- choose a food --":
            code = int(choice.split("#")[-1].strip(")"))
            food_row = foods_df[foods_df["food_code"] == code].iloc[0]

            density, fraction, unit, base_grams, base_kcal = serving_for_food(food_row)
            color = "#330000" if density == "Energy-dense" else "#003300"

            amt = st.selectbox(
                "Add servings",
                [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
                index=3,
                key="amt_choice"
            )

            # total grams and kcal scale linearly from the chosen "one serving"
            total_grams = round(base_grams * amt)
            total_kcal = round(base_kcal * amt)

            # display total units in natural decimal form: total_units = fraction * amt
            if unit == "g":
                # fallback grams display
                display_serving = f"{total_grams} g (~{total_kcal} kcal)"
            else:
                total_units = fraction * amt
                total_units_str = _fmt_decimal(total_units)
                # pluralize unit when >1
                unit_adj = unit if (float(total_units) == 1) else (unit + "s" if not unit.endswith("s") else unit)
                display_serving = f"{total_units_str} {unit_adj} (≈{total_grams} g, ~{total_kcal} kcal)"

            st.markdown(
                f"<div style='background-color:{color}; padding:8px; border-radius:8px;'>"
                f"<b>{food_row['main_food_description']}</b><br>{density}: {display_serving}</div>",
                unsafe_allow_html=True,
            )

            if st.button("Add to tally"):
                add_serving(density, amt)
                st.session_state.selected_foods.append({
                    "code": code,
                    "name": food_row["main_food_description"],
                    "density": density,
                    "amt": amt,
                })

                for k in ["food_search", "food_choice", "amt_choice"]:
                    if k in st.session_state:
                        del st.session_state[k]

                st.rerun()

# ------------------- Manual tally section -------------------
st.subheader("Quick Add")
col1, col2 = st.columns(2)
with col1:
    amt = st.selectbox("Serving increment", [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2], index=3, key="energy_inc")
    if st.button("⚡ Add Energy ⚡"):
        add_serving("Energy-dense", amt)
with col2:
    amt = st.selectbox("Serving increment", [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2], index=3, key="nutrient_inc")
    if st.button("🌱 Add Nutrient 🌱"):
        add_serving("Nutrient-dense", amt)
