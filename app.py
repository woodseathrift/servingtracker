# streamlit_usda_fped.py
import streamlit as st
import requests
import pandas as pd

# ---------- CONFIG ----------
FDC_API_KEY = "HvgXfQKOj8xIz3vubw8K87mOrankyf22ld4dHnAS"  # replace with your key if needed
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
DETAIL_URL = "https://api.nal.usda.gov/fdc/v1/food/{}"

FPED_PATH = "FPED_1718.csv"  # must exist in your repo (converted from .xls -> .csv)

# ---------- HELPERS ----------
@st.cache_data
def load_fped(path=FPED_PATH):
    df = pd.read_csv(path)
    # normalize column names
    df.columns = df.columns.str.strip().str.lower()
    # ensure food_code column is int if present
    if "food_code" in df.columns:
        df["food_code"] = pd.to_numeric(df["food_code"], errors="coerce").astype("Int64")
    return df

@st.cache_data
def fdc_search(q: str, page_size: int = 30):
    params = {
        "api_key": FDC_API_KEY,
        "query": q,
        "pageSize": page_size,
        "dataType": ["Foundation", "SR Legacy"],  # prefer datasets that map to FPED
    }
    r = requests.get(SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("foods", [])

@st.cache_data
def fdc_detail(fdc_id: int):
    r = requests.get(DETAIL_URL.format(fdc_id), params={"api_key": FDC_API_KEY}, timeout=30)
    r.raise_for_status()
    return r.json()

def find_fped_row_for_foodcode(fped_df: pd.DataFrame, food_code):
    if food_code is None:
        return pd.DataFrame()
    try:
        code_int = int(food_code)
    except Exception:
        return pd.DataFrame()
    if "food_code" not in fped_df.columns:
        return pd.DataFrame()
    return fped_df.loc[fped_df["food_code"] == code_int]

def fped_has_fruit_or_veg(row: pd.Series):
    # heuristically find FPED columns related to fruit/vegetable
    cols = row.index.tolist()
    fruit_cols = [c for c in cols if "fruit" in c and not c.endswith("_source")] 
    veg_cols = [c for c in cols if ("vegetab" in c) or ("veg" in c and "veg" in c)]
    # fallback common names
    fallback_fruit = [c for c in cols if "total_fruit" in c or "fruit_cup" in c or "total_fruits" in c]
    fallback_veg = [c for c in cols if "total_vegetable" in c or "vegetable" in c or "veg_cup" in c]
    if not fruit_cols:
        fruit_cols = list(set(fruit_cols + fallback_fruit))
    if not veg_cols:
        veg_cols = list(set(veg_cols + fallback_veg))
    # sum available columns (tolerant if some are missing)
    fruit_sum = 0.0
    veg_sum = 0.0
    for c in fruit_cols:
        try:
            fruit_sum += float(row.get(c, 0) or 0)
        except Exception:
            pass
    for c in veg_cols:
        try:
            veg_sum += float(row.get(c, 0) or 0)
        except Exception:
            pass
    return (fruit_sum > 0) or (veg_sum > 0), fruit_sum, veg_sum, fruit_cols, veg_cols

def extract_energy_per_100g(detail_json):
    # FDC often lists nutrients with a 'nutrientName' / 'name' field; try to find energy (kcal)
    for n in detail_json.get("foodNutrients", []):
        # different formats exist in FDC responses – check several keys safely
        name = n.get("nutrient", {}).get("name") or n.get("nutrientName") or n.get("name") or ""
        if name and "energy" in name.lower():
            # amount is usually per 100 g for Foundation/SR foods
            amt = n.get("amount") or n.get("value")
            if amt is not None:
                try:
                    return float(amt)
                except Exception:
                    pass
    # fallback: try top-level 'labelNutrients' or 'nutrients' (unlikely for Foundation)
    return None

# ---------- APP ----------
st.set_page_config(page_title="USDA → FPED Classifier", layout="wide")
st.title("🥗 USDA → FPED classifier (fruit/veg → nutrient-dense)")

fped = load_fped()

# show which FPED columns look like fruit/veg to help debugging
if st.checkbox("Show FPED columns (debug)"):
    st.write(fped.columns.tolist())

query = st.text_input("Search for a food (e.g. 'apple', 'raw apple')")

# make results persistent
if "search_results" not in st.session_state:
    st.session_state.search_results = []

if st.button("Search") and query:
    with st.spinner("Searching USDA..."):
        try:
            search_hits = fdc_search(query, page_size=40)
        except Exception as e:
            st.error(f"Search error: {e}")
            search_hits = []

        # For each hit, attempt to find a foodCode -> then try match to FPED
        matches = []
        for hit in search_hits:
            # prefer foodCode in the search hit if present
            food_code = hit.get("foodCode")
            fdc_id = hit.get("fdcId")
            if not food_code and fdc_id:
                # fetch detail to get foodCode (some entries only expose in detail)
                try:
                    detail = fdc_detail(fdc_id)
                    food_code = detail.get("foodCode") or detail.get("food_code")
                except Exception:
                    food_code = None
            if not food_code:
                # can't map to FPED without a food_code → skip
                continue
            # check FPED
            row = find_fped_row_for_foodcode(fped, food_code)
            if row.empty:
                continue
            # crop to a single row (food_code unique)
            row_series = row.iloc[0]
            has_fv, fruit_sum, veg_sum, fruit_cols, veg_cols = fped_has_fruit_or_veg(row_series)
            classification = "Nutrient-dense" if has_fv else "Energy-dense"
            matches.append({
                "description": hit.get("description"),
                "fdcId": fdc_id,
                "foodCode": int(food_code),
                "classification": classification,
                "fped_row": row_series,
                "fruit_sum": fruit_sum,
                "veg_sum": veg_sum
            })

        if not matches:
            st.warning("No searchable USDA foods could be linked to FPED (no food_code → no FPED match).")
            st.session_state.search_results = []
        else:
            st.session_state.search_results = matches

# show dropdown if we have matches
if st.session_state.search_results:
    labels = [
        f"{m['description']} — {m['classification']} (FNDDS {m['foodCode']})"
        for m in st.session_state.search_results
    ]
    sel = st.selectbox("Pick an FPED-mapped food", labels, key="fped_picker")
    if sel:
        idx = labels.index(sel)
        item = st.session_state.search_results[idx]
        st.subheader(item["description"])
        st.write("**FNDDS food code:**", item["foodCode"])
        st.write("**Classification (FPED fruit/veg > 0):**", item["classification"])
        st.write(f"FPED fruit cup eq sum: {item['fruit_sum']}, veg cup eq sum: {item['veg_sum']}")

        # show the FPED row (transpose for readability)
        st.subheader("FPED row (matched)")
        st.dataframe(item["fped_row"].to_frame().T)

        # show grams needed for target calories (default 100 kcal)
        target_cal = st.number_input("Target calories for 1 serving", value=100.0, step=10.0)
        # fetch detail for nutrient info
        try:
            detail = fdc_detail(item["fdcId"])
            cal_per_100g = extract_energy_per_100g(detail)
            if cal_per_100g and cal_per_100g > 0:
                grams_needed = target_cal * 100.0 / cal_per_100g
                st.write(f"**{grams_needed:.0f} g** of this food ≈ **{target_cal:.0f} kcal** (cal per 100g = {cal_per_100g:.1f})")
            else:
                st.info("Could not find energy (kcal) in the USDA detail. FPED mapping exists but nutrient energy not available.")
        except Exception as e:
            st.error(f"Failed to fetch detail: {e}")

# small note
st.markdown("---")
st.write("Notes: this app requires FNDDS food codes present in FDC results (some items won't include them). FPED is matched by `food_code` and we classify as nutrient-dense when FPED reports >0 fruit or vegetable equivalents per 100 g.")
