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
    "piece", "pieces", "can", "bottle", "link",
    "patty", "bar", "cookie", "egg", "loaf",
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
    "serving", 
    "container"
]

def _fmt_decimal(x):
    # format numbers like 1.0 -> "1", 0.25 -> "0.25", 1.25 -> "1.25"
    if float(x).is_integer():
        return str(int(x))
    return f"{x:.2f}".rstrip("0").rstrip(".")

def pick_fractional_serving(food_row, target_cal):
    kcal_row = nutrients_df[nutrients_df["food_code"] == food_row["food_code"]]
    if kcal_row.empty:
        # no kcal info — fallback
        return 1, "g", 0, 0
    kcal_per_100g = kcal_row.iloc[0]["energy_kcal"]
    if pd.isna(kcal_per_100g) or kcal_per_100g == 0:
        return 1, "g", 0, 0
    kcal_per_g = kcal_per_100g / 100.0

    # gather usable portions (common named units, excluding bad phrases)
    portion_rows = portions_df[portions_df["food_code"] == food_row["food_code"]]
    usable_portions = []
    for _, row in portion_rows.iterrows():
        desc = str(row.get("portion_description", "")).lower()
        if any(u in desc for u in COMMON_UNITS) and not any(bad in desc for bad in BAD_PHRASES):
            usable_portions.append(row)

    # if no named unit portions, fallback to grams sized to hit target_cal
    if not usable_portions:
        grams_for_target = max(1, round(target_cal / kcal_per_g))
        kcal_for_target = round(grams_for_target * kcal_per_g)
        return grams_for_target, "g", grams_for_target, kcal_for_target

    # test 0.25-step fractions from 0.25 to 4.0 for all usable portions, pick the best match
    best = None
    for _, row in pd.DataFrame(usable_portions).iterrows():
        part_grams = row["portion_weight_g"]
        kcal_per_portion = part_grams * kcal_per_g
        # check 0.25..4.0
        for f in [i * 0.25 for i in range(1, 17)]:
            kcal_est = f * kcal_per_portion
            diff = abs(kcal_est - target_cal)
            if best is None or diff < best[0]:
                best = (diff, row, f, kcal_per_portion, part_grams, kcal_est)

    # Defensive fallback if nothing found
    if best is None:
        grams_for_target = max(1, round(target_cal / kcal_per_g))
        kcal_for_target = round(grams_for_target * kcal_per_g)
        return grams_for_target, "g", grams_for_target, kcal_for_target

    _, chosen_row, fraction, kcal_per_portion, part_grams, kcal_est = best

    # compute exact fraction that would match the target for this portion
    exact_fraction = target_cal / kcal_per_portion if kcal_per_portion > 0 else float("inf")

    # If exact_fraction is < 0.25 (i.e., we'd need less than 0.25 of this unit),
    # or the resulting kcal for the chosen rounded fraction is outside the acceptable window (±20%),
    # then FALL BACK to grams so one serving ~ target_cal.
    approx_cal = round(kcal_est)
    if exact_fraction < 0.25 or (approx_cal < 0.8 * target_cal or approx_cal > 1.2 * target_cal):
        grams_for_target = max(1, round(target_cal / kcal_per_g))
        kcal_for_target = round(grams_for_target * kcal_per_g)
        return grams_for_target, "g", grams_for_target, kcal_for_target

    # Otherwise format the chosen unit cleanly:
    raw_desc = str(chosen_row.get("portion_description", "")).lower().strip()
    # strip any leading numeric tokens like "1 ", "0.25 ", "one " etc.
    unit = re.sub(r"^[\d\s\/\.]+", "", raw_desc).strip()
    if unit == "":
        unit = "unit"

    grams_per_serving = max(1, round(fraction * part_grams))
    kcal_per_serving = max(0, round(kcal_est))

    # return: fraction (numeric amount of unit per one serving), unit (e.g. 'cup' or 'g'),
    # grams for that one serving, kcal for that one serving
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
        if st.session_state.energy_servings < 0:
            st.session_state.energy_servings = 0
    else:
        st.session_state.nutrient_servings += amount
        if st.session_state.nutrient_servings < 0:
            st.session_state.nutrient_servings = 0

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
                if st.session_state.show_calories:
                    display_serving = f"{total_grams} g (~{total_kcal} kcal)"
                else:
                    display_serving = f"{total_grams} g"
            else:
                total_units = fraction * amt
                total_units_str = _fmt_decimal(total_units)
                # pluralize unit when >1
                unit_adj = unit if (float(total_units) == 1) else (unit + "s" if not unit.endswith("s") else unit)
                if st.session_state.show_calories:
                    display_serving = f"{total_units_str} {unit_adj} (≈{total_grams} g, ~{total_kcal} kcal)"
                else:
                    display_serving = f"{total_units_str} {unit_adj} (≈{total_grams} g)"

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
    amt = st.selectbox(
        "Serving increment",
        [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
        index=3,
        key="energy_inc",
    )
    if st.button("⚡ Add Energy ⚡"):
        add_serving("Energy-dense", amt)
        st.rerun()
with col2:
    amt = st.selectbox(
        "Serving increment ",
        [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
        index=3,
        key="nutrient_inc",
    )
    if st.button("🌱 Add Nutrient 🌱"):
        add_serving("Nutrient-dense", amt)
        st.rerun()

# ------------------- Manual subtract section -------------------
st.subheader("Quick Subtract")
col1, col2 = st.columns(2)
with col1:
    amt = st.selectbox(
        "Serving decrement",
        [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
        index=3,
        key="energy_dec",
    )
    if st.button("⚡ Subtract Energy ⚡"):
        add_serving("Energy-dense", -amt)
        st.rerun()
with col2:
    amt = st.selectbox(
        "Serving decrement ",
        [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
        index=3,
        key="nutrient_dec",
    )
    if st.button("🌱 Subtract Nutrient 🌱"):
        add_serving("Nutrient-dense", -amt)
        st.rerun()

# ------------------- Calorie Toggle -------------------
def _toggle_calories():
    st.session_state.show_calories = not st.session_state.get("show_calories of foods while searching", False)
    st.rerun()

if "show_calories" not in st.session_state:
    st.session_state.show_calories = False

st.checkbox(
    "Show calories",
    value=st.session_state.show_calories,
    key="show_calories_checkbox",
    on_change=_toggle_calories,
)
