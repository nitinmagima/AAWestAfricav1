import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

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
                [d for d in os.listdir(country_path) if os.path.isdir(os.path.join(country_path, d))])

    return countries, seasons


# Get available countries and their seasons
countries, country_seasons = get_country_season_options(BASE_FOLDER)

# Streamlit UI
st.title("📈 AA West Africa - Rainfall Hindcast Multi-Region Bad Year Comparison")

# Dropdown for country selection
selected_country = st.selectbox("🌍 Select a Country", countries)

# Dropdown for season selection (based on selected country)
seasons = country_seasons.get(selected_country, [])
selected_season = st.selectbox("☀️ Select a Season", seasons)


# Function to load CSV files dynamically from selected country & season
@st.cache_data
def load_data(country, season, base_folder):
    folder_path = os.path.join(base_folder, country, season)
    data_dict = {}

    if os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            if file.endswith(".csv"):
                file_path = os.path.join(folder_path, file)
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

                data_dict[place_name] = df  # Store cleaned data

    return data_dict


# Load datasets dynamically
data_dict = load_data(selected_country, selected_season, BASE_FOLDER)

# Multi-select dropdown for regions (if data is available)
if data_dict:
    selected_regions = st.multiselect("📍 Select Regions for Comparison", list(data_dict.keys()),
                                      default=list(data_dict.keys())[:2])

    if selected_regions:
        # Get min/max only from selected regions (avoiding excessive empty space)
        selected_rainfall_values = [data_dict[region]["Rainfall"].min() for region in selected_regions] + \
                                   [data_dict[region]["Rainfall"].max() for region in selected_regions]

        min_rainfall = min(selected_rainfall_values)
        max_rainfall = max(selected_rainfall_values)

        # Add a toggle switch for threshold selection
        use_threshold = st.checkbox("Enable Hindcast Threshold Selection", value=False)

        # Show threshold slider only if enabled
        if use_threshold:
            threshold = st.slider("🌧️ Set Hindcast Rainfall Threshold",
                                  min_value=float(min_rainfall),
                                  max_value=float(max_rainfall),
                                  value=float(min_rainfall))

        st.write("")
        st.markdown("---")
        st.write("")

        # Create a Plotly line chart for multi-region comparison
        fig = go.Figure()

        for region in selected_regions:
            df = data_dict[region]
            fig.add_trace(go.Scatter(
                x=df["Year"], y=df["Rainfall"],
                mode="lines+markers", name=region
            ))

        # Add threshold line only if enabled
        if use_threshold:
            fig.add_trace(go.Scatter(
                x=df["Year"], y=[threshold] * len(df),
                mode="lines", name="Threshold",
                line=dict(color="red", dash="dash")
            ))

        # Dynamically set y-axis range based on selected regions
        fig.update_layout(
            title=f"Hindcast Rainfall for Selected Regions ({selected_season}, {selected_country})",
            xaxis=dict(
                title="Year",
                tickmode="array",
                tickvals=df["Year"].tolist(),
                tickformat="d"  # Removes commas in years
            ),
            yaxis=dict(
                title="Rainfall (mm)",
                range=[min_rainfall * 0.9, max_rainfall * 1.1],  # Adds padding without empty space
            ),
            hovermode="x",
            template="plotly_white"
        )

        # Show the optimized interactive chart
        st.plotly_chart(fig, use_container_width=True)

        # If threshold is enabled, generate bad years table
        if use_threshold:
            bad_years_dict = {}

            # Collect all bad years for each region
            for region in selected_regions:
                df = data_dict[region]
                bad_years = df[df["Rainfall"] < threshold]["Year"].tolist()
                for year in bad_years:
                    if year not in bad_years_dict:
                        bad_years_dict[year] = {}
                    bad_years_dict[year][region] = "Yes"

            # Create a structured DataFrame with only bad years
            if bad_years_dict:
                all_years = sorted(bad_years_dict.keys())
                formatted_df = pd.DataFrame({"Year": all_years})

                # Fill "Yes" where the region had a bad year, leave empty otherwise
                for region in selected_regions:
                    formatted_df[region] = formatted_df["Year"].apply(
                        lambda y: bad_years_dict.get(y, {}).get(region, ""))


                # Highlight color to Orange
                def highlight_bad_years(val):
                    return "background-color: orange; color: black; font-weight: bold;" if val == "Yes" else ""


                styled_df = formatted_df.style.map(lambda x: highlight_bad_years(x), subset=selected_regions)

                # Display the table
                st.subheader("⚠️ Bad Years Detected Based on Hindcast Threshold Selection")
                st.dataframe(styled_df.format({"Year": "{:.0f}"}))  # Ensure Year column has no comma formatting


        # Function to highlight bad years
        def highlight_bad_years(val):
            return "background-color: orange; color: black; font-weight: bold;" if val == "Yes" else ""

        if selected_regions:
            # Frequency-Based Selection of Lowest Rainfall Values
            st.write("")
            st.markdown("---")
            st.write("")
            st.header("Return Period Analysis for Bad Rainfall Years Across Selected Regions")

            # Allow user to select frequency percentage (5%, 10%, 20%)
            st.markdown("**Select the percentage of lowest rainfall years to be considered as 'Bad Years'.**")
            freq_percentage = st.slider(
                "Select Frequency (5%, 10%, 20%) of Bad Years",
                min_value=5,
                max_value=50,
                step=5,
                value=10,
                help="Choose the percentage of lowest rainfall years to analyze as 'Bad Years'. "
                     "For example, selecting 10% means the bottom 10% of rainfall years will be marked."
            )

            # Collect lowest rainfall values based on frequency
            freq_bad_years_dict = {}

            for region in selected_regions:
                df = data_dict[region].copy()
                df_sorted = df.sort_values(by="Rainfall")  # Sort by lowest rainfall
                num_values = int(len(df_sorted) * (freq_percentage / 100))  # Select lowest X%
                freq_bad_years = df_sorted.head(num_values)["Year"].tolist()

                for year in freq_bad_years:
                    if year not in freq_bad_years_dict:
                        freq_bad_years_dict[year] = {}
                    freq_bad_years_dict[year][region] = "Yes"

            # Create a structured DataFrame for frequency-based bad years
            if freq_bad_years_dict:
                all_freq_years = sorted(freq_bad_years_dict.keys())
                freq_formatted_df = pd.DataFrame({"Year": all_freq_years})

                # Fill "Yes" where the region had a bad year, leave empty otherwise
                for region in selected_regions:
                    freq_formatted_df[region] = freq_formatted_df["Year"].apply(
                        lambda y: freq_bad_years_dict.get(y, {}).get(region, ""))

                # 🔴 Apply styling to highlight the lowest values
                styled_freq_df = freq_formatted_df.style.map(lambda x: highlight_bad_years(x), subset=selected_regions)

                # Display the formatted table
                st.subheader(f"Detected Bad Years Based on {freq_percentage}% For Selected Regions")
                st.dataframe(styled_freq_df.format({"Year": "{:.0f}"}))  # Ensure Year column has no comma formatting

                # 📥 Add download button for CSV
                csv_freq = freq_formatted_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"📥 Download Bad Years at {freq_percentage}% as CSV",
                    data=csv_freq,
                    file_name=f"bad_years_frequency_{freq_percentage}_{selected_season}_{selected_country}.csv",
                    mime="text/csv"
                )
            else:
                st.success(f"✅ No data found for the lowest {freq_percentage}% of rainfall values.")





else:
    st.warning("⚠️ No data available for the selected country and season.")

