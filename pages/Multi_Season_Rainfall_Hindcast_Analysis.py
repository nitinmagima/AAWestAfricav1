import streamlit as st
import pandas as pd
import os

# Base data folder path
BASE_FOLDER = "data"


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
st.title("📈 AA West Africa - Multi Season Rainfall Hindcast Multi-Region Bad Year Analysis")

# Dropdown for country selection
selected_country = st.selectbox("\U0001F30D Select a Country", countries)


# Function to load all seasons for a country dynamically
@st.cache_data
def load_all_seasons(country, base_folder):
    country_path = os.path.join(base_folder, country)
    season_data = {}

    if os.path.exists(country_path):
        for season in country_seasons.get(country, []):  # Loop through all seasons for the selected country
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

                        # Convert "Year" values: 1 → 1991, ..., 35 → 2025
                        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
                        df.dropna(subset=["Year"], inplace=True)
                        df["Year"] = df["Year"].astype(int) + 1990  # Shift to correct years

                        # Ensure Rainfall values are numeric
                        df["Rainfall"] = pd.to_numeric(df["Rainfall"], errors="coerce")

                        season_data[season][place_name] = df  # Store cleaned data for each region in each season

    return season_data


# Load all seasons for the selected country
all_season_data = load_all_seasons(selected_country, BASE_FOLDER)

# Extract all available regions across all seasons
all_regions = set()
for season, data in all_season_data.items():
    all_regions.update(data.keys())

# Multi-select dropdown for regions (if data is available)
selected_regions = st.multiselect("\U0001F4CD Select Regions for Comparison", sorted(all_regions),
                                  default=list(all_regions)[:2])

# User selects the frequency for bad years
freq_percentage = st.slider("Select Lowest Percentage of Rainfall Years", 5, 50, 10, step=5)

if selected_regions:
    all_bad_years = {}

    # Loop through all seasons
    for season, season_data in all_season_data.items():
        for region in selected_regions:
            if region in season_data:
                df = season_data[region].copy()
                df_sorted = df.sort_values(by="Rainfall")  # Sort by lowest rainfall
                num_values = int(len(df_sorted) * (freq_percentage / 100))  # Select lowest X%
                bad_years = df_sorted.head(num_values)["Year"].tolist()

                for year in bad_years:
                    col_name = f"{region} - {season}"  # Create column name format
                    if year not in all_bad_years:
                        all_bad_years[year] = {}
                    all_bad_years[year][col_name] = "Yes"

    if all_bad_years:
        sorted_years = sorted(all_bad_years.keys())
        formatted_df = pd.DataFrame({"Year": sorted_years})

        # Sort columns by region first, then add its seasons together
        column_order = ["Year"]
        for region in selected_regions:
            region_season_columns = sorted([col for col in formatted_df.columns if col.startswith(region)],
                                           key=lambda x: x.split(" - ")[1])
            column_order.extend(region_season_columns)
        formatted_df = formatted_df[column_order]

        # Fill "Yes" for bad years across region-season combinations
        for year in all_bad_years:
            for col in all_bad_years[year]:  # Iterate over region-season keys
                if col not in formatted_df.columns:
                    formatted_df[col] = ""
                formatted_df.loc[formatted_df["Year"] == year, col] = "Yes"

        # Ensure exact season matches for highlighting
        season_colors = {
            " JJA": "background-color: #ADD8E6; color: black; font-weight: bold;",  # Light blue
            " JAS": "background-color: #90EE90; color: black; font-weight: bold;",  # Light green
            " JJAS": "background-color: #FFB6C1; color: black; font-weight: bold;",  # Light pink
            " JJASO": "background-color: #FFD700; color: black; font-weight: bold;"  # Gold
        }


        def highlight_seasonal_bad_years(val, col):
            for season, color in season_colors.items():
                if col.endswith(season) and val == "Yes":  # Ensure exact season match
                    return color
            return ""


        styled_df = formatted_df.style.apply(
            lambda x: [highlight_seasonal_bad_years(v, c) for v, c in zip(x, formatted_df.columns)], axis=1)

        st.subheader(f"Detected Bad Years Based on {freq_percentage}% For Selected Regions Across All Seasons")
        st.dataframe(styled_df.format({"Year": "{:.0f}"}))

        # Download button
        csv_data = formatted_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv_data, f"bad_years_across_seasons_{freq_percentage}.csv", "text/csv")
    else:
        st.success("✅ No bad years found for the selected criteria.")
