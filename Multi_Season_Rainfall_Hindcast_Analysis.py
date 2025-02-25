import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import datetime

# Base data folder path
BASE_FOLDER = "data"

# Define season-based colors
season_colors = {
    " JJA": "#ADD8E6",  # Light Blue
    " JAS": "#90EE90",  # Light Green
    " JJAS": "#FFB6C1",  # Light Pink
    " JJASO": "#FFD700"  # Gold
}


# Function to highlight bad years based on season
def highlight_seasonal_bad_years(val, col):
    for season, color in season_colors.items():
        if col.endswith(season) and val == "Yes":  # Ensure exact match
            return f"background-color: {color}; color: black; font-weight: bold;"
    return ""

# Function to get available countries and seasons dynamically
def get_country_season_options(base_folder):
    countries = sorted([d for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d))])
    seasons = {}

    for country in countries:
        country_path = os.path.join(base_folder, country)
        if os.path.isdir(country_path):
            seasons[country] = sorted(
                [d for d in os.listdir(country_path) if os.path.isdir(os.path.join(country_path, d))]
            )

    return countries, seasons

# Get available countries and their seasons
countries, country_seasons = get_country_season_options(BASE_FOLDER)

# Streamlit UI
st.title("📈 AA West Africa - Multi Season and Region Rainfall Hindcast Bad Year Analysis")

# Dropdown for country selection
selected_country = st.selectbox("🌍 Select a Country", countries)

# Multi-select dropdown for season selection
available_seasons = country_seasons.get(selected_country, [])
selected_seasons = st.multiselect("☀️ Select Seasons", available_seasons, default=available_seasons)

# Function to load selected seasons for a country dynamically
@st.cache_data
def load_selected_seasons(country, selected_seasons, base_folder):
    country_path = os.path.join(base_folder, country)
    season_data = {}

    if os.path.exists(country_path):
        for season in selected_seasons:
            season_path = os.path.join(country_path, season)
            season_data[season] = {}

            if os.path.exists(season_path):
                for file in os.listdir(season_path):
                    if file.endswith(".csv"):
                        file_path = os.path.join(season_path, file)
                        place_name = file.replace("mean_data.csv", "").replace(".csv", "").replace("_", " ").strip()
                        df = pd.read_csv(file_path, header=None)

                        # Rename columns correctly
                        df.columns = ["Year", "Rainfall"]

                        # Get current year dynamically
                        current_year = datetime.datetime.now().year

                        # Convert "Year" column to numeric
                        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").dropna().astype(int)

                        # Check if the majority of values are less than 4 digits (likely an index)
                        if (df["Year"] < 1000).sum() > (df.shape[0] / 2):  # If more than half are indexes
                            max_index = df["Year"].max()  # Find highest index
                            start_year = current_year - max_index  # Compute dynamic base year
                            df["Year"] = df["Year"] + start_year  # Convert indexes to years

                        df["Rainfall"] = pd.to_numeric(df["Rainfall"], errors="coerce")

                        season_data[season][place_name] = df

    return season_data

# Load selected seasons for the selected country
all_season_data = load_selected_seasons(selected_country, selected_seasons, BASE_FOLDER)

# Extract all available regions across selected seasons
all_regions = {region for season in selected_seasons for region in all_season_data.get(season, {})}

# Multi-select dropdown for regions
selected_regions = st.multiselect("📍 Select Regions for Comparison", sorted(all_regions), default=list(all_regions)[:2])

# Create data_dict dynamically
data_dict = {f"{region} - {season}": all_season_data[season][region]
             for season in selected_seasons for region in selected_regions if region in all_season_data[season]}

# Ensure selections are valid before proceeding
if selected_regions and selected_seasons and data_dict:

    # Get min/max rainfall values across selected regions
    selected_rainfall_values = [df["Rainfall"].min() for df in data_dict.values()] + \
                               [df["Rainfall"].max() for df in data_dict.values()]
    min_rainfall, max_rainfall = min(selected_rainfall_values), max(selected_rainfall_values)

    # Threshold selection
    use_threshold = st.checkbox("Enable Hindcast Rainfall Baseline Selection", value=False, key="threshold_toggle")
    if use_threshold:
        threshold = st.slider("🌧️ Set Hindcast Rainfall Baseline", float(min_rainfall), float(max_rainfall),
                              value=float(min_rainfall))

    st.write("")
    st.markdown("---")
    st.write("")

    # Create a Plotly line chart for multi-region comparison
    fig = go.Figure()
    for col_name, df in data_dict.items():
        fig.add_trace(go.Scatter(x=df["Year"], y=df["Rainfall"], mode="lines+markers", name=col_name))

    # Add threshold line if enabled
    if use_threshold:
        fig.add_trace(go.Scatter(x=df["Year"], y=[threshold] * len(df), mode="lines",
                                 name="Selected Rainfall Baseline for Bad Year", line=dict(color="red", dash="dash")))

    # Update layout
    fig.update_layout(title=f"Hindcast Rainfall for Selected Regions ({', '.join(selected_seasons)}, {selected_country})",
                      xaxis=dict(title="Year", tickformat="d"),
                      yaxis=dict(title="Rainfall (mm)", range=[min_rainfall * 0.9, max_rainfall * 1.1]),
                      hovermode="x", template="plotly_white")

    st.plotly_chart(fig, use_container_width=True)


    # Generate Bad Years Table if threshold is enabled
    if use_threshold:
        st.write("")
        st.markdown("---")
        st.write("")

        bad_years_dict = {year: {col_name: "Yes" for col_name, df in data_dict.items() if year in df["Year"].values and
                                 df[df["Year"] == year]["Rainfall"].values[0] < threshold}
                          for df in data_dict.values() for year in df["Year"].values}

        if bad_years_dict:
            formatted_df = pd.DataFrame({"Year": sorted(bad_years_dict.keys())})

            for col_name in data_dict.keys():
                formatted_df[col_name] = formatted_df["Year"].apply(
                    lambda y: bad_years_dict.get(y, {}).get(col_name, ""))

            # Apply highlighting across all columns dynamically
            styled_df = formatted_df.style.apply(
                lambda x: [highlight_seasonal_bad_years(v, c) for v, c in zip(x, formatted_df.columns)], axis=1
            )

            # Display styled DataFrame
            st.header("Bad Years Analysis Based on Rainfall Hindcast Baseline Selection")
            st.dataframe(styled_df.format({"Year": "{:.0f}"}))

# User selects the frequency for bad years
st.write("")
st.markdown("---")
st.write("")
st.header("Bad Years Analysis Based on Lowest Percentage of Rainfall Frequency Selection")

if selected_regions and selected_seasons:
    all_bad_years = {}

    # Step 1: Get min/max year dynamically from the dataset
    min_year, max_year = float('inf'), float('-inf')

    for season in selected_seasons:
        if season in all_season_data:
            for region in selected_regions:
                if region in all_season_data[season]:
                    df = all_season_data[season][region]

                    # Update min/max year dynamically
                    min_year = min(min_year, df["Year"].min())
                    max_year = max(max_year, df["Year"].max())

    # Ensure valid year range (handle no data case)
    if min_year == float('inf') or max_year == float('-inf'):
        st.warning("No data found for the selected regions and seasons.")
    else:
        # Step 2: Year Range Slider (User selects which years to analyze)
        year_range = st.slider("📅 Select Year Range", min_value=int(min_year), max_value=int(max_year),
                               value=(int(min_year), int(max_year)))

        # Step 3: Filter data based on selected year range
        filtered_data = {}
        for season in selected_seasons:
            if season in all_season_data:
                for region in selected_regions:
                    if region in all_season_data[season]:
                        df = all_season_data[season][region]
                        df_filtered = df[(df["Year"] >= year_range[0]) & (df["Year"] <= year_range[1])]

                        col_name = f"{region} - {season}"
                        filtered_data[col_name] = df_filtered  # Store filtered data

        # Step 4: Frequency Slider (Now apply percentage selection on the filtered dataset)
        freq_percentage = st.slider("📉 Select Lowest Percentage of Rainfall Years", 5, 50, 10, step=5)

        # Step 5: Process the filtered dataset
        for col_name, df_filtered in filtered_data.items():
            df_sorted = df_filtered.sort_values(by="Rainfall")
            num_values = int(len(df_sorted) * (freq_percentage / 100))
            bad_years = df_sorted.head(num_values)["Year"].tolist()

            for year in bad_years:
                if year not in all_bad_years:
                    all_bad_years[year] = {}
                all_bad_years[year][col_name] = "Yes"

        if all_bad_years:
            formatted_df = pd.DataFrame({"Year": sorted(all_bad_years.keys())})

            for col_name in filtered_data.keys():
                formatted_df[col_name] = formatted_df["Year"].apply(lambda y: all_bad_years.get(y, {}).get(col_name, ""))

            # Highlight bad years based on their season
            styled_df = formatted_df.style.apply(
                lambda x: [highlight_seasonal_bad_years(v, c) for v, c in zip(x, formatted_df.columns)], axis=1
            )

            st.subheader(f"Bad Years Based on {freq_percentage}% Lowest Rainfall (Filtered by Year Range: {year_range[0]} - {year_range[1]})")
            st.dataframe(styled_df.format({"Year": "{:.0f}"}))

