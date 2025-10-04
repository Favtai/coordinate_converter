import pyproj
import streamlit as st
import folium
import pandas as pd
from streamlit_folium import folium_static

# --- App Title and Introduction ---
st.markdown('<h1 style="text-align:center;">Coordinate Converter 🌐</h1>', unsafe_allow_html=True)
st.text("This is a simple coordinate converter app using pyproj library.")

# --- User Guide Popover ---
with st.popover("User Guide"):
    st.markdown(
        """
        ### Instructions
        1. **Select Source and Target CRS:** Choose the coordinate reference systems for conversion.
        2. **Switch Mode (if needed):** Use the <span style="color:green;"><b>Switch Mode 🔄</b></span> toggle to choose between <b>Single Conversion</b> and <b>Batch (CSV) Conversion</b>.
        3. **Single Conversion:** Enter longitude (X) and latitude (Y) values, then click 'Convert Coordinates' to see the result and map.
        4. **Batch Conversion:** Upload a CSV file with coordinate columns, select the appropriate columns, and download the converted results.
        5. **Download:** For batch conversion, use the download button to save your converted data as a CSV file.
        """,
        unsafe_allow_html=True
    )

# --- Function to Retrieve EPSG Codes ---
@st.cache_data
def get_epsg_codes():
    """
    Retrieves a list of available CRS information from the pyproj database,
    including EPSG codes.

    Returns: dictionary of retrieved EPSG codes based on their names
    """
    crs_info_list = pyproj.database.query_crs_info(auth_name=None, pj_types=None)

    epsg_codes = []
    for info in crs_info_list:
        if info.code and info.auth_name and info.auth_name.lower() == "epsg":
            epsg_codes.append(f"EPSG:{info.code}")

    epsg_codes = set(epsg_codes)  # Removes duplicates

    epsg_dict = dict()
    for EPSGs in epsg_codes:
        epsg_dict.update({pyproj.CRS.from_user_input(EPSGs).name: EPSGs})

    return epsg_dict

# --- Get EPSG Dictionary ---
epsg_dict = get_epsg_codes()

# --- CRS Selection (common to both modes) ---
st.markdown('<h4 ">Select source and target CRS</h4>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
col1.selectbox("Select Source CRS:", options=list(epsg_dict.keys()), key="source_crs")
col2.selectbox("Select Target CRS:", options=list(epsg_dict.keys()), key="target_crs")

# --- Coordinate Conversion Function ---
def coordinate_conv(lon, lat, source_crs_name, target_crs_name, epsg_dict):
    """
    Converts coordinates from source CRS to target CRS using pyproj.
    Accepts scalars or pandas Series for lon and lat.
    """
    source_crs = pyproj.CRS(epsg_dict[source_crs_name])
    target_crs = pyproj.CRS(epsg_dict[target_crs_name])
    transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return x, y

# --- Toggle between Single and Batch Modes ---
st.markdown('<span style="color:green; font-weight:bold; font-size:1.3em;">Toggle between <b>Single Conversion</b> and <b>Batch (CSV) Conversion</b>:</span>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([2,2,2])
col1.markdown('<span style="color:cyan; font-weight:bold;"><b>Single Mode</b></span>',  unsafe_allow_html=True)
batch_mode = col2.toggle("🔄 Switch", width= "stretch")
col3.markdown('<span style="color:cyan; font-weight:bold;"><b>Batch Mode</b></span>', unsafe_allow_html=True)

# --- Single Conversion Mode ---
if not batch_mode:
    # Input fields for single coordinate conversion
    col3, col4 = st.columns(2)
    col3.number_input("Enter Longitude (Eastings or X):", format="%0.4f", value=0.0, key="lon")
    col4.number_input("Enter Latitude (Northings or Y):", format="%0.4f", value=0.0, key="lat")

    st.button("Convert Coordinates", key="convert_btn")

    if st.session_state.get("convert_btn"):
        source_crs_name = st.session_state.get("source_crs")
        target_crs_name = st.session_state.get("target_crs")
        lon = st.session_state.get("lon")
        lat = st.session_state.get("lat")

        if source_crs_name and target_crs_name:
            try:
                # Perform coordinate conversion
                x, y = coordinate_conv(lon, lat, source_crs_name, target_crs_name, epsg_dict)
                st.success(f"Conversion successful!")
                lon_col, lat_col = st.columns(2)
                lon_col.metric("Converted Longitude (X):", f"{x:.4f}")
                lat_col.metric("Converted Latitude (Y):", f"{y:.4f}")

                st.text(f"Map View of Converted Coordinates from {epsg_dict[source_crs_name]} to {epsg_dict[target_crs_name]}")

                # Always convert to WGS84 for plotting on Folium map
                wgs84 = pyproj.CRS("EPSG:4326")
                to_wgs84 = pyproj.Transformer.from_crs(pyproj.CRS(epsg_dict[target_crs_name]), wgs84, always_xy=True)
                plot_lon, plot_lat = to_wgs84.transform(x, y)

                # Create and display Folium map with marker
                m = folium.Map(location=[plot_lat, plot_lon], zoom_start=5)
                folium.Marker(
                    [plot_lat, plot_lon], popup="P.O.I.", icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(m)

                folium_static(m, width=700, height=500)
            except Exception as e:
                st.error(f"Error in conversion: {e}")
        else:
            st.warning("Please select both source and target CRS.")

# --- Batch (CSV) Conversion Mode ---
else:
    # File uploader for CSV input
    csv_path = st.file_uploader("Upload CSV", type="csv")
    if csv_path is not None:
        df = pd.read_csv(csv_path)
        cols = [None] + df.columns.tolist()

        # Select columns for longitude and latitude
        col1, col2 = st.columns(2)
        lon_col = col1.selectbox("Longitude col (Eastings or X)", cols, key="csv_lon")
        lat_col = col2.selectbox("Latitude col (Northings or Y)", cols, key="csv_lat")
        
        if lon_col is None or lat_col is None:
            st.warning("Please select both Longitude and Latitude columns.")
            st.stop()
        elif lon_col == lat_col:
            st.warning("Longitude and Latitude columns cannot be the same.")
            st.stop()
        else:
            source_crs_name = st.session_state.get("source_crs")
            target_crs_name = st.session_state.get("target_crs")
            if not source_crs_name or not target_crs_name:
                st.warning("Please select both source and target CRS.")
                st.stop()
            # Perform vectorized coordinate conversion for the DataFrame
            df['CONVERTED_X'], df['CONVERTED_Y'] = coordinate_conv(df[lon_col], df[lat_col], source_crs_name, target_crs_name, epsg_dict)
            st.subheader("Converted Coordinates Table")
            st.dataframe(df)
            # Download button for converted data
            st.download_button(
                label="Download Computed Data", data=df.to_csv(index=False),
                file_name="converted_coordinates.csv", mime="text/csv"
            )

# --- Footer ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("Made with ❤️ by [Favour Taiwo](https://linkedin.com/in/favour-taiwo-57232023a/)")