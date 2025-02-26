import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import datetime
import json

# Base data folder path
BASE_FOLDER = "data"

# Load translations from JSON file
with open("translations.json", "r", encoding="utf-8") as file:
    translations = json.load(file)

# Sidebar: Language Selector
selected_language = st.sidebar.selectbox("🌐 Select Language", list(translations.keys()))

# Get selected language dictionary
lang = translations[selected_language]

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
st.title(lang["title"])

# Dropdown for country selection
selected_country = st.selectbox(lang["select_country"], countries)

# Multi-select dropdown for season selection
available_seasons = country_seasons.get(selected_country, [])
selected_seasons = st.multiselect(lang["select_seasons"], available_seasons, default=available_seasons)

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
selected_regions = st.multiselect(lang["select_regions"], sorted(all_regions), default=list(all_regions)[:2])

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
    use_threshold = st.checkbox(lang["enable_threshold"], value=False, key="threshold_toggle")
    if use_threshold:
        threshold = st.slider(lang["set_threshold"], float(min_rainfall), float(max_rainfall),
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
    fig.update_layout(title=f"{lang['hindcast_chart_title']} ({', '.join(selected_seasons)}, {selected_country})",
                      xaxis=dict(title=lang["year"], tickformat="d"),
                      yaxis=dict(title=lang["rainfall_mm"], range=[min_rainfall * 0.9, max_rainfall * 1.1]),
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
            st.header(lang["threshold_analysis"])
            st.dataframe(styled_df.format({"Year": "{:.0f}"}))

# User selects the frequency for bad years
st.write("")
st.markdown("---")
st.write("")
st.header(lang["freq_analysis"])

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
        st.warning(lang["bad_years_msg"])
    else:
        # Step 2: Year Range Slider (User selects which years to analyze)
        year_range = st.slider(lang["year_range"], min_value=int(min_year), max_value=int(max_year),
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
        freq_percentage = st.slider(lang["freq_percentage"], 5, 50, 10, step=5)

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

            st.subheader(f"{lang['bad_years_table']} - {freq_percentage}% : {year_range[0]} - {year_range[1]}")
            st.dataframe(styled_df.format({"Year": "{:.0f}"}))

        # Multi-Select Dropdown for Year Selection
        # User selects the frequency for bad years
        st.write("")
        st.markdown("---")
        st.write("")
        st.header(lang["historical_analysis"])

        # Step 6: Multi-Select Dropdown for Year Selection Based on Dataset Range
        # Ensure valid years exist before proceeding
        if min_year != float('inf') and max_year != float('-inf'):
            year_options = list(range(int(year_range[0]), int(year_range[1]) + 1))  # Generate full year range

            selected_years = st.multiselect(
                lang["historical_loss_select"], year_options, default=[]  # Default to none selected
            )

            # Step 7: Compute Percentage of Selected Years That Are Bad Years
            if selected_years:
                selected_years_percentages = {}

                # Ensure we have valid bad years to analyze
                if all_bad_years and selected_years:
                    total_selected_years = len(selected_years)  # 🔹 Total number of selected years

                    # Loop through all selected columns (region-season combinations)
                    for col_name in set(
                            k for v in all_bad_years.values() for k in v.keys()):  # Dynamically get column names
                        # Count how many selected years are bad years for this column
                        selected_bad_years = sum(
                            1 for year in selected_years if year in all_bad_years and col_name in all_bad_years[year]
                        )

                        # Compute percentage relative to selected years
                        if total_selected_years > 0:
                            selected_years_percentages[col_name] = (selected_bad_years / total_selected_years) * 100
                        else:
                            selected_years_percentages[col_name] = 0  # If no selected years, set 0%

                # 🔹 Visualization: Horizontal Bar Chart
                if selected_years_percentages and any(
                        v > 0 for v in selected_years_percentages.values()):  # Ensure valid data
                    # Sort data for better visualization
                    sorted_data = sorted(selected_years_percentages.items(), key=lambda x: x[1], reverse=True)
                    labels, values = zip(*sorted_data)  # Extract column names & percentages

                    # Create Plotly bar chart
                    fig = go.Figure(go.Bar(
                        x=values,  # Percentages
                        y=labels,  # Column Names
                        orientation="h",  # Horizontal bar chart
                        marker=dict(
                            color=values,  # Dynamic color based on value
                            colorscale="blues",  # Color gradient (light to dark blue)
                            showscale=True  # Show color scale
                        ),
                        text=[f"{v:.2f}%" for v in values],  # Show percentage on bars
                        textposition="outside"  # Place labels outside bars
                    ))

                    fig.update_layout(
                        title=lang["graph_title"],  # 🔹 Localized title
                        xaxis_title=lang["xaxis_title"],  # 🔹 Localized x-axis label
                        yaxis_title=lang["yaxis_title"],  # 🔹 Localized y-axis label
                        xaxis=dict(range=[0, 100]),  # 🔹 Force x-axis from 0% to 100%
                        yaxis=dict(categoryorder="total ascending"),  # Sort bars by value
                        height=600,  # Adjust height for readability
                    )

                    # Display chart
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(lang["bad_years_msg_historical"])
            else:
                st.info(lang["bad_years_msg_percent"])







