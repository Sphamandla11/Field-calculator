import folium
from folium.plugins import Draw
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
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
    "Measure fields via map, wheel dimensions, or direct input, and calculate"
    " complete quotes for your John Deere 1120."
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
    "Select Operation Type",
    [
        "Combined Full Job (Plow + Disc + Plant)",
        "Plowing",
        "Discing",
        "Planting",
        "Spraying",
    ],
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

markup_pct = st.sidebar.slider("Profit & Labor Markup (%)", 0, 200, 100)

# Minimum charge control for Plowing (tyre wear & mobilization protection)
min_plowing_fee = st.sidebar.number_input(
    "Minimum Plowing Base Fee (R)", value=1600.00, step=100.00
)

# Travel / Transport Fee Settings (Using Total Round-Trip Distance)
st.sidebar.subheader("🚚 Travel & Transport Fee")
travel_rate_per_km = st.sidebar.number_input(
    "Travel Rate (R/km - Total Round Trip)",
    value=50.00,
    step=5.00,
    help="Rate charged per kilometer for the total round-trip distance.",
)

# Main Measurement Modes
mode = st.radio(
    "Select Measurement Method",
    [
        "Rectangular Field (Length & Width in Meters)",
        "Interactive Map (Draw Fields & Trace Road Route)",
        "Direct Hectares & Distance Input",
    ],
    horizontal=True,
)

total_area_hectares = 0.0
distance_km = 0.0
hazard_count = 0
geod = Geod(ellps="WGS84")

# Home Base Coordinates (Utrecht / KZN farm region)
HOME_COORDS = (-27.6585, 30.3323)

if mode == "Rectangular Field (Length & Width in Meters)":
  st.markdown(
      "### 📏 Rectangular Field Dimension Input (Measuring Wheel / Tape)"
  )
  st.info(
      "💡 Enter the measured length and width in meters. The app will"
      " automatically calculate the total square meters and convert it to"
      " hectares!"
  )

  col_m1, col_m2 = st.columns(2)
  with col_m1:
    field_length_m = st.number_input(
        "Field Length (meters)", min_value=1.0, value=187.0, step=1.0
    )
  with col_m2:
    field_width_m = st.number_input(
        "Field Width (meters)", min_value=1.0, value=36.0, step=1.0
    )

  total_area_m2 = field_length_m * field_width_m
  total_area_hectares = total_area_m2 / 10000.0

  st.success(
      f"📐 **Calculated Area:** {field_length_m:,.1f} m × {field_width_m:,.1f} m"
      f" = {total_area_m2:,.2f} m² (**{total_area_hectares:.3f} hectares**)"
  )

  distance_km = st.number_input(
      "Total Round-Trip Travel Distance (km)",
      min_value=0.0,
      value=4.5,
      step=0.5,
  )

elif mode == "Interactive Map (Draw Fields & Trace Road Route)":
  st.markdown("### 🗺️ Interactive Map & Road Tracing")
  st.info(
      "💡 **How to use:** \n"
      "1. Use the **Polygon / Rectangle tools** to measure field boundaries.\n"
      "2. Use the **Line (Polyline) tool** to trace the round-trip road route"
      " from home to the client's farm."
  )

  if "center_lat" not in st.session_state:
    st.session_state.center_lat = HOME_COORDS[0]
  if "center_lon" not in st.session_state:
    st.session_state.center_lon = HOME_COORDS[1]

  search_query = st.text_input(
      "Optional: Quick Town Search (or pan map manually)",
      value="",
      key="search_location_input",
  )
  search_btn = st.button("🔍 Jump to Town", use_container_width=True)

  if search_btn and search_query:
    try:
      geolocator = Nominatim(user_agent="tractor_field_calculator")
      location = geolocator.geocode(search_query)
      if location:
        st.session_state.center_lat = location.latitude
        st.session_state.center_lon = location.longitude
        st.success(f"Jumped to: {location.address}")
      else:
        st.warning("Location not found.")
    except Exception as e:
      st.error(f"Search error: {e}")

  m = folium.Map(
      location=[st.session_state.center_lat, st.session_state.center_lon],
      zoom_start=15,
      tiles=None,
  )

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

  folium.Marker(
      location=HOME_COORDS,
      popup="Home Base (Your Farm)",
      icon=folium.Icon(color="blue", icon="home", prefix="fa"),
  ).add_to(m)

  draw = Draw(
      export=False,
      draw_options={
          "polyline": True,
          "rectangle": True,
          "polygon": True,
          "circle": False,
          "marker": True,
          "circlemarker": False,
      },
      edit_options={"edit": True},
  )
  draw.add_to(m)

  output = st_folium(m, width="100%", height=450, key="map")

  traced_road_km = 0.0
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
      elif g_type == "LineString":
        try:
          coords = geom["coordinates"]
          for i in range(len(coords) - 1):
            pt1 = (coords[i][1], coords[i][0])
            pt2 = (coords[i + 1][1], coords[i + 1][0])
            traced_road_km += geodesic(pt1, pt2).kilometers
        except Exception:
          pass
      elif g_type == "Point":
        hazard_count += 1

  if traced_road_km > 0:
    distance_km = traced_road_km
    st.success(
        f"🚚 **Road Route Traced!** Total Round-Trip Distance: **{distance_km:.1f}"
        " km**"
    )
  else:
    st.info(
        "🛤️ *Tip: Use the Line tool to trace the round-trip road route to the"
        " farm.*"
    )

  st.success(
      f"🌾 **Combined Total Field Area Measured:** {total_area_hectares:.2f}"
      f" hectares ({total_area_hectares * 10000:,.2f} m²)"
  )

else:
  total_area_hectares = st.number_input(
      "Enter Total Field Area (Hectares)", min_value=0.01, value=0.67, step=0.01
  )
  distance_km = st.number_input(
      "Total Round-Trip Travel Distance (km)",
      min_value=0.0,
      value=4.5,
      step=0.5,
  )

# Calculations
min_applied = False
travel_cost = distance_km * travel_rate_per_km

if selected_operation == "Combined Full Job (Plow + Disc + Plant)":
  plow_fuel = (
      total_area_hectares * burn_rates["Plowing"] * modifier_multiplier
  )
  disc_fuel = (
      total_area_hectares * burn_rates["Discing"] * modifier_multiplier
  )
  plant_fuel = (
      total_area_hectares * burn_rates["Planting"] * modifier_multiplier
  )
  total_fuel_litres = plow_fuel + disc_fuel + plant_fuel

  total_diesel_cost = total_fuel_litres * diesel_price
  markup_amount = total_diesel_cost * (markup_pct / 100.0)
  field_quotation = total_diesel_cost + markup_amount

  if field_quotation < min_plowing_fee:
    field_quotation = min_plowing_fee
    min_applied = True

  final_quotation = field_quotation + travel_cost

else:
  base_burn_rate = burn_rates[selected_operation]
  adjusted_burn_rate = base_burn_rate * modifier_multiplier
  total_fuel_litres = total_area_hectares * adjusted_burn_rate
  total_diesel_cost = total_fuel_litres * diesel_price
  markup_amount = total_diesel_cost * (markup_pct / 100.0)

  field_quotation = total_diesel_cost + markup_amount

  if selected_operation == "Plowing" and field_quotation < min_plowing_fee:
    field_quotation = min_plowing_fee
    min_applied = True

  final_quotation = field_quotation + travel_cost

per_hectare_quote = (
    final_quotation / total_area_hectares if total_area_hectares > 0 else 0
)

st.markdown("---")
st.subheader("📊 Operational & Financial Summary")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Field Size", f"{total_area_hectares:.2f} ha")
col2.metric("Total Fuel Needed", f"{total_fuel_litres:.1f} L")
col3.metric("Travel Distance", f"{distance_km:.1f} km (Round Trip)")
col4.metric(
    "Recommended Quote",
    f"R {final_quotation:,.2f}"
    + (" (Min Floor)" if min_applied else ""),
    delta=f"R {per_hectare_quote:,.2f}/ha",
)

with st.expander("🔍 View Itemized Financial Breakdown", expanded=True):
  breakdown_text = f"""
    - **Selected Operation / Package:** {selected_operation}
    - **Total Diesel Required:** {total_fuel_litres:.2f} Litres
    - **Diesel Unit Price:** R {diesel_price:.2f} / Litre
    - **Base Fuel Expense:** R {total_diesel_cost:,.2f}
    - **Profit & Labor Markup ({markup_pct}%):** R {markup_amount:,.2f}
    """
  if min_applied:
    breakdown_text += f"    - **Minimum Plowing Fee Floor:** R {min_plowing_fee:,.2f} applied.\n"
  breakdown_text += f"""    - **Travel & Transport Cost ({distance_km:.1f} km round-trip @ R {travel_rate_per_km:.2f}/km):** R {travel_cost:,.2f}
    - **Final Client Quotation:** **R {final_quotation:,.2f}**
    """
  st.markdown(breakdown_text)
