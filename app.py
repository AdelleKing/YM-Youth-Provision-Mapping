
# -----------------------------
# Medway Activities Explorer
# -----------------------------
# Purpose:
# - Visualise activities on a Leaflet map (via folium)
# - Filter by location, day, activity type, age range label
# - Allow users to submit new activities, append to the same CSV
# - No external DB; CSV is the single source of truth
#
# Requirements:
# pip install streamlit pandas folium streamlit-folium
# -----------------------------

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ---------------------------------------------------------------
# BASIC CONFIG
# ---------------------------------------------------------------
st.set_page_config(
    page_title="Medway Youth Activities Map",
    layout="wide",
)

# Path to your CSV file.
# Make sure this matches the actual filename in your project folder.
DATA_PATH = "Youth Provisions.xlsx - Overview.csv"

# ---------------------------------------------------------------
# AUTH PLACEHOLDER (COMMENTED OUT FOR NOW)
# ---------------------------------------------------------------
# In future, you can implement authentication and wrap your main app.
# Example pattern (pseudo-code):
#
# def check_user_logged_in():
#     # TODO: replace with a real auth mechanism (e.g. streamlit-authenticator)
#     # return True if authenticated, otherwise False
#     return True
#
# if not check_user_logged_in():
#     st.error("Please log in to access this app.")
#     st.stop()
#
# ---------------------------------------------------------------
# DATA LOADING & SAVING
# ---------------------------------------------------------------

@st.cache_data
def load_data(csv_path: str) -> pd.DataFrame:
    """
    Load the activities CSV into a pandas DataFrame.
    - Strips whitespace from column names.
    - Coerces Latitude/Longitude to numeric.
    """
    df = pd.read_csv(csv_path)

    # Normalise column names (remove trailing spaces etc.)
    df.columns = [c.strip() for c in df.columns]

    # Ensure Latitude/Longitude exist even if missing in some rows
    if "Latitude" in df.columns:
        df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    else:
        df["Latitude"] = None

    if "Longitude" in df.columns:
        df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    else:
        df["Longitude"] = None

    return df


def save_data(df: pd.DataFrame, csv_path: str) -> None:
    """
    Persist the DataFrame back to CSV.
    This is your 'write' layer instead of a database.
    """
    df.to_csv(csv_path, index=False)


# ---------------------------------------------------------------
# FILTERING LOGIC
# ---------------------------------------------------------------

def apply_filters(
    df: pd.DataFrame,
    location_query: str,
    selected_activity_types: list,
    selected_days: list,
    selected_age_ranges: list,
) -> pd.DataFrame:
    """
    Filter the DataFrame based on:
    - Free-text location (matches Address / Region / Postcode)
    - Activity Type
    - Day
    - Age range label (string-based, e.g. '13-18', '8+')
    """

    filtered = df.copy()

    # 1) Location free-text search
    if location_query:
        location_query = location_query.strip().lower()

        # List of location-related columns we want to search in
        location_columns = []
        for col in ["Address", "Region", "Postcode"]:
            if col in filtered.columns:
                location_columns.append(col)

        if location_columns:
            loc_mask = False
            for col in location_columns:
                loc_mask = loc_mask | filtered[col].astype(str).str.lower().str.contains(
                    location_query, na=False
                )
            filtered = filtered[loc_mask]

    # 2) Activity Type filter
    if selected_activity_types:
        if "Activity Type" in filtered.columns:
            filtered = filtered[filtered["Activity Type"].isin(selected_activity_types)]

    # 3) Day filter
    if selected_days:
        if "Day" in filtered.columns:
            filtered = filtered[filtered["Day"].isin(selected_days)]

    # 4) Age range label filter (simple categorical, not numeric parsing)
    if selected_age_ranges:
        if "Age range" in filtered.columns:
            filtered = filtered[filtered["Age range"].isin(selected_age_ranges)]

    return filtered


# ---------------------------------------------------------------
# MAP CREATION
# ---------------------------------------------------------------

def create_map(df: pd.DataFrame) -> folium.Map:
    """
    Create a Leaflet map (via folium) showing one marker per activity,
    always centred on Medway.
    """

    # Fixed Medway centre – this is roughly central Chatham / Medway
    center_lat, center_lon = 51.385, 0.53

    # Filter rows with valid coordinates
    df_map = df.dropna(subset=["Latitude", "Longitude"])

    # Create map centred on Medway, with a good local zoom level
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # Add markers
    for _, row in df_map.iterrows():
        lat = row["Latitude"]
        lon = row["Longitude"]

        activity_name = row.get("Activity Name", "Unnamed activity")
        address = row.get("Address", "")
        region = row.get("Region", "")
        day = row.get("Day", "")
        time = row.get("Time", "")
        activity_type = row.get("Activity Type", "")
        type_detail = row.get("Type", "")
        age_range = row.get("Age range", "")

        popup_html = f"""
        <b>{activity_name}</b><br/>
        <i>{activity_type}</i> ({type_detail})<br/>
        <b>Day:</b> {day} &nbsp;&nbsp; <b>Time:</b> {time}<br/>
        <b>Age range:</b> {age_range}<br/>
        <b>Address:</b> {address}, {region}<br/>
        """

        folium.Marker(
            location=[lat, lon],
            popup=popup_html,
        ).add_to(m)

    return m

# ---------------------------------------------------------------
# APP LAYOUT
# ---------------------------------------------------------------

def main():
    # Load data
    df = load_data(DATA_PATH)

    st.title("Medway Youth Activities Map")
    st.write(
        "Explore youth activities across Medway on the map, filter by what matters, "
        "and add new activities directly into the dataset."
    )

    # -----------------------
    # SIDEBAR FILTERS
    # -----------------------
    st.sidebar.header("Filter activities")

    # Location search (text)
    location_query = st.sidebar.text_input(
        "Search by location (address / region / postcode):",
        placeholder="e.g. Gillingham, ME7, Chatham",
    )

    # Activity Type filter (categorical)
    activity_types = []
    if "Activity Type" in df.columns:
        activity_types = sorted(df["Activity Type"].dropna().unique())
    selected_activity_types = st.sidebar.multiselect(
        "Activity type:",
        options=activity_types,
        default=[],
    )

    # Day filter (categorical)
    days = []
    if "Day" in df.columns:
        days = sorted(df["Day"].dropna().unique())
    selected_days = st.sidebar.multiselect(
        "Day:",
        options=days,
        default=[],
    )

    # Age range label filter (string-based)
    age_ranges = []
    if "Age range" in df.columns:
        age_ranges = sorted(df["Age range"].dropna().unique())
    selected_age_ranges = st.sidebar.multiselect(
        "Age range label:",
        options=age_ranges,
        default=[],
        help="These are the age labels exactly as stored in the CSV (e.g. '13-18', '8+').",
    )

    # Apply filters
    filtered_df = apply_filters(
        df,
        location_query=location_query,
        selected_activity_types=selected_activity_types,
        selected_days=selected_days,
        selected_age_ranges=selected_age_ranges,
    )

# -----------------------
# FULL-WIDTH MAP
# -----------------------
    st.subheader("Map view")
    m = create_map(filtered_df)
    st_folium(m, width=None, height=600)  # width=None makes it expand full width

# -----------------------
# ACTIVITIES LIST UNDER MAP
# -----------------------
    
    cols_to_show = [
        col
        for col in [
            "Activity Name",
            "Activity Type",
            "Type",
            "Day",
            "Time",
            "Age range",
            "Address",
            "Region",
            "Postcode",
            "Organisation",
            "Email",
            "Website",
        ] if col in filtered_df.columns
    ]
  

    st.subheader(f"Activities list ({len(filtered_df)} found)")
    st.dataframe(
        filtered_df[cols_to_show].reset_index(drop=True),
        use_container_width=True,
    )

    # -----------------------
    # FORM: ADD NEW ACTIVITY
    # -----------------------
    with st.expander("Add a new activity in Medway"):

        st.caption(
            "Use this form to add a new activity. "
            "On submit, your entry is appended to the CSV and will appear in the map and list."
        )

        with st.form(key="add_activity_form"):
            col1, col2 = st.columns(2)

            with col1:
                activity_name = st.text_input("Activity name *")
                organisation = st.text_input("Organisation")
                activity_type_input = st.text_input(
                    "Activity Type (e.g. 'Sports and Recreation')"
                )
                type_detail = st.text_input(
                    "Type detail (e.g. 'Outdoor Activities', 'Life Skills')"
                )
                day = st.text_input("Day (e.g. 'Monday', 'Wednesday', 'Check website')")
                time = st.text_input("Time (e.g. '18:00-20:00')")

            with col2:
                address = st.text_input("Address")
                region = st.text_input("Region / Town (e.g. Gillingham, Chatham)")
                postcode = st.text_input("Postcode")
                age_range_label = st.text_input("Age range label (e.g. '13-18', '8+', 'All ages')")
                latitude = st.number_input(
                    "Latitude (decimal degrees) *",
                    format="%.6f",
                )
                longitude = st.number_input(
                    "Longitude (decimal degrees) *",
                    format="%.6f",
                )

            website = st.text_input("Website (optional)")
            email = st.text_input("Contact email (optional)")

            submitted = st.form_submit_button("Add activity")

            if submitted:
                # Basic validation: require name + coordinates
                if not activity_name:
                    st.error("Please provide at least an activity name.")
                else:
                    # Reload original data before appending, to minimise overwrite risk
                    current_df = load_data(DATA_PATH)

                    # Build new row as a dict.
                    # Only setting the key fields we care about; other columns will be NaN.
                    new_row = {
                        "Activity Name": activity_name,
                        "Organisation": organisation,
                        "Activity Type": activity_type_input,
                        "Type": type_detail,
                        "Day": day,
                        "Time": time,
                        "Address": address,
                        "Region": region,
                        "Postcode": postcode,
                        "Age range": age_range_label,
                        "Latitude": latitude,
                        "Longitude": longitude,
                        "Website": website,
                        "Email": email,
                    }

                    updated_df = pd.concat(
                        [current_df, pd.DataFrame([new_row])],
                        ignore_index=True,
                    )

                    # Save back to CSV
                    save_data(updated_df, DATA_PATH)

                    st.success("New activity added successfully! The map and list will refresh.")

                    # Force a rerun so the new row appears immediately
                    st.rerun()


if __name__ == "__main__":
    main()

