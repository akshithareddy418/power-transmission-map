
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Power Transmission Map",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Power Transmission Route Map")
st.subheader("Power Generation to Gurralagondi Village, Siddipet")

st.info(
    "This dashboard reads station locations and connections from CSV files. "
    "Only verified routes should be treated as actual grid connections."
)

# CSV file paths
BASE_DIR = Path(__file__).parent
STATIONS_FILE = BASE_DIR / "stations.csv"
ROUTES_FILE = BASE_DIR / "routes.csv"


def normalize_columns(df):
    df.columns = [
        str(c).strip().lower().replace(" ", "_")
        for c in df.columns
    ]
    return df


def find_column(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None


try:
    stations = normalize_columns(pd.read_csv(STATIONS_FILE))
    routes = normalize_columns(pd.read_csv(ROUTES_FILE))

    # Recognize common column names
    id_col = find_column(
        stations, ["station_id", "id", "station_code"]
    )
    name_col = find_column(
        stations, ["station_name", "name", "station"]
    )
    lat_col = find_column(
        stations, ["latitude", "lat"]
    )
    lon_col = find_column(
        stations, ["longitude", "lon", "lng", "long"]
    )

    if not all([id_col, name_col, lat_col, lon_col]):
        st.error(
            "Please check stations.csv. It needs columns for "
            "station ID, station name, latitude and longitude."
        )
        st.write("Columns currently found:", list(stations.columns))
        st.stop()

    # Convert coordinates to numeric values
    stations[lat_col] = pd.to_numeric(
        stations[lat_col], errors="coerce"
    )
    stations[lon_col] = pd.to_numeric(
        stations[lon_col], errors="coerce"
    )
    stations = stations.dropna(subset=[lat_col, lon_col])

    # Map display
    st.markdown("### Transmission Network Map")

    if stations.empty:
        st.warning("No valid station coordinates were found.")
        st.stop()

    center_lat = stations[lat_col].mean()
    center_lon = stations[lon_col].mean()

    power_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles="OpenStreetMap"
    )

    # Add station markers
    for _, station in stations.iterrows():
        details = (
            f"<b>{station[name_col]}</b><br>"
            f"Station ID: {station[id_col]}<br>"
            f"Latitude: {station[lat_col]}<br>"
            f"Longitude: {station[lon_col]}"
        )

        folium.Marker(
            location=[station[lat_col], station[lon_col]],
            tooltip=str(station[name_col]),
            popup=folium.Popup(details, max_width=300),
            icon=folium.Icon(
                color="blue",
                icon="flash",
                prefix="fa"
            )
        ).add_to(power_map)

    # Draw connections from routes.csv
    from_col = find_column(
        routes, ["from_id", "from_station", "source_id"]
    )
    to_col = find_column(
        routes, ["to_id", "to_station", "destination_id"]
    )

    if from_col and to_col:
        station_lookup = stations.set_index(
            stations[id_col].astype(str)
        )

        for _, route in routes.iterrows():
            start_id = str(route[from_col])
            end_id = str(route[to_col])

            if (
                start_id not in station_lookup.index
                or end_id not in station_lookup.index
            ):
                continue

            start = station_lookup.loc[start_id]
            end = station_lookup.loc[end_id]

            if isinstance(start, pd.DataFrame):
                start = start.iloc[0]
            if isinstance(end, pd.DataFrame):
                end = end.iloc[0]

            status_col = find_column(
                routes, ["route_status", "status"]
            )
            status = (
                str(route[status_col])
                if status_col else "Unverified"
            )

            voltage_col = find_column(
                routes, ["voltage_kv", "voltage", "kv"]
            )
            voltage = (
                str(route[voltage_col])
                if voltage_col else "Not specified"
            )

            color = (
                "green"
                if "verified" in status.lower()
                and "unverified" not in status.lower()
                else "orange"
            )

            folium.PolyLine(
                locations=[
                    [start[lat_col], start[lon_col]],
                    [end[lat_col], end[lon_col]]
                ],
                color=color,
                weight=4,
                tooltip=(
                    f"{start[name_col]} → {end[name_col]} | "
                    f"{voltage} kV | {status}"
                )
            ).add_to(power_map)

    st_folium(
        power_map,
        use_container_width=True,
        height=550
    )

    st.markdown("### Station Details")
    st.dataframe(stations, use_container_width=True)

    st.markdown("### Route Details")
    st.dataframe(routes, use_container_width=True)

    st.caption(
        "Straight lines connect station coordinates for visualization. "
        "They do not represent the exact physical transmission-line path."
    )

except FileNotFoundError as error:
    st.error(f"CSV file not found: {error.filename}")
    st.info(
        "Make sure stations.csv and routes.csv are saved "
        "in the same folder as app.py."
    )
except Exception as error:
    st.error(f"An error occurred: {error}")
