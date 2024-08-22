import streamlit as st
from streamlit_js_eval import get_geolocation
import mygeotab
import pandas as pd
import folium
from streamlit_folium import folium_static
from shapely.geometry import Point, Polygon

# Set page configuration
st.set_page_config(layout="wide")

# Initialize session state for location and selected tab
if 'user_lat' not in st.session_state:
    st.session_state['user_lat'] = None
if 'user_lon' not in st.session_state:
    st.session_state['user_lon'] = None
if 'current_tab' not in st.session_state:
    st.session_state['current_tab'] = None

# Mapbox token and style
mapbox_token = "pk.eyJ1IjoidnIwMG4tbnljc2J1cyIsImEiOiJjbDB5cHhoeHgxcmEyM2ptdXVkczk1M2xlIn0.qq6o-6TMurwke-t1eyetBw"
mapbox_style = "mapbox://styles/vr00n-nycsbus/cm0404e2900bj01qvc6c381fn"

# Load and display the logo
logo_path = "nycsbus-small-logo.png"

# Display the logo and the title at the top
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.title("Where's the Bus (Depot)")
with col2:
    st.image(logo_path, use_column_width=True,width=100)

# Function to get user location using streamlit_js_eval
def get_user_location():
    location = get_geolocation()
    if location:
        st.session_state['user_lat'] = location['coords']['latitude']
        st.session_state['user_lon'] = location['coords']['longitude']
        st.write(f"Current location: ({st.session_state['user_lat']}, {st.session_state['user_lon']})")
    else:
        st.warning("Unable to get your location.")

get_user_location()

# Function to check if a point is within a polygon
def is_within_bounds(lat, lon, bounds):
    polygon = Polygon(bounds)
    point = Point(lon, lat)
    return polygon.contains(point)

# Define boundaries for Greenpoint, Zerega, Conner, Jamaica, and Richmond Terrace depots
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

conner_bounds = [
    [-73.83038775843255, 40.88696837878996],
    [-73.83038775843255, 40.88480162587726],
    [-73.82786994700692, 40.88480162587726],
    [-73.82786994700692, 40.88696837878996]
]

jamaica_bounds = [
    [-73.77827652778593, 40.70321775639505],
    [-73.77827652778593, 40.699744658752905],
    [-73.77595909919668, 40.699744658752905],
    [-73.77595909919668, 40.70321775639505]
]

richmond_terrace_bounds = [
    [-74.13017255085087, 40.64051079380465],
    [-74.13017255085087, 40.63795904666881],
    [-74.12692989053916, 40.63795904666881],
    [-74.12692989053916, 40.64051079380465]
]

# Function to switch to the appropriate tab based on user location
def switch_to_nearest_tab():
    if st.session_state['user_lat'] and st.session_state['user_lon']:
        if is_within_bounds(st.session_state['user_lat'], st.session_state['user_lon'], greenpoint_bounds):
            st.session_state['current_tab'] = 'Greenpoint'
        elif is_within_bounds(st.session_state['user_lat'], st.session_state['user_lon'], zerega_bounds):
            st.session_state['current_tab'] = 'Zerega'
        elif is_within_bounds(st.session_state['user_lat'], st.session_state['user_lon'], conner_bounds):
            st.session_state['current_tab'] = 'Conner'
        elif is_within_bounds(st.session_state['user_lat'], st.session_state['user_lon'], jamaica_bounds):
            st.session_state['current_tab'] = 'Jamaica'
        elif is_within_bounds(st.session_state['user_lat'], st.session_state['user_lon'], richmond_terrace_bounds):
            st.session_state['current_tab'] = 'Richmond Terrace'
        else:
            st.warning("You are not within any defined bus yard boundaries.")

# Enable or disable automatic tab switching
enable_auto_switch = False  # Set to False to disable

if enable_auto_switch:
    switch_to_nearest_tab()
st.session_state['current_tab'] = 'Greenpoint'
# Function to clean and normalize the vehicle name
def clean_vehicle_name(vehicle_name):
    vehicle_name = vehicle_name.upper().strip()
    if not vehicle_name.startswith("NT"):
        vehicle_name = "NT" + vehicle_name
    return vehicle_name

# Function to display bus location on a map
def display_bus_location():
    vehicle_name = st.text_input("Enter Vehicle ID", placeholder="Vehicle ID")
    
    if st.button("Show Bus Location"):
        if vehicle_name:
            vehicle_name = clean_vehicle_name(vehicle_name)
            
            # Authentication with Geotab
            database = 'nycsbus'
            server = 'afmfe.att.com'
            geotab_username = st.secrets["geotab_username"]
            geotab_password = st.secrets["geotab_password"]
            api = mygeotab.API(username=geotab_username, password=geotab_password, database=database, server=server)

            try:
                api.authenticate()
                
                # Get all devices and map vehicle names to Geotab IDs
                devices = api.get('Device')
                df_id = pd.json_normalize(devices)[['name', 'id']]
                df_id.columns = ["Vehicle", "ID"]
                
                # Look up the internal Geotab ID based on the vehicle name provided by the user
                geotab_id = df_id[df_id['Vehicle'] == vehicle_name]['ID'].values
                if len(geotab_id) == 0:
                    st.error(f"No Geotab ID found for vehicle '{vehicle_name}'.")
                    return
                geotab_id = geotab_id[0]

                # Query Geotab for the device status using the internal ID
                device_statuses = api.get('DeviceStatusInfo', search={'deviceSearch': {'id': geotab_id}})

                if device_statuses:
                    device_status = device_statuses[0]
                    bus_lat = device_status.get('latitude', None)
                    bus_lon = device_status.get('longitude', None)
                    vehicle_name = device_status.get('device', {}).get('name', 'Unknown Vehicle')

                    if bus_lat and bus_lon:
                        # Check if the bus is within the bounds of any depot
                        if (is_within_bounds(bus_lat, bus_lon, greenpoint_bounds) or 
                            is_within_bounds(bus_lat, bus_lon, zerega_bounds) or
                            is_within_bounds(bus_lat, bus_lon, conner_bounds) or
                            is_within_bounds(bus_lat, bus_lon, jamaica_bounds) or
                            is_within_bounds(bus_lat, bus_lon, richmond_terrace_bounds)):
                            
                            # Center the map on the bus location
                            m = folium.Map(location=[bus_lat, bus_lon], zoom_start=19, tiles=f"https://api.mapbox.com/styles/v1/vr00n-nycsbus/cm0404e2900bj01qvc6c381fn/tiles/256/{{z}}/{{x}}/{{y}}@2x?access_token={mapbox_token}", attr="Mapbox")

                            # Add bus marker
                            folium.Marker([bus_lat, bus_lon], popup=f'{vehicle_name}', icon=folium.Icon(color='red', icon='bus', prefix='fa')).add_to(m)

                            # Add user location marker if available
                            if st.session_state['user_lat'] and st.session_state['user_lon']:
                                folium.Marker([st.session_state['user_lat'], st.session_state['user_lon']], popup='Your Location', icon=folium.Icon(color='blue', icon='user', prefix='fa')).add_to(m)

                            # Optimize map for mobile view
                            folium_static(m, width=350, height=500)
                        else:
                            st.error("The bus is not inside a depot. Cannot show location.")
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
