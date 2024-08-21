import streamlit as st
from streamlit_js_eval import get_geolocation
import mygeotab
import folium
from streamlit_folium import folium_static
from shapely.geometry import Point, Polygon

# Set page configuration - This should be the first Streamlit command
st.set_page_config(layout="wide")


# Initialize session state for location and selected tab
if 'user_lat' not in st.session_state:
    st.session_state['user_lat'] = None
if 'user_lon' not in st.session_state:
    st.session_state['user_lon'] = None
if 'current_tab' not in st.session_state:
    st.session_state['current_tab'] = None

# Authentication with Geotab
database = 'nycsbus'
server = 'afmfe.att.com'
geotab_username = st.secrets["geotab_username"]
geotab_password = st.secrets["geotab_password"]
api = mygeotab.API(username=geotab_username, password=geotab_password, database=database, server=server)

try:
    api.authenticate()
    st.write("Successfully authenticated with Geotab.")

    # List all devices
    devices = api.get('Device')
    st.write("List of devices:", devices)

    # Optionally, you can filter devices based on some criteria to narrow down
    filtered_devices = [device for device in devices if '1733' in device['name']]
    st.write("Filtered devices (by ID or name containing '1733'):", filtered_devices)

except mygeotab.exceptions.AuthenticationException:
    st.error("Authentication failed!")


# Function to get user location using streamlit_js_eval
def get_user_location():
    location = get_geolocation()
    if location:
        st.session_state['user_lat'] = location['coords']['latitude']
        st.session_state['user_lon'] = location['coords']['longitude']
        st.write(f"Current location: ({st.session_state['user_lat']}, {st.session_state['user_lon']})")
    else:
        st.warning("Failed to retrieve location. Please enter your location manually below.")
        manual_lat = st.number_input("Latitude", format="%.6f")
        manual_lon = st.number_input("Longitude", format="%.6f")
        if st.button("Set Manual Location"):
            st.session_state['user_lat'] = manual_lat
            st.session_state['user_lon'] = manual_lon
            st.write(f"Manual location set: ({st.session_state['user_lat']}, {st.session_state['user_lon']})")

get_user_location()

# Function to check if a point is within a polygon
def is_within_bounds(lat, lon, bounds):
    polygon = Polygon(bounds)
    point = Point(lon, lat)
    return polygon.contains(point)

# Define boundaries for Greenpoint and Zerega
greenpoint_bounds = [
    [-73.94226338858698, 40.72931657250524],
    [-73.94226338858698, 40.72698871645508],
    [-73.93862947535852, 40.72698871645508],
    [-73.93862947535852, 40.72931657250524]
]

zerega_bounds = [
    [-73.84305114100036, 40.829178521810235],
    [-73.84305114100036, 40.83253559646761],
    [-73.84929847524617, 40.83253559646761],
    [-73.84929847524617, 40.829178521810235]
]

# Function to switch to the appropriate tab based on user location
def switch_to_nearest_tab():
    if st.session_state['user_lat'] and st.session_state['user_lon']:
        if is_within_bounds(st.session_state['user_lat'], st.session_state['user_lon'], greenpoint_bounds):
            st.session_state['current_tab'] = 'Greenpoint'
        elif is_within_bounds(st.session_state['user_lat'], st.session_state['user_lon'], zerega_bounds):
            st.session_state['current_tab'] = 'Zerega'
        else:
            st.warning("You are not within any defined bus yard boundaries.")

switch_to_nearest_tab()

# Function to display bus location on a map
def display_bus_location():
    vehicle_id = st.text_input("Enter Vehicle ID", placeholder="Vehicle ID")
    
    if st.button("Show Bus Location"):
        if vehicle_id:
            # Authentication with Geotab
            database = 'nycsbus'
            server = 'afmfe.att.com'
            geotab_username = st.secrets["geotab_username"]
            geotab_password = st.secrets["geotab_password"]
            api = mygeotab.API(username=geotab_username, password=geotab_password, database=database, server=server)

            try:
                api.authenticate()
                st.write("Successfully authenticated with Geotab.")
                
                # Debugging: Show the vehicle ID being queried
                st.write(f"Querying Geotab for vehicle ID: {vehicle_id}")

                device_statuses = api.get('DeviceStatusInfo', search={'deviceSearch': {'id': vehicle_id}})
                
                # Debugging: Show the API response
                st.write("Geotab API response:", device_statuses)

                if device_statuses:
                    device_status = device_statuses[0]
                    lat = device_status.get('latitude', None)
                    lon = device_status.get('longitude', None)
                    vehicle_name = device_status.get('device', {}).get('name', 'Unknown Vehicle')

                    if lat and lon:
                        m = folium.Map(location=[lat, lon], zoom_start=15)
                        folium.Marker([lat, lon], popup=f'{vehicle_name}').add_to(m)
                        folium_static(m)
                    else:
                        st.error("Bus location not available.")
                else:
                    st.error("No data found for this vehicle.")
            except mygeotab.exceptions.AuthenticationException:
                st.error("Authentication failed!")
        else:
            st.error("Please enter a vehicle ID.")

# Show the appropriate tab content
if st.session_state['current_tab']:
    st.header(f"You are in the {st.session_state['current_tab']} area")
    display_bus_location()
else:
    st.warning("Unable to determine your location.")

