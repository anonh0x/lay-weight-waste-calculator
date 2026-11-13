import csv
import io
import streamlit as st

st.set_page_config(page_title="Lay Weight and Waste Calculator", page_icon="🧵", layout="centered")
st.title("Lay Weight and Waste Calculator")
st.caption("Apparel & Textile Fabric Estimation Tool · BUFT Project")

COMPOSITIONS = {
    "100% cotton": 5,
    "Cotton / polyester": 3,
    "100% polyester": 1,
    "Viscose / rayon": 6,
    "Linen": 4,
    "Wool": 3,
    "Nylon": 2,
    "Cotton / elastane": 4,
    "Manual / other": None,
}

CUTTING_METHODS = {
    "Straight knife": 1.0,
    "Band knife": 0.8,
    "Round knife": 1.0,
    "Die cutting": 0.5,
    "CNC / auto cutter": 0.3,
    "Laser": 0.2,
}


def inches(value: float, unit: str) -> float:
    """Convert a length to inches."""
    if unit == "yard":
        return value * 36
    if unit == "metre":
        return value / 0.0254
    if unit == "cm":
        return value / 2.54
    return value


st.header("Fabric")
department = st.selectbox("Department", ["Mens", "Womens", "Kids wear"])
gsm = st.number_input("GSM (g/m²)", min_value=0.0, value=180.0, step=1.0)
width = st.number_input("Cuttable width", min_value=0.0, value=60.0, step=0.5)
width_unit = st.selectbox("Width unit", ["inch", "cm"])
composition = st.selectbox("Composition", list(COMPOSITIONS.keys()))
manual_composition = ""
if composition == "Manual / other":
    manual_composition = st.text_input("Enter composition", placeholder="e.g. 95% Cotton, 5% Elastane")

default_shrink = COMPOSITIONS[composition]
shrinkage = st.number_input(
    "Shrinkage (%)",
    min_value=0.0,
    max_value=99.9,
    value=float(default_shrink if default_shrink is not None else 0),
    step=0.5,
)

st.header("Lay and cutting")
size_set = st.selectbox(
    "Size set",
    ["XS", "S", "M", "L", "XL", "XXL", "XXXL", "XS – XXL (full set)"]
    + [str(n) for n in range(0, 81, 2)]
    + ["0 – 80 (full set)"],
)
spread_length = st.number_input("Spreading length", min_value=0.0, value=96.0, step=1.0)
length_unit = st.selectbox("Spreading length unit", ["inch", "yard", "metre"])
plies = st.number_input("Number of plies", min_value=1, value=100, step=1)
efficiency = st.number_input("Marker efficiency (%)", min_value=1.0, max_value=100.0, value=85.0, step=0.5)
cutting_method = st.selectbox("Cutting method", list(CUTTING_METHODS.keys()))
cutting_loss = st.number_input(
    "Cutting loss (%)",
    min_value=0.0,
    value=CUTTING_METHODS[cutting_method],
    step=0.1,
)

allowance_mode = st.selectbox(
    "Shrinkage allowance",
    ["Calculate from shrinkage %", "Enter my own allowance", "No allowance"],
)
allowance_value = 0.0
allowance_unit = "%"
if allowance_mode == "Enter my own allowance":
    allowance_value = st.number_input("Allowance added to each ply", min_value=0.0, value=0.0, step=0.1)
    allowance_unit = st.selectbox("Allowance unit", ["%", "inch", "cm"])

# Convert inputs to a consistent unit system.
width_m = width / 100 if width_unit == "cm" else width * 0.0254
spread_inches = inches(spread_length, length_unit)

if allowance_mode == "Calculate from shrinkage %":
    adjusted_length_inches = spread_inches / (1 - shrinkage / 100)
elif allowance_mode == "Enter my own allowance":
    if allowance_unit == "%":
        adjusted_length_inches = spread_inches * (1 + allowance_value / 100)
    elif allowance_unit == "cm":
        adjusted_length_inches = spread_inches + allowance_value / 2.54
    else:
        adjusted_length_inches = spread_inches + allowance_value
else:
    adjusted_length_inches = spread_inches

adjusted_length_m = adjusted_length_inches * 0.0254
allowance_inches = adjusted_length_inches - spread_inches
allowance_percent = (allowance_inches / spread_inches * 100) if spread_inches else 0.0

st.header("Results")
if gsm <= 0 or width <= 0 or spread_length <= 0:
    st.error("GSM, width, and spreading length must be greater than zero.")
elif allowance_mode == "Calculate from shrinkage %" and shrinkage >= 100:
    st.error("Shrinkage must be below 100%.")
else:
    weight_per_ply = gsm * width_m * adjusted_length_m / 1000
    total_weight = weight_per_ply * plies
    marker_loss_percent = 100 - efficiency
    raw_waste_percent = marker_loss_percent + cutting_loss

    if raw_waste_percent > 100:
        st.warning("Combined marker loss and cutting loss exceeds 100%. Total waste is capped at 100%.")

    total_waste_percent = min(raw_waste_percent, 100.0)
    waste_weight = total_weight * total_waste_percent / 100
    usable_weight = max(0.0, total_weight - waste_weight)
    marker_waste_kg = total_weight * marker_loss_percent / 100
    cutting_waste_kg = total_weight * cutting_loss / 100
    total_length_m = adjusted_length_m * plies

    c1, c2, c3 = st.columns(3)
    c1.metric("Total lay weight", f"{total_weight:,.2f} kg")
    c2.metric("Usable fabric", f"{usable_weight:,.2f} kg")
    c3.metric("Total waste", f"{waste_weight:,.2f} kg", f"{total_waste_percent:,.2f}%", delta_color="inverse")

    usable_pct = max(0.0, 100.0 - total_waste_percent)
    st.write(f"**Fabric Utilization:** {usable_pct:.2f}% usable · {total_waste_percent:.2f}% waste")
    st.progress(min(max(usable_pct / 100.0, 0.0), 1.0))

    st.subheader("Breakdown")
    if allowance_mode == "No allowance":
        allowance_text = "None"
    else:
        allowance_text = f"{allowance_percent:.2f}% · +{allowance_inches:.2f} in per ply"

    comp_display = (
        manual_composition.strip()
        if composition == "Manual / other" and manual_composition.strip()
        else composition
    )

    breakdown = {
        "Department": department,
        "GSM": f"{gsm:.1f} g/m²",
        "Cuttable width": f"{width:.2f} {width_unit}",
        "Composition": comp_display,
        "Size set": size_set,
        "Number of plies": f"{plies}",
        "Cutting method": cutting_method,
        "Shrinkage allowance": allowance_text,
        "Length spread per ply": f"{adjusted_length_inches:.2f} in",
        "Weight per ply": f"{weight_per_ply:.3f} kg",
        "Total fabric length in lay": f"{total_length_m:.1f} m ({total_length_m / 0.9144:.1f} yd)",
        "Total lay weight": f"{total_weight:.2f} kg",
        "Marker loss": f"{marker_loss_percent:.2f}% · {marker_waste_kg:.2f} kg",
        "Cutting loss": f"{cutting_loss:.2f}% · {cutting_waste_kg:.2f} kg",
        "Total waste": f"{total_waste_percent:.2f}% · {waste_weight:.2f} kg",
        "Usable fabric weight": f"{usable_weight:.2f} kg",
    }
    st.table([{"Item": key, "Value": value} for key, value in breakdown.items()])

    # Exportable CSV Report
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["Item", "Value"])
    for key, value in breakdown.items():
        writer.writerow([key, value])

    st.download_button(
        label="📥 Download Calculation Report (CSV)",
        data=csv_buffer.getvalue(),
        file_name="lay_weight_waste_report.csv",
        mime="text/csv",
    )

    st.caption(
        "Formula: weight per ply (kg) = GSM × width (m) × adjusted length (m) ÷ 1000. "
        "Total lay weight = weight per ply × plies. Waste % = (100 − marker efficiency) + cutting loss %. "
        "These estimates depend on the accuracy of the inputs; compare cutting-loss assumptions with factory data."
    )
