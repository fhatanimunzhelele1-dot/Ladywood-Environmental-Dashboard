import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import date
from pathlib import Path

st.set_page_config(page_title="Ladywood | Environmental Decision Support", page_icon="L", layout="wide")
st.markdown("""<style>
.block-container {padding-top: 1.35rem; padding-bottom: 3rem; max-width: 1450px;}
h1 {font-weight: 750; letter-spacing: -0.035em;}

[data-testid="stMetric"] {background: transparent; padding: 0.85rem 1rem; border: 1px solid rgba(128,128,128,.32); border-radius: 0.55rem;}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {color: var(--text-color) !important;}
</style>""", unsafe_allow_html=True)
st.title("Ladywood Environmental Dashboard")
st.markdown("**Environmental Monitoring and Rehabilitation Planning**  |  Ladywood, Birmingham")
st.caption("Engineering decision-support prototype · FEBE1004A")
st.divider()
folder = Path(__file__).parent

@st.cache_data(show_spinner="Reading selected flood scenario...")
def load_scenario(path, modified, scenario):
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    features = []
    minlat, minlon, maxlat, maxlon = 90, 180, -90, -180
    for placemark in root.findall(".//k:Placemark", ns):
        values = {item.get("name"): (item.text or "").strip()
                  for item in placemark.findall(".//k:SimpleData", ns)}
        if values.get("aep") != scenario:
            continue
        for polygon in placemark.findall(".//k:Polygon", ns):
            raw = polygon.findtext(".//k:outerBoundaryIs/k:LinearRing/k:coordinates", namespaces=ns)
            if not raw:
                continue
            points = []
            for item in raw.split():
                parts = item.split(",")
                if len(parts) >= 2:
                    try:
                        lon, lat = float(parts[0]), float(parts[1])
                        points.append([lon, lat])
                        minlat, minlon = min(minlat, lat), min(minlon, lon)
                        maxlat, maxlon = max(maxlat, lat), max(maxlon, lon)
                    except ValueError:
                        pass
            if len(points) >= 3:
                # Limit extremely detailed rings for responsive browser rendering.
                if len(points) > 250:
                    step = (len(points) + 248) // 249
                    points = points[::step]
                if points[0] != points[-1]:
                    points.append(points[0])
                features.append({"type": "Feature", "properties": {"scenario": scenario},
                                 "geometry": {"type": "Polygon", "coordinates": [points]}})
    bounds = [[minlat, minlon], [maxlat, maxlon]] if features else None
    return {"type": "FeatureCollection", "features": features}, bounds

@st.cache_data(show_spinner=False)
def load_air_data(path, modified):
    return pd.read_excel(path, header=None)

@st.cache_data(show_spinner=False)
def load_rain_data(path, modified):
    return pd.read_excel(path, header=2)

# Five sections, preserving the existing analyses.
(t_flood_land, t_climate, t_rehab, t_engineering, t_reports) = st.tabs([
    "Flood & Land", "Climate & Air", "Rehabilitation", "Engineering", "Reports & Data"
])
tab1 = tab4 = t_flood_land
tab2 = tab3 = tab10 = t_climate
tab5 = tab7 = t_rehab
tab6 = tab8 = t_engineering
tab9 = tab11 = t_reports

def source_download(pattern, label, key):
    """Offer the original source dataset alongside its analysis."""
    matches = sorted(folder.glob(pattern))
    if matches:
        file = matches[0]
        st.download_button(f"Download {label}", file.read_bytes(),
                           file_name=file.name, key=key)

# Horizontal sub-navigation keeps the merged topics side by side,
# while displaying one full-width analysis at a time.
with t_flood_land:
    flood_land_view = st.radio("Flood & Land sections", ["Flood Risk", "Land Use"], horizontal=True, label_visibility="collapsed", key="flood_land_view")
with t_climate:
    climate_view = st.radio("Climate & Air sections", ["Air Quality", "Rainfall", "Temperature & Heat"], horizontal=True, label_visibility="collapsed", key="climate_view")
with t_rehab:
    rehab_view = st.radio("Rehabilitation sections", ["Priorities", "Intervention Comparison"], horizontal=True, label_visibility="collapsed", key="rehab_view")
with t_engineering:
    engineering_view = st.radio("Engineering sections", ["Hydrology Calculator", "Engineering & Testing"], horizontal=True, label_visibility="collapsed", key="engineering_view")
with t_reports:
    reports_view = st.radio("Reports & Data sections", ["PDF Report", "Data & Sources"], horizontal=True, label_visibility="collapsed", key="reports_view")

with tab1:
    if flood_land_view == 'Flood Risk':
        st.caption("FLOOD & LAND  /  FLOOD-RISK MAPPING")
        st.header("Flood Risk Analysis")
        source_download("*.kml", "flood-risk KML", "flood_tab_download")

        kml_files = sorted(folder.glob("*.kml"))
        if kml_files:
            scenario = st.selectbox("Choose a flood probability scenario:",
                                    ["1 in 30", "1 in 100", "1 in 1000"])
            chance = {"1 in 30": "approximately 3.33%", "1 in 100": "1%", "1 in 1000": "0.1%"}
            colors = {"1 in 30": "#e53935", "1 in 100": "#fb8c00", "1 in 1000": "#1976d2"}
            st.caption(f"Annual exceedance probability: {chance[scenario]}.")
            if st.button("Load Selected Flood Scenario", type="primary"):
                st.session_state["flood_scenario_loaded"] = scenario
            if st.session_state.get("flood_scenario_loaded") == scenario:
                try:
                    kml_file = kml_files[0]
                    with st.spinner("Preparing the selected scenario map..."):
                        geojson, bounds = load_scenario(str(kml_file), kml_file.stat().st_mtime, scenario)
                        flood_map = folium.Map(location=[52.478, -1.922], zoom_start=13,
                                               tiles="OpenStreetMap", prefer_canvas=True)
                        folium.GeoJson(
                            geojson,
                            style_function=lambda feature: {
                                "color": colors[scenario], "weight": 1,
                                "fillColor": colors[scenario], "fillOpacity": 0.4
                            },
                            tooltip=folium.GeoJsonTooltip(fields=["scenario"], aliases=["Flood scenario:"])
                        ).add_to(flood_map)
                        if bounds:
                            flood_map.fit_bounds(bounds)
                    st_folium(flood_map, height=550, width="stretch", returned_objects=[])
                    st.metric("Polygons in selected scenario", len(geojson["features"]))
                    st.caption("Source: Supplied Environment Agency Surface Water Spatial Planning Extents – Present Day KML. Modelled extents, not live flood conditions. For display speed, very detailed polygon outlines are reduced in resolution; do not use this map for property-level decisions.")
                except Exception as error:
                    st.error(f"Could not load the flood map: {error}")
            else:
                st.caption("Select a scenario and choose Load Selected Flood Scenario to display its map.")
        else:
            st.error("Flood-risk KML file not found. Keep your KML file in the Ladywood_Dashboard folder.")

with tab2:
    if climate_view == 'Air Quality':
        st.caption("CLIMATE & AIR  /  AIR QUALITY")
        st.header("Air Quality Monitoring")
        source_download("*Air quality*.xlsx", "air-quality data", "air_tab_download")

        air_files = list(folder.glob("*Air quality*.xlsx"))
        if air_files:
            air_file = air_files[0]
            df = load_air_data(str(air_file), air_file.stat().st_mtime)
            st.subheader("Air Pollution Analysis — 2026")
            pollutants = {"PM2.5": 11, "PM10": 9, "Ozone": 1, "Nitric Oxide": 3,
                          "Nitrogen Dioxide": 5, "Sulphur Dioxide": 7}
            selected = st.selectbox("Choose an air pollutant:", list(pollutants.keys()))
            air = df.iloc[3:13, [0, pollutants[selected]]].copy()
            air.columns = ["Month", "Concentration"]
            air["Concentration"] = pd.to_numeric(air["Concentration"], errors="coerce")
            air = air.dropna(subset=["Month", "Concentration"])
            months_short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            air["Month"] = air["Month"].astype(str).str.strip()
            air = air[air["Month"].isin(months_short)]
            fig_air = px.line(
                air, x="Month", y="Concentration", markers=True,
                title=f"{selected} Concentration in 2026",
                labels={"Concentration": "Concentration (µg/m³)"},
                category_orders={"Month": months_short}
            )
            fig_air.update_layout(hovermode="x unified")
            st.plotly_chart(fig_air, width="stretch")
            st.subheader("Monthly Measurements")
            st.dataframe(air, hide_index=True)
            if not air.empty:
                col1, col2, col3 = st.columns(3)
                col1.metric("Average Concentration", f"{air['Concentration'].mean():.2f} µg/m³")
                col2.metric("Highest Concentration", f"{air['Concentration'].max():.2f} µg/m³")
                col3.metric("Lowest Concentration", f"{air['Concentration'].min():.2f} µg/m³")
        else:
            st.error("Air quality Excel file not found.")

with tab3:
    if climate_view == 'Rainfall':
        st.divider()
        st.caption("CLIMATE & AIR  /  RAINFALL")
        st.header("Rainfall Analysis")
        source_download("*Rainfall*.xlsx", "rainfall data", "rain_tab_download")

        rainfall_files = list(folder.glob("*Rainfall*.xlsx"))
        if rainfall_files:
            rain_file = rainfall_files[0]
            rain = load_rain_data(str(rain_file), rain_file.stat().st_mtime)
            rain = rain[["Year", "Month", "Rainfall (mm)"]].copy()
            rain["Year"] = pd.to_numeric(rain["Year"], errors="coerce")
            rain["Rainfall (mm)"] = pd.to_numeric(rain["Rainfall (mm)"], errors="coerce")
            rain = rain.dropna(subset=["Month", "Rainfall (mm)"])
            rain = rain[rain["Year"] == 2024].copy()
            months_full = ["January", "February", "March", "April", "May", "June",
                           "July", "August", "September", "October", "November", "December"]
            rain["Month"] = pd.Categorical(rain["Month"], categories=months_full, ordered=True)
            rain = rain.sort_values("Month")
            st.subheader("Monthly Rainfall — 2024")
            chart_type = st.radio("Choose graph type:", ["Bar Chart", "Line Chart"], horizontal=True)
            if chart_type == "Bar Chart":
                fig_rain = px.bar(rain, x="Month", y="Rainfall (mm)",
                                  title="Monthly Rainfall in Ladywood — 2024")
            else:
                fig_rain = px.line(rain, x="Month", y="Rainfall (mm)", markers=True,
                                   title="Monthly Rainfall in Ladywood — 2024")
            fig_rain.update_layout(hovermode="x unified")
            st.plotly_chart(fig_rain, width="stretch")
            st.subheader("Rainfall Summary")
            if not rain.empty:
                total = rain["Rainfall (mm)"].sum()
                average = rain["Rainfall (mm)"].mean()
                wettest = rain.loc[rain["Rainfall (mm)"].idxmax()]
                driest = rain.loc[rain["Rainfall (mm)"].idxmin()]
                col1, col2 = st.columns(2)
                col1.metric("Total Annual Rainfall", f"{total:.2f} mm")
                col2.metric("Average Monthly Rainfall", f"{average:.2f} mm")
                col3, col4 = st.columns(2)
                col3.metric(f"Wettest Month: {wettest['Month']}", f"{wettest['Rainfall (mm)']:.2f} mm")
                col4.metric(f"Driest Month: {driest['Month']}", f"{driest['Rainfall (mm)']:.2f} mm")
            st.subheader("Monthly Rainfall Data")
            st.dataframe(rain[["Month", "Rainfall (mm)"]], hide_index=True)
            st.caption("Source: Met Office HadUK-Grid, 1 km spatial resolution, 2024. Rainfall alone does not determine flood risk.")
        else:
            st.error("Rainfall Excel file not found.")

with tab4:
    if flood_land_view == 'Land Use':
        st.divider()
        st.caption("FLOOD & LAND  /  LAND USE")
        st.header("Land Use and Rehabilitation")
        source_download("*Land_Use*.xlsx", "land-use data", "land_tab_download")


        land_files = sorted(folder.glob("*Land_Use*.xlsx"))
        if not land_files:
            st.warning("Land-use Excel file not found. Copy Ladywood_Land_Use_Complete_Table(1).xlsx into your Ladywood_Dashboard folder.")
        else:
            land_file = land_files[0]
            try:
                @st.cache_data(show_spinner=False)
                def load_land_use(path, modified):
                    land = pd.read_excel(path, sheet_name="Land Use")
                    indicators = pd.read_excel(path, sheet_name="Dashboard Indicators")
                    return land, indicators

                land, indicators = load_land_use(str(land_file), land_file.stat().st_mtime)
                land = land.dropna(subset=["Land-use category"]).copy()
                indicators = indicators.dropna(subset=["Indicator"]).copy()

                st.subheader("Key Environmental Indicators")
                indicator_values = dict(zip(indicators["Indicator"], indicators["Ladywood value / finding"]))
                c1, c2, c3 = st.columns(3)
                c1.metric("Green Space per Person", str(indicator_values.get("Green space per person", "Not reported")))
                c2.metric("Tree Canopy Cover", str(indicator_values.get("Tree canopy cover", "Not reported")))
                c3.metric("Brownfield Example", "3.94 ha" if "3.94" in str(indicator_values.get("Brownfield example", "")) else "See dataset")
                st.caption("These indicators come from the supplied spreadsheet and may refer to different geographic boundaries and years. They are not a measured breakdown of land area by category.")

                st.subheader("Explore Land-Use Categories")
                chosen = st.selectbox("Select a land-use category:", land["Land-use category"].astype(str).tolist())
                record = land.loc[land["Land-use category"] == chosen].iloc[0]
                st.markdown("**Documented land-use information**")
                st.write(str(record["Actual Ladywood information"]))
                st.markdown("**Example or location**")
                st.write(str(record["Example / location"]))
                st.markdown("**Environmental significance**")
                st.write(str(record["Environmental significance"]))
                if pd.notna(record.get("Source link")):
                    st.markdown(f"**Source:** [Open supporting source]({record['Source link']})")

                st.subheader("Potential Rehabilitation Actions")
                st.caption("Planning ideas for investigation, not approved projects or site-specific engineering designs.")
                actions = {
                    "Residential": ["Plant shade trees where space and utilities allow", "Introduce rain gardens and community green spaces"],
                    "Industrial": ["Assess possible contamination before redevelopment", "Consider sustainable drainage and green buffers"],
                    "Commercial / mixed-use": ["Add shaded walking and cycling routes", "Explore green roofs and permeable surfaces"],
                    "Green / open space": ["Protect existing open spaces", "Enhance native planting and biodiversity"],
                    "Brownfield / previously developed land": ["Investigate soil quality and remediation needs", "Include trees and sustainable drainage in redevelopment plans"],
                    "Water / canals": ["Protect canal-side habitats", "Improve litter management and drainage connections"],
                    "Roads / transport": ["Explore roadside tree planting", "Assess permeable paving and rain gardens where feasible"],
                    "Tree canopy": ["Identify suitable locations for additional trees", "Plan long-term watering and maintenance"]
                }
                for action in actions.get(chosen, ["Assess local environmental needs before selecting interventions"]):
                    st.write("• " + action)

                st.subheader("Land-Use Evidence Table")
                st.dataframe(land[["Land-use category", "Example / location", "Environmental significance", "Source"]],
                             hide_index=True, width="stretch")
                st.subheader("Indicator Evidence")
                st.dataframe(indicators, hide_index=True, width="stretch")
                st.info("A true land-use area chart or land-use boundary map needs spatial land-cover data or measured area figures. This spreadsheet provides qualitative categories and selected indicators, not land-use percentages or polygon boundaries.")
            except Exception as error:
                st.error(f"Could not read the land-use spreadsheet: {error}")


    # ==========================================
    # TAB 5: REHABILITATION PRIORITY ANALYSIS
    # ==========================================
with tab5:
    if rehab_view == 'Priorities':
        st.header("Rehabilitation Priority Analysis")
        source_download("*Land_Use*.xlsx", "land-use source data", "rehab_tab_download")
        st.write(
            "Compare possible rehabilitation opportunities across the documented "
            "Ladywood land-use categories using a transparent, adjustable screening score."
        )
        st.caption("Illustrative rankings, not measured site risk. Land-use boundaries are not available for spatial overlap analysis.")

        land_files = sorted(folder.glob("*Land_Use*.xlsx"))
        if not land_files:
            st.error("Place your Ladywood land-use Excel spreadsheet in the dashboard folder.")
        else:
            try:
                land_file = land_files[0]
                priorities_land = pd.read_excel(land_file, sheet_name="Land Use")
                priorities_land = priorities_land.dropna(subset=["Land-use category"])
                st.subheader("Adjust the importance of each factor")
                st.caption(
                    "The three sliders set relative importance. Weights are normalised "
                    "automatically, so they do not need to add to 100."
                )
                w1, w2, w3 = st.columns(3)
                with w1:
                    flood_weight = st.slider("Potential runoff / flood benefit", 0, 10, 5)
                with w2:
                    green_weight = st.slider("Greening / heat benefit", 0, 10, 5)
                with w3:
                    delivery_weight = st.slider("Feasibility for initial investigation", 0, 10, 3)

                # These are explicitly subjective initial screening assumptions (1-5).
                # They are NOT calculated from spatial intersections or measured risk.
                assumptions = {
                    "Residential": (3, 4, 3, "Street trees, rain gardens and community greening"),
                    "Industrial": (4, 3, 2, "Site assessment, drainage retrofits and green buffers"),
                    "Commercial / mixed-use": (3, 3, 3, "Green roofs, shade and permeable surfaces"),
                    "Green / open space": (3, 5, 4, "Protect open space; investigate rain gardens and biodiversity"),
                    "Brownfield / previously developed land": (4, 4, 2, "Investigate contamination, drainage and green redevelopment"),
                    "Water / canals": (3, 3, 2, "Canal-edge habitat and drainage assessments"),
                    "Roads / transport": (4, 4, 3, "Roadside trees, rain gardens and permeable paving"),
                    "Tree canopy": (2, 5, 4, "Identify tree planting locations and maintenance needs"),
                }
                rows = []
                for _, record in priorities_land.iterrows():
                    category = str(record["Land-use category"]).strip()
                    if category not in assumptions:
                        continue
                    runoff, greening, feasibility, action = assumptions[category]
                    total_weight = flood_weight + green_weight + delivery_weight
                    score = (
                        (runoff * flood_weight + greening * green_weight +
                         feasibility * delivery_weight) / total_weight
                        if total_weight else 0
                    )
                    rows.append({
                        "Land-use category": category,
                        "Screening score (out of 5)": round(score, 2),
                        "Runoff benefit assumption (1-5)": runoff,
                        "Greening benefit assumption (1-5)": greening,
                        "Feasibility assumption (1-5)": feasibility,
                        "Suggested investigation": action,
                        "Example / location": record.get("Example / location", ""),
                    })

                ranking = pd.DataFrame(rows).sort_values(
                    "Screening score (out of 5)", ascending=False
                ).reset_index(drop=True)
                if ranking.empty:
                    st.info("No matching land-use categories were found in the spreadsheet.")
                else:
                    ranking.insert(0, "Screening rank", range(1, len(ranking) + 1))
                    st.subheader("Illustrative priority ranking")
                    chart = px.bar(
                        ranking.sort_values("Screening score (out of 5)"),
                        x="Screening score (out of 5)",
                        y="Land-use category",
                        orientation="h",
                        text="Screening score (out of 5)",
                        title="Category-level rehabilitation screening",
                        range_x=[0, 5],
                    )
                    chart.update_layout(height=460)
                    st.plotly_chart(chart, width="stretch")
                    top = ranking.iloc[0]
                    st.metric("Highest-ranked category under selected weights",
                              top["Land-use category"])
                    st.write("**Suggested investigation:** " + top["Suggested investigation"])
                    st.subheader("Ranking and assumptions")
                    st.dataframe(ranking, hide_index=True, width="stretch")
                    st.download_button(
                        "Download screening results (CSV)",
                        ranking.to_csv(index=False).encode("utf-8-sig"),
                        file_name="ladywood_rehabilitation_screening.csv",
                        mime="text/csv",
                    )
                    st.subheader("How to use these results responsibly")
                    st.write(
                        "Start with the highest-ranked categories as candidates for "
                        "further investigation. Then obtain site-level land-use boundaries, "
                        "check their intersections with the original flood scenario polygons, "
                        "verify ownership, soil conditions, infrastructure, access, costs, "
                        "and consult residents before proposing specific projects."
                    )
                    st.caption(
                        "Flood scenario maps remain available in the Flood Risk tab. "
                        "The score does not change with the flood scenario because the "
                        "supplied land-use workbook has no geospatial boundaries."
                    )
            except Exception as error:
                st.error(f"Could not calculate the priority screen: {error}")



    # ==========================================
    # ENGINEERING HYDROLOGY: RATIONAL METHOD
    # ==========================================
with tab6:
    if engineering_view == 'Hydrology Calculator':
        st.header("Engineering Hydrology | Rational Method")

        st.latex(r"Q = 0.00278 \, C \, i \, A")
        st.caption("Q (m³/s) = peak flow; C = runoff coefficient; i = rainfall intensity (mm/h); A = area (ha).")
        st.markdown("**Design inputs — editable illustrative scenario**")
        h1, h2, h3 = st.columns(3)
        with h1:
            area_ha = st.number_input("Contributing drainage area (ha)", min_value=0.01, max_value=10000.0, value=3.94, step=0.25, format="%.2f", help="Example area only; 3.94 ha is not a surveyed drainage catchment boundary.")
        with h2:
            intensity = st.number_input("Design rainfall intensity (mm/h)", min_value=0.1, max_value=500.0, value=50.0, step=5.0, help="Illustrative storm intensity. Do not substitute monthly rainfall totals for a design intensity.")
        with h3:
            c_existing = st.slider("Existing runoff coefficient, C", min_value=0.05, max_value=1.0, value=0.85, step=0.05)
        c1, c2 = st.columns(2)
        with c1:
            c_proposed = st.slider("Rehabilitated runoff coefficient, C", min_value=0.05, max_value=1.0, value=0.25, step=0.05)
        with c2:
            tc = st.number_input("Assumed time of concentration (minutes)", min_value=1.0, max_value=360.0, value=20.0, step=1.0, help="The Rational Method normally uses a design rainfall intensity corresponding to the catchment time of concentration and selected return period. This field documents an assumption; it does not automatically determine intensity.")
        q_existing = 0.00278 * c_existing * intensity * area_ha
        q_proposed = 0.00278 * c_proposed * intensity * area_ha
        change_pct = 100 * (q_existing - q_proposed) / q_existing if q_existing else 0.0
        m1, m2, m3 = st.columns(3)
        m1.metric("Existing peak runoff", f"{q_existing:.3f} m³/s")
        m2.metric("Proposed peak runoff", f"{q_proposed:.3f} m³/s")
        m3.metric("Modelled reduction", f"{change_pct:.1f}%")
        comparison = pd.DataFrame({"Surface scenario": ["Existing", "After rehabilitation"], "Runoff coefficient C": [c_existing, c_proposed], "Peak discharge (m³/s)": [q_existing, q_proposed]})
        st.plotly_chart(px.bar(comparison, x="Surface scenario", y="Peak discharge (m³/s)", color="Surface scenario", title="Illustrative peak discharge comparison"), width="stretch")
        st.dataframe(comparison, hide_index=True, width="stretch")
        st.download_button("Download hydrology calculation (CSV)", comparison.to_csv(index=False).encode("utf-8-sig"), file_name="ladywood_rational_method_scenario.csv", mime="text/csv")
        st.caption("Illustrative scenario — input values are assumed, not site-verified.")
        if area_ha > 80:
            st.error("The selected drainage area exceeds 80 ha, beyond the commonly recommended application range for this simplified Rational Method screening. Do not use this result for design.")
        if c_proposed > c_existing:
            st.info("A proposed intervention is not automatically beneficial: a higher runoff coefficient increases calculated discharge under otherwise identical conditions.")
    # ==========================================
    # INTERVENTION COMPARISON: TRANSPARENT SCREEN
    # ==========================================
with tab7:
    if rehab_view == 'Intervention Comparison':
        st.divider()
        st.caption("REHABILITATION  /  INTERVENTION COMPARISON")
        st.header("Engineering Intervention Comparison")
        st.write("Compare possible rehabilitation interventions using technical feasibility, indicative cost, environmental benefit and community impact.")
        st.caption("Ratings are illustrative, not site measurements or verified costs.")
        intervention_rows = [
            ("Rain gardens / bioswales", 4, 3, 5, 4, "Drainage pathways, soil infiltration, utilities and maintenance"),
            ("Permeable paving", 3, 2, 4, 3, "Traffic loads, subgrade, clogging, drainage and maintenance"),
            ("Street trees / green buffers", 4, 4, 4, 5, "Underground services, rooting volume, shade and watering"),
            ("Brownfield soil rehabilitation", 2, 1, 5, 4, "Contamination testing, geotechnics, ownership and remediation permits"),
            ("Green roof retrofit", 2, 2, 4, 3, "Roof load capacity, waterproofing, access and maintenance"),
            ("Existing green-space protection", 5, 5, 4, 5, "Land tenure, ecological value and community access"),
        ]
        interventions = pd.DataFrame(intervention_rows, columns=["Intervention", "Technical feasibility", "Cost affordability", "Environmental benefit", "Community impact", "Required verification"])
        st.caption("Scale: 1 = least favourable, 5 = most favourable. For cost affordability, 5 = lower anticipated cost and 1 = higher anticipated cost. These are ordinal assumptions, not currency estimates.")
        wc1, wc2, wc3, wc4 = st.columns(4)
        with wc1:
            wt = st.slider("Technical feasibility weight", 0, 10, 4, key="intervention_technical")
        with wc2:
            wcost = st.slider("Cost affordability weight", 0, 10, 3, key="intervention_cost")
        with wc3:
            wenv = st.slider("Environmental benefit weight", 0, 10, 5, key="intervention_environment")
        with wc4:
            wcommunity = st.slider("Community impact weight", 0, 10, 4, key="intervention_community")
        weight_total = wt + wcost + wenv + wcommunity
        if weight_total:
            interventions["Weighted score / 5"] = ((interventions["Technical feasibility"] * wt + interventions["Cost affordability"] * wcost + interventions["Environmental benefit"] * wenv + interventions["Community impact"] * wcommunity) / weight_total).round(2)
            interventions = interventions.sort_values(["Weighted score / 5", "Intervention"], ascending=[False, True]).reset_index(drop=True)
            interventions.insert(0, "Screening rank", range(1, len(interventions) + 1))
            st.plotly_chart(px.bar(interventions.sort_values("Weighted score / 5"), x="Weighted score / 5", y="Intervention", orientation="h", range_x=[0, 5], title="Illustrative multi-criteria intervention ranking"), width="stretch")
            st.write("**Highest-ranked option under the selected assumptions:** " + str(interventions.iloc[0]["Intervention"]))
        else:
            st.info("Set at least one weight above zero to calculate a ranking.")
        st.dataframe(interventions, hide_index=True, width="stretch")
        st.download_button("Download intervention comparison (CSV)", interventions.to_csv(index=False).encode("utf-8-sig"), file_name="ladywood_intervention_comparison.csv", mime="text/csv")


    # ==========================================
    # MINING ENGINEERING AND PROTOTYPE EVALUATION
    # ==========================================
with tab8:
    if engineering_view == 'Engineering & Testing':
        st.divider()
        st.header("Engineering Principles & Prototype Evaluation")
        source_download("*Land_Use*.xlsx", "land-use reference data", "engineering_tab_download")
        st.subheader("Mining engineering knowledge applied to an urban setting")
        principles = pd.DataFrame([
            ("Mine-water management and hydrology", "Evaluate runoff from disturbed and sealed surfaces", "Rational Method scenario calculator; mapped flood exposure", "Verify catchments, design storms and drainage capacity"),
            ("Mine closure and land rehabilitation", "Plan staged improvement of degraded or previously developed land", "Brownfield rehabilitation options and intervention screening", "Investigate contamination, remediation objectives and aftercare"),
            ("Geotechnical investigation", "Assess ground suitability before constructing drainage or planting works", "Feasibility and soil-condition checks in intervention comparison", "Soil tests, infiltration tests, stability and buried services"),
            ("Environmental monitoring", "Track environmental indicators and interpret trends", "Air-quality and rainfall graphs", "Verify source provenance, measurement units and time coverage"),
            ("Risk-based engineering decisions", "Compare interventions against multiple constraints", "Adjustable weighting and downloadable ranking tables", "Validate scores with stakeholders and measured evidence"),
        ], columns=["Mining engineering principle", "Urban application", "Dashboard evidence", "Further engineering work"])
        st.dataframe(principles, hide_index=True, width="stretch")

    # ==========================================
    # TAB 6: PROFESSIONAL DOWNLOADABLE PDF REPORT
    # ==========================================
with tab9:
    if reports_view == 'PDF Report':
        st.header("Professional Environmental Assessment Report")
        report_title = st.text_input("Report title", value="Ladywood Environmental Assessment")
        report_author = st.text_input("Prepared by (optional)", value="")

        if st.button("Prepare professional PDF report", type="primary"):
            try:
                from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                    Table, TableStyle, PageBreak, KeepTogether)
                from reportlab.lib import colors
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.enums import TA_CENTER
                from reportlab.lib.pagesizes import A4
                from reportlab.graphics.shapes import Drawing, Rect, String, Line
                from reportlab.lib.colors import HexColor
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                from xml.sax.saxutils import escape

                navy = HexColor("#17324B")
                teal = HexColor("#167D86")
                pale = HexColor("#EAF4F3")
                muted = HexColor("#536778")
                font = "Helvetica"
                font_bold = "Helvetica-Bold"
                for candidate in [
                    "C:/Windows/Fonts/arial.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                ]:
                    if Path(candidate).exists():
                        pdfmetrics.registerFont(TTFont("ReportUnicode", candidate))
                        font = "ReportUnicode"
                        break
                for candidate in [
                    "C:/Windows/Fonts/arialbd.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                ]:
                    if Path(candidate).exists():
                        pdfmetrics.registerFont(TTFont("ReportUnicodeBold", candidate))
                        font_bold = "ReportUnicodeBold"
                        break

                styles = getSampleStyleSheet()
                styles.add(ParagraphStyle(name="CoverKickerCustom", fontName=font_bold,
                    fontSize=11, textColor=teal, spaceAfter=15, leading=17))
                styles.add(ParagraphStyle(name="CoverTitleCustom", fontName=font_bold,
                    fontSize=27, leading=35, textColor=navy, spaceAfter=17))
                styles.add(ParagraphStyle(name="CoverSubtitleCustom", fontName=font,
                    fontSize=12, leading=19, textColor=muted))
                styles.add(ParagraphStyle(name="SectionCustom", fontName=font_bold,
                    fontSize=14, leading=19, textColor=navy, spaceBefore=17, spaceAfter=9))
                styles.add(ParagraphStyle(name="BodyCustom", fontName=font,
                    fontSize=9.2, leading=15, textColor=navy, spaceAfter=8))
                styles.add(ParagraphStyle(name="SmallCustom", fontName=font,
                    fontSize=7.5, leading=11, textColor=muted, spaceAfter=6))
                styles.add(ParagraphStyle(name="TableCustom", fontName=font,
                    fontSize=8.4, leading=12, textColor=navy))
                styles.add(ParagraphStyle(name="TableHeadCustom", fontName=font_bold,
                    fontSize=8.4, leading=12, textColor=colors.white))

                def p(value, style="BodyCustom"):
                    return Paragraph(escape(str(value)), styles[style])
                def heading(label):
                    story.append(p(label, "SectionCustom"))
                def data_table(rows, widths):
                    table = Table([[p(v, "TableHeadCustom" if i == 0 else "TableCustom")
                                    for v in row] for i, row in enumerate(rows)],
                                  colWidths=widths, repeatRows=1, hAlign="LEFT")
                    table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), navy),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, pale]),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("LINEBELOW", (0, -1), (-1, -1), 0.4, HexColor("#CBD9DB")),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 10))

                def footer(canvas, doc):
                    canvas.saveState()
                    w, h = A4
                    canvas.setStrokeColor(HexColor("#D6E3E4"))
                    canvas.line(42, 42, w - 42, 42)
                    canvas.setFont("Helvetica", 8)
                    canvas.setFillColor(muted)
                    canvas.drawString(42, 29, "LADYWOOD  /  ENVIRONMENTAL PLANNING")
                    canvas.drawRightString(w - 42, 29, f"Page {doc.page}")
                    canvas.restoreState()

                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4,
                    leftMargin=46, rightMargin=46, topMargin=55, bottomMargin=60)
                content_width = A4[0] - 92
                story = []

                # Cover page
                story.append(Spacer(1, 105))
                story.append(p("ENVIRONMENTAL MONITORING  /  REHABILITATION PLANNING",
                               "CoverKickerCustom"))
                story.append(p(report_title.strip() or "Ladywood Environmental Assessment",
                               "CoverTitleCustom"))
                story.append(p("Ladywood, Birmingham | Preliminary evidence and planning opportunities",
                               "CoverSubtitleCustom"))
                story.append(Spacer(1, 28))
                cover_bar = Table([[""]], colWidths=[content_width], rowHeights=[9])
                cover_bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), teal)]))
                story.append(cover_bar)
                story.append(Spacer(1, 32))
                story.append(p("Report date: " + date.today().strftime("%d %B %Y")))
                if report_author.strip():
                    story.append(p("Prepared by: " + report_author.strip()))
                story.append(p("Prepared from the environmental datasets supplied with the Ladywood dashboard."))
                story.append(Spacer(1, 26))
                story.append(p("This report is for preliminary planning and education. "
                    "It is not a live flood alert, site-specific risk assessment, "
                    "regulatory approval, or final engineering design.", "SmallCustom"))
                story.append(PageBreak())

                heading("01  |  Executive summary")
                story.append(p("This report reviews modelled surface-water flood scenarios, "
                    "2024 rainfall measurements and land-use indicators. It identifies "
                    "potential environmental rehabilitation interventions for further investigation. "
                    "The datasets represent different years and may use different spatial boundaries."))

                heading("02  |  Modelled surface-water flooding")
                flood_file = next(iter(sorted(folder.glob("*.kml"))), None)
                if flood_file:
                    data_table([
                        ["Scenario", "Annual exceedance probability", "Interpretation"],
                        ["1 in 30", "Approx. 3.33%", "More frequent design scenario"],
                        ["1 in 100", "1%", "Intermediate design scenario"],
                        ["1 in 1000", "0.1%", "Less frequent, more extreme scenario"],
                    ], [110, 175, content_width - 285])
                    story.append(p("Source KML: " + flood_file.name, "SmallCustom"))
                    story.append(p("These are modelled annual probabilities, not dates of "
                        "actual flooding. The map is available interactively in the Flood Risk tab."))
                else:
                    story.append(p("Flood KML file not found; map evidence was not included."))

                heading("03  |  Rainfall evidence (2024)")
                rainfall_file = next(iter(sorted(folder.glob("*Rainfall*.xlsx"))), None)
                if rainfall_file:
                    rainfall = load_rain_data(str(rainfall_file), rainfall_file.stat().st_mtime).copy()
                    rainfall["Year"] = pd.to_numeric(rainfall["Year"], errors="coerce")
                    rainfall["Rainfall (mm)"] = pd.to_numeric(rainfall["Rainfall (mm)"], errors="coerce")
                    rainfall = rainfall[(rainfall["Year"] == 2024) &
                        rainfall["Rainfall (mm)"].notna()].copy()
                    if not rainfall.empty:
                        rainfall["Month"] = rainfall["Month"].astype(str).str.strip()
                        months = ["January", "February", "March", "April", "May", "June",
                            "July", "August", "September", "October", "November", "December"]
                        rainfall["Month"] = pd.Categorical(rainfall["Month"], categories=months, ordered=True)
                        rainfall = rainfall.sort_values("Month")
                        wet = rainfall.loc[rainfall["Rainfall (mm)"].idxmax()]
                        dry = rainfall.loc[rainfall["Rainfall (mm)"].idxmin()]
                        data_table([
                            ["Indicator", "Value"],
                            ["Total annual rainfall", f"{rainfall['Rainfall (mm)'].sum():.2f} mm"],
                            ["Average monthly rainfall", f"{rainfall['Rainfall (mm)'].mean():.2f} mm"],
                            ["Wettest month", f"{wet['Month']}: {wet['Rainfall (mm)']:.2f} mm"],
                            ["Driest month", f"{dry['Month']}: {dry['Rainfall (mm)']:.2f} mm"],
                        ], [220, content_width - 220])
                        values = [float(rainfall.loc[rainfall["Month"] == m,
                            "Rainfall (mm)"].sum()) for m in months]
                        drawing = Drawing(content_width, 195)
                        drawing.add(String(8, 179, "Monthly rainfall (mm) - 2024",
                            fontName="Helvetica-Bold", fontSize=10, fillColor=navy))
                        base_y, plot_height = 32, 127
                        max_v = max(values) * 1.15 if max(values) else 1
                        drawing.add(Line(35, base_y, content_width - 8, base_y,
                            strokeColor=muted, strokeWidth=0.6))
                        drawing.add(Line(35, base_y, 35, base_y + plot_height,
                            strokeColor=muted, strokeWidth=0.6))
                        plot_width = content_width - 54
                        for i, val in enumerate(values):
                            slot = plot_width / 12
                            bar_w = slot * 0.59
                            x = 39 + i * slot + (slot - bar_w) / 2
                            h = (val / max_v) * plot_height
                            drawing.add(Rect(x, base_y, bar_w, h,
                                fillColor=teal, strokeColor=None))
                            drawing.add(String(x + bar_w / 2, 19, months[i][:3],
                                fontName="Helvetica", fontSize=7,
                                textAnchor="middle", fillColor=muted))
                        story.append(drawing)
                        story.append(p("Rainfall alone does not determine local flood risk. "
                            "Source: " + rainfall_file.name, "SmallCustom"))
                    else:
                        story.append(p("No valid 2024 rainfall records found."))
                else:
                    story.append(p("Rainfall spreadsheet not found."))

                heading("04  |  Land-use and green-space evidence")
                land_file = next(iter(sorted(folder.glob("*Land_Use*.xlsx"))), None)
                if land_file:
                    indicators = pd.read_excel(land_file, sheet_name="Dashboard Indicators")
                    indicators = indicators.dropna(subset=["Indicator"])
                    table_rows = [["Indicator", "Reported value / finding"]]
                    for _, record in indicators.iterrows():
                        table_rows.append([str(record["Indicator"]),
                            str(record.get("Ladywood value / finding", "Not reported"))])
                    data_table(table_rows, [220, content_width - 220])
                    story.append(p("Source: " + land_file.name, "SmallCustom"))
                else:
                    story.append(p("Land-use spreadsheet not found."))

                heading("05  |  Rehabilitation opportunities")
                data_table([
                    ["Proposed intervention", "Investigation needed"],
                    ["Street trees and green buffers", "Check planting space, utilities, soil and maintenance."],
                    ["Rain gardens and sustainable drainage", "Check catchments, infiltration and local flood pathways."],
                    ["Permeable paving", "Check ground conditions, traffic and maintenance."],
                    ["Brownfield restoration", "Check contamination, ownership and redevelopment constraints."],
                    ["Green-space and habitat protection", "Check ecological value, access and community priorities."],
                ], [205, content_width - 205])
                story.append(p("These are proposed opportunities for assessment, "
                    "not approved or funded interventions."))

                heading("06  |  Priority analysis and limitations")
                story.append(p("The interactive Rehabilitation Priorities tab uses user-adjustable "
                    "weights and assumed category-level benefit scores. These scores are "
                    "illustrative and are not calculated from geospatial overlap. The "
                    "supplied land-use spreadsheet does not provide polygon boundaries "
                    "that can be intersected with the flood-scenario KML."))
                story.append(p("Before recommending specific locations: obtain geospatial "
                    "land-use data, verify flood and drainage conditions, check ownership, "
                    "utilities, ecology, soil conditions and costs, and consult residents."))
                story.append(Spacer(1, 12))
                story.append(p("DATA NOTE  |  Values and labels are transcribed from supplied "
                    "datasets. Sources may cover different years or spatial extents.", "SmallCustom"))

                doc.build(story, onFirstPage=footer, onLaterPages=footer)
                st.caption("PDF report generated and ready for download.")
                st.download_button("Download professional assessment PDF",
                    data=buffer.getvalue(),
                    file_name="ladywood_professional_environmental_assessment.pdf",
                    mime="application/pdf")
            except ImportError:
                st.error("Install ReportLab first: python -m pip install reportlab")
            except Exception as error:
                st.error(f"Could not prepare the PDF: {error}")


    # ==========================================
    # HISTORICAL TEMPERATURE & HEAT ANALYSIS
    # ==========================================
with tab10:
    if climate_view == 'Temperature & Heat':
        st.divider()
        st.header("Temperature & Heat Analysis")
        temperature_file = folder / "ladywood_temperature_2024_2025.csv"
        if not temperature_file.exists():
            st.warning("Temperature dataset is not available. Place ladywood_temperature_2024_2025.csv in the dashboard folder.")
        else:
            temp = pd.read_csv(temperature_file)
            required = ["Year", "Month", "Mean air temperature (°C)",
                        "Maximum air temperature (°C)", "Minimum air temperature (°C)"]
            if not set(required).issubset(temp.columns):
                st.error("The temperature CSV does not have the expected columns.")
            else:
                for name in required:
                    temp[name] = pd.to_numeric(temp[name], errors="coerce")
                temp = temp.dropna(subset=required).sort_values(["Year", "Month"])
                year_options = sorted(temp["Year"].astype(int).unique().tolist())
                selected_years = st.multiselect("Select year(s)", year_options, default=year_options)
                available = temp[temp["Year"].isin(selected_years)].copy()
                if available.empty:
                    st.info("Select at least one year to display temperature trends.")
                else:
                    variables = ["Mean air temperature (°C)", "Maximum air temperature (°C)",
                                 "Minimum air temperature (°C)"]
                    selected_variable = st.selectbox("Temperature indicator", variables)
                    available["Month name"] = available["Month"].astype(int).map({
                        1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun",
                        7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"})
                    fig = px.line(available, x="Month", y=selected_variable,
                                  color=available["Year"].astype(int).astype(str), markers=True,
                                  labels={"color":"Year", "Month":"Month", selected_variable:"Temperature (°C)"},
                                  title="Monthly air temperature by year")
                    fig.update_xaxes(tickmode="array", tickvals=list(range(1,13)),
                                     ticktext=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])
                    st.plotly_chart(fig, width="stretch")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Mean of monthly mean temperatures", f"{available[variables[0]].mean():.2f} °C")
                    c2.metric("Highest monthly mean daily maximum", f"{available[variables[1]].max():.2f} °C")
                    c3.metric("Lowest monthly mean daily minimum", f"{available[variables[2]].min():.2f} °C")
                    st.subheader("Monthly observations")
                    st.dataframe(available[["Year", "Month name"] + variables], hide_index=True, width="stretch")
                    st.download_button("Download temperature observations (CSV)",
                                       data=temperature_file.read_bytes(),
                                       file_name=temperature_file.name, mime="text/csv", key="temperature_download")
                    st.caption("Source: Met Office HadUK-Grid, 1 km monthly data, 2024–2025. Not street-level heat measurements.")


    # ==========================================
    # TAB 7: PUBLIC DATA ACCESS AND SOURCES
    # ==========================================
with tab11:
    if reports_view == 'Data & Sources':
        st.divider()
        st.header("Data & Sources")
        st.markdown("**Available datasets**")
        source_groups = [
            ("Air quality", "*Air quality*.xlsx", "Monthly pollutant concentrations; see the Air Quality tab for units and year."),
            ("Rainfall", "*Rainfall*.xlsx", "Rainfall workbook used for the 2024 analysis; attributed in the Rainfall tab to Met Office HadUK-Grid."),
            ("Land use and indicators", "*Land_Use*.xlsx", "Qualitative land-use categories, reported indicators and supporting source links."),
            ("Temperature (2024–2025)", "ladywood_temperature_2024_2025.csv", "Met Office HadUK-Grid 1 km monthly temperatures."),
        ]
        for label, pattern, description in source_groups:
            matches = sorted(folder.glob(pattern))
            st.subheader(label)
            st.caption(description)
            if matches:
                source_file = matches[0]
                st.download_button(
                    label=f"Download {label.lower()} dataset",
                    data=source_file.read_bytes(),
                    file_name=source_file.name,
                    mime="text/csv" if source_file.suffix.lower() == ".csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_{pattern}",
                )
            else:
                st.warning(f"The {label.lower()} dataset is currently unavailable.")

        st.subheader("Flood-risk spatial data")
        kml_sources = sorted(folder.glob("*.kml"))
        if kml_sources:
            flood_source = kml_sources[0]
            st.caption(
                "Environment Agency modelled surface-water flood extents, as supplied for this project. "
                "The original KML contains spatial polygons; the displayed map may simplify outlines for performance."
            )
            # Avoid unnecessarily loading very large geospatial files into app memory.
            if flood_source.stat().st_size <= 25 * 1024 * 1024:
                st.download_button(
                    "Download flood-risk spatial data (.kml)",
                    data=flood_source.read_bytes(),
                    file_name=flood_source.name,
                    mime="application/vnd.google-earth.kml+xml",
                    key="download_flood_kml",
                )
            else:
                st.info("The KML is too large for an in-app download. Use the project repository link below to access the original file.")
        else:
            st.warning("The flood-risk spatial dataset is currently unavailable.")

        st.markdown("**Project files and reproducibility**")
        st.link_button(
            "View dashboard code and datasets on GitHub",
            "https://github.com/fhatanimunzhelele1-dot/Ladywood-Environmental-Dashboard",
        )
        st.caption(
            "The linked repository includes the dashboard source code and publicly uploaded data files. "
            "Individual dataset attribution and original source links should be verified before reuse. "
            "The rehabilitation priority scores are illustrative planning assumptions, not measured site risk."
        )
