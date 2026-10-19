from geopy.geocoders import Nominatim
import folium
from folium.plugins import Draw
from pyproj import Geod
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Field Calculator - John Deere 1120",
    page_icon="🚜",
    layout="wide",
)

st.title("🚜 Tractor Field & Fuel Cost Calculator")
st.markdown(
    "Measure multiple field parcels, log hazards, and calculate precise"
    " operational costs for your John Deere 1120."
)

# Sidebar Settings
st.sidebar.header("⚙️ Pricing & Rate Settings")
diesel_price = st.sidebar.number_input(
    "Diesel Price (R/L)", value=33.50, step=0.50
)

st.sidebar.subheader("Default Fuel Burn Rates (Litres / Hectare)")
burn_rates = {
    "Plowing": st.sidebar.number_input("Plowing (L/ha)", value=25.0),
    "Discing": st.sidebar.number_input("Discing (L/ha)", value=12.0),
    "Planting": st.sidebar.number_input("Planting (L/ha)", value=8.0),
    "Spraying": st.sidebar.number_input("Spraying (L/ha)", value=4.5),
}

selected_operation = st.sidebar.selectbox(
    "Select Operation Type", list(burn_rates.keys())
)

soil_modifier = st.sidebar.selectbox(
    "Soil / Terrain Condition",
    [
        "Normal (1.0x)",
        "Hard / Dry (+25%)",
        "Heavy Clay / Hard Soil (+40%)",
        "Rocky / Sloped (+50%)",
    ],
)

modifier_multiplier = 1.0
if "Hard / Dry" in soil_modifier:
  modifier_multiplier = 1.25
elif "Heavy Clay" in soil_modifier:
  modifier_multiplier = 1.40
elif "Rocky / Sloped" in soil_modifier:
  modifier_multiplier = 1.50

markup_pct = st.sidebar.slider("Profit & Labor Markup (%)", 0, 100, 50)

# Minimum charge control for Plowing (tyre wear & mobilization protection)
min_plowing_fee = 1600.00
if selected_operation == "Plowing":
  min_plowing_fee = st.sidebar.number_input(
      "Minimum Plowing Base Fee (R)", value=1600.00, step=100.00
  )

# Main Measurement Modes
mode = st.radio(
    "Select Measurement Method",
    [
        "Interactive Map (Draw Multiple Fields)",
        "Direct Hectares Input",
        "Length & Width (Rectangular Field)",
    ],
    horizontal=True,
)

total_area_hectares = 0.0
hazard_count = 0

geod = Geod(ellps="WGS84")

if mode == "Interactive Map (Draw Multiple Fields)":
  st.markdown("### 🗺️ Interactive Field Mapping")
  st.info(
      "💡 **Tip:** Draw multiple field polygons using the polygon tool on the"
      " left side of the map. The app will automatically combine all drawn"
      " fields into one total quote!"
  )

  # Initialize map center in session state so it doesn't reset while drawing
  if "center_lat" not in st.session_state:
    st.session_state.center_lat = -27.6585
  if "center_lon" not in st.session_state:
    st.session_state.center_lon = 30.3323

  # Mobile-friendly stacked search layout
  search_query = st.text_input(
      "Search Location / Town",
      value="Utrecht KwaZulu-Natal",
      key="search_location_input",
  )
  search_btn = st.button("🔍 Search Location", use_container_width=True)

  if search_btn and search_query:
    try:
      geolocator = Nominatim(user_agent="tractor_field_calculator")
      location = geolocator.geocode(search_query)
      if location:
        st.session_state.center_lat = location.latitude
        st.session_state.center_lon = location.longitude
        st.success(f"Found: {location.address}")
      else:
        st.warning("Location not found. Showing current area.")
    except Exception as e:
      st.error(f"Search error: {e}")

  # Create Folium Map using persistent session state coordinates
  m = folium.Map(
      location=[st.session_state.center_lat, st.session_state.center_lon],
      zoom_start=16,
      tiles=None,
  )

  # Add Esri Satellite Imagery
  folium.TileLayer(
      tiles=(
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
      ),
      attr=(
          "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX,"
          " GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User"
          " Community"
      ),
      name="Esri Satellite",
      max_zoom=19,
  ).add_to(m)

  # Add Drawing Tools
  draw = Draw(
      export=False,
      draw_options={
          "polyline": False,
          "rectangle": True,
          "polygon": True,
          "circle": False,
          "marker": True,
          "circlemarker": False,
      },
      edit_options={"edit": True},
  )
  draw.add_to(m)

  # Render Map in Streamlit
  output = st_folium(m, width="100%", height=450, key="map")

  # Process Map Drawings and Combine Areas
  if output and "all_drawings" in output and output["all_drawings"]:
    for drawing in output["all_drawings"]:
      geom = drawing.get("geometry", {})
      g_type = geom.get("type")

      if g_type == "Polygon":
        try:
          coords = geom["coordinates"][0]
          lons = [c[0] for c in coords]
          lats = [c[1] for c in coords]
          area_m2, _ = geod.polygon_area_perimeter(lons, lats)
          total_area_hectares += abs(area_m2) / 10000.0
        except Exception:
          pass
      elif g_type == "Point":
        hazard_count += 1

  st.success(
      f"🌾 **Combined Total Field Area Measured:** {total_area_hectares:.2f}"
      f" hectares ({total_area_hectares * 10000:,.2f} m²)"
  )
  if hazard_count > 0:
    st.warning(
        f"⚠️ **Logged Hazards / Obstacles:** {hazard_count} marker(s) detected"
        " on map."
    )

elif mode == "Direct Hectares Input":
  total_area_hectares = st.number_input(
      "Enter Total Field Area (Hectares)", min_value=0.01, value=5.0, step=0.1
  )

else:
  col_l, col_w = st.columns(2)
  with col_l:
    length_m = st.number_input(
        "Field Length (meters)", min_value=1.0, value=200.0
    )
  with col_w:
    width_m = st.number_input(
        "Field Width (meters)", min_value=1.0, value=100.0
    )
  total_area_hectares = (length_m * width_m) / 10000.0
  st.info(f"Calculated Area: {total_area_hectares:.2f} hectares")

# Calculations
base_burn_rate = burn_rates[selected_operation]
adjusted_burn_rate = base_burn_rate * modifier_multiplier
total_fuel_litres = total_area_hectares * adjusted_burn_rate
total_diesel_cost = total_fuel_litres * diesel_price
markup_amount = total_diesel_cost * (markup_pct / 100.0)
final_quotation = total_diesel_cost + markup_amount

# Apply Minimum Plowing Rule if selected
min_applied = False
if selected_operation == "Plowing" and final_quotation < min_plowing_fee:
  final_quotation = min_plowing_fee
  min_applied = True

per_hectare_quote = (
    final_quotation / total_area_hectares if total_area_hectares > 0 else 0
)

st.markdown("---")
st.subheader("📊 Operational & Financial Summary")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Field Size", f"{total_area_hectares:.2f} ha")
col2.metric("Fuel Needed", f"{total_fuel_litres:.1f} L")
col3.metric("Diesel Expense", f"R {total_diesel_cost:,.2f}")
col4.metric(
    "Recommended Quote",
    f"R {final_quotation:,.2f}"
    + (" (Min Floor)" if min_applied else ""),
    delta=f"R {per_hectare_quote:,.2f}/ha",
)

with st.expander("🔍 View Itemized Financial Breakdown"):
  min_note = (
      f"- **Minimum Plowing Fee Floor:** R {min_plowing_fee:,.2f} applied to"
      " protect equipment & tyre wear."
      if min_applied
      else ""
  )
  st.markdown(f"""
    - **Operation Type:** {selected_operation}
    - **Base Burn Rate:** {base_burn_rate} L/ha
    - **Terrain/Soil Modifier:** {soil_modifier} (Multiplier: {modifier_multiplier}x)
    - **Effective Burn Rate:** {adjusted_burn_rate:.2f} L/ha
    - **Total Diesel Required:** {total_fuel_litres:.2f} Litres
    - **Diesel Cost Rate:** R {diesel_price:.2f} / Litre
    - **Base Fuel Expense:** R {total_diesel_cost:,.2f}
    - **Profit & Labor Markup ({markup_pct}%):** R {markup_amount:,.2f}
    {min_note}
    - **Final Client Quotation:** R {final_quotation:,.2f}
    """)