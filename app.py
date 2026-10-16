import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from pyproj import Geod
from shapely.geometry import Polygon
from geopy.geocoders import Nominatim

# Page Configuration
st.set_page_config(
    page_title="Tractor Field & Fuel Cost Calculator",
    page_icon="🚜",
    layout="wide"
)

st.title("🚜 Tractor Field Area & Pricing Calculator")
st.markdown("Calculate fuel consumption, diesel costs, and client quotations with field mapping and hazard detection.")

# --- SIDEBAR: SETTINGS & RATES ---
st.sidebar.header("⚙️ Pricing & Rate Settings")

diesel_price = st.sidebar.number_input(
    "Current Diesel Price (R/L)", 
    value=33.29, 
    step=0.10, 
    format="%.2f"
)

st.sidebar.subheader("Default Fuel Burn Rates (Litres / Hectare)")
burn_rates = {
    "Deep Plowing / Cultivating": st.sidebar.number_input("Plowing (L/ha)", value=18.0, step=0.5),
    "Discing (Secondary Tillage)": st.sidebar.number_input("Discing (L/ha)", value=12.0, step=0.5),
    "Planting / Seeding": st.sidebar.number_input("Planting (L/ha)", value=8.0, step=0.5),
    "Spray / Fertilizer Application": st.sidebar.number_input("Spraying (L/ha)", value=4.0, step=0.5)
}

markup_percentage = st.sidebar.slider(
    "Labor, Tractor Wear & Profit Markup (%)", 
    min_value=10, 
    max_value=100, 
    value=35, 
    step=5
)

# --- MAIN DASHBOARD: FIELD MEASUREMENT ---
st.subheader("1. Field Measurement & Obstacles")
measurement_mode = st.radio(
    "Choose Measurement Method", 
    ["Interactive Map (Draw Field & Hazards)", "Direct Hectares Input", "Length & Width (Rectangular Field)"]
)

hectares = 1.44  # default fallback

if measurement_mode == "Interactive Map (Draw Field & Hazards)":
    st.info("💡 **How to use:** Draw your field boundary using the **Polygon tool**, then use the **Marker (pin)** or **Circle tool** on the left of the map to click and mark trees, rocks, or danger zones inside the field.")
    
    search_query = st.text_input("🔍 Search Location / Town", value="Newcastle KwaZulu-Natal")
    
    map_lat, map_lon = -28.75, 29.93
    zoom_level = 16  # Closer zoom to see trees clearly
    
    if search_query:
        try:
            geolocator = Nominatim(user_agent="tractor_calculator_app")
            location = geolocator.geocode(search_query)
            if location:
                map_lat, map_lon = location.latitude, location.longitude
        except Exception:
            pass

    m = folium.Map(location=[map_lat, map_lon], zoom_start=zoom_level, tiles="Esri.WorldImagery")
    
    draw = Draw(export=False)
    draw.add_to(m)
    
    output = st_folium(m, width=700, height=500)
    
    hectares = 0.0
    obstruction_count = 0
    
    if output and output.get("all_drawings"):
        for drawing in output["all_drawings"]:
            geom_type = drawing["geometry"]["type"]
            
            if geom_type == "Polygon":
                coords = drawing["geometry"]["coordinates"][0]
                geod = Geod(ellps='WGS84')
                poly_lon_lat = [(c[0], c[1]) for c in coords]
                area_result = geod.geometry_area_perimeter(Polygon(poly_lon_lat))
                square_meters = abs(area_result[0])
                hectares = square_meters / 10000.0
            elif geom_type in ["Point", "Circle"]:
                obstruction_count += 1

        if hectares > 0:
            st.success(f"🗺️ Field Area Measured: **{hectares:.2f} hectares** ({hectares * 10000:,.2f} m²)")
        else:
            st.warning("Please draw your field boundary polygon using the polygon tool on the map.")
            hectares = 1.44  # Default fallback
            
        if obstruction_count > 0:
            st.warning(f"⚠️ **Caution:** **{obstruction_count} obstruction(s) / hazard zone(s)** marked in this field (e.g., trees or obstacles). Drive with care!")
        else:
            st.info("ℹ️ Tip: Drop a marker pin on any trees or obstacles so the operator knows they are there.")
    else:
        st.warning("No field drawn yet. Outline your field with the polygon tool and drop pins on trees/hazards.")
        hectares = 1.44

elif measurement_mode == "Direct Hectares Input":
    hectares = st.number_input("Field Size (Hectares)", min_value=0.1, value=1.44, step=0.1)

else:
    col_l, col_w = st.columns(2)
    with col_l:
        length_m = st.number_input("Field Length (meters)", min_value=10.0, value=200.0, step=10.0)
    with col_w:
        width_m = st.number_input("Field Width (meters)", min_value=10.0, value=72.0, step=10.0)
    square_meters = length_m * width_m
    hectares = square_meters / 10000.0
    st.info(f"Calculated Area: **{square_meters:,.2f} m²** ({hectares:.2f} hectares)")

st.markdown("---")

# --- OPERATION DETAILS ---
st.subheader("2. Tractor Operation & Soil Conditions")
col_op1, col_op2 = st.columns(2)

with col_op1:
    selected_operation = st.selectbox("Select Tractor Operation", list(burn_rates.keys()))
    base_rate = burn_rates[selected_operation]

with col_op2:
    soil_condition = st.selectbox(
        "Soil Condition Modifier", 
        ["Normal Loam (1.0x)", "Heavy Clay / Hard Soil (1.2x)", "Sandy / Light Soil (0.9x)"]
    )

modifier = 1.0
if "Heavy" in soil_condition:
    modifier = 1.2
elif "Sandy" in soil_condition:
    modifier = 0.9

adjusted_rate = base_rate * modifier
st.write(f"Updated Fuel Burn Rate: **{adjusted_rate:.1f} L/ha**")

st.markdown("---")

# --- CALCULATIONS ---
total_fuel_litres = hectares * adjusted_rate
total_diesel_cost = total_fuel_litres * diesel_price
markup_amount = total_diesel_cost * (markup_percentage / 100.0)
final_quotation = total_diesel_cost + markup_amount
per_hectare_quote = final_quotation / hectares if hectares > 0 else 0

# --- RESULTS DISPLAY ---
st.subheader("📊 Cost Breakdown & Quotation Summary")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Field Size", f"{hectares:.2f} ha")
m2.metric("Total Fuel Needed", f"{total_fuel_litres:.1f} L")
m3.metric("Diesel Expense", f"R {total_diesel_cost:,.2f}")
m4.metric("Recommended Quote", f"R {final_quotation:,.2f}", delta=f"R {per_hectare_quote:,.2f} / ha")

with st.expander("🔍 View Itemized Financial Breakdown"):
    st.markdown(f"""
    - **Operation Type:** {selected_operation}
    - **Field Area:** {hectares:.2f} ha
    - **Marked Obstructions / Hazards:** {obstruction_count if 'obstruction_count' in locals() else 0} detected
    - **Fuel Consumption Rate:** {adjusted_rate:.2f} Litres per hectare
    - **Total Diesel Required:** {total_fuel_litres:.2f} Litres
    - **Diesel Cost (at R {diesel_price:.2f}/L):** R {total_diesel_cost:,.2f}
    - **Markup ({markup_percentage}% for Operator & Machinery):** R {markup_amount:,.2f}
    - **Final Client Quotation:** **R {final_quotation:,.2f}**
    - **Effective Rate per Hectare:** **R {per_hectare_quote:,.2f} / ha**
    """)