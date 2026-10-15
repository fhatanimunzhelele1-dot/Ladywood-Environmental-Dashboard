import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import date
from pathlib import Path

st.set_page_config(page_title="Ladywood Environmental Dashboard", page_icon="🌍", layout="wide")
st.title("🌍 Ladywood Environmental Dashboard")
st.write("Community Environmental Monitoring and Rehabilitation Planning")
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

tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏠 Overview", "🌊 Flood Risk", "🌫️ Air Quality",
    "🌧️ Rainfall", "🌳 Land Use", "🎯 Rehabilitation Priorities",
    "📄 PDF Report"
])

with tab0:
    st.header("🏠 Ladywood Environmental Overview")
    st.write(
        "A quick guide to the environmental evidence, mapped flood scenarios "
        "and rehabilitation opportunities explored in this dashboard."
    )
    st.info(
        "The datasets cover different years and geographic extents. "
        "This is a planning and educational dashboard, not a live warning system."
    )

    # Show overview metrics from the same source files as the main tabs.
    rain_total = None
    rain_files = sorted(folder.glob("*Rainfall*.xlsx"))
    if rain_files:
        try:
            rf = rain_files[0]
            overview_rain = load_rain_data(str(rf), rf.stat().st_mtime)
            overview_rain["Year"] = pd.to_numeric(overview_rain["Year"], errors="coerce")
            overview_rain["Rainfall (mm)"] = pd.to_numeric(
                overview_rain["Rainfall (mm)"], errors="coerce"
            )
            overview_rain = overview_rain[overview_rain["Year"] == 2024]
            if overview_rain["Rainfall (mm)"].notna().any():
                rain_total = overview_rain["Rainfall (mm)"].sum()
        except Exception:
            pass

    green_value = "Not available"
    canopy_value = "Not available"
    land_files_overview = sorted(folder.glob("*Land_Use*.xlsx"))
    if land_files_overview:
        try:
            indicator_data = pd.read_excel(
                land_files_overview[0], sheet_name="Dashboard Indicators"
            )
            indicator_data = indicator_data.dropna(subset=["Indicator"])
            iv = dict(zip(
                indicator_data["Indicator"],
                indicator_data["Ladywood value / finding"]
            ))
            green_value = str(iv.get("Green space per person", green_value))
            canopy_value = str(iv.get("Tree canopy cover", canopy_value))
        except Exception:
            pass

    c1, c2, c3 = st.columns(3)
    c1.metric("2024 rainfall total",
              f"{rain_total:,.2f} mm" if rain_total is not None else "Not available")
    c2.metric("Green space per person", green_value)
    c3.metric("Tree canopy cover", canopy_value)
    st.caption(
        "Values are drawn from your rainfall and land-use spreadsheets; "
        "they are not necessarily for identical areas or periods."
    )

    st.subheader("🧭 Explore the dashboard")
    a, b = st.columns(2)
    with a:
        st.markdown("**🌊 Flood Risk**")
        st.write(
            "Compare 1 in 30, 1 in 100 and 1 in 1000 annual-probability "
            "surface-water flood scenarios on an interactive map."
        )
        st.markdown("**🌫️ Air Quality**")
        st.write(
            "Explore 2026 monthly concentrations of PM2.5, PM10, ozone, "
            "nitric oxide, nitrogen dioxide and sulphur dioxide."
        )
        st.markdown("**🎯 Rehabilitation Priorities**")
        st.write(
            "Change the relative importance of runoff reduction, greening "
            "and feasibility to explore illustrative intervention priorities."
        )
    with b:
        st.markdown("**🌧️ Rainfall**")
        st.write(
            "Review 2024 monthly rainfall patterns, annual total "
            "and wettest and driest months."
        )
        st.markdown("**🌳 Land Use**")
        st.write(
            "Explore documented land-use categories, green-space indicators "
            "and potential rehabilitation actions."
        )
        st.markdown("**🌱 Planning opportunities**")
        st.write(
            "Investigate street trees, rain gardens, permeable paving, "
            "green-space protection and suitable brownfield restoration."
        )

    st.subheader("🔎 What the evidence can and cannot tell us")
    st.write(
        "**Flooding:** The KML maps modelled flood extents, not current floods. "
        "**Rainfall:** Rainfall alone does not determine local flood risk. "
        "**Greening:** The land-use workbook provides selected indicators "
        "and qualitative categories, not a spatial land-cover map."
    )
    st.warning(
        "The rehabilitation ranking is an illustrative screening tool. "
        "It does not calculate site-level overlap between land use and flood polygons."
    )
    st.caption(
        "Use the tabs above for detailed charts, source tables, interactive maps "
        "and downloadable rehabilitation screening results."
    )


with tab1:
    st.header("🌊 Flood Risk Analysis")
    st.write("Explore the Environment Agency's modelled surface-water flood scenarios for Ladywood.")
    kml_files = sorted(folder.glob("*.kml"))
    if kml_files:
        st.success("Flood-risk KML file found!")
        scenario = st.selectbox("Choose a flood probability scenario:",
                                ["1 in 30", "1 in 100", "1 in 1000"])
        chance = {"1 in 30": "approximately 3.33%", "1 in 100": "1%", "1 in 1000": "0.1%"}
        colors = {"1 in 30": "#e53935", "1 in 100": "#fb8c00", "1 in 1000": "#1976d2"}
        st.info(f"{scenario} means an annual chance of {chance[scenario]} of a flood of that magnitude or greater. It does not mean a flood happens on a fixed schedule.")
        if st.button("🗺️ Load Selected Flood Scenario", type="primary"):
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
            st.info("Choose a scenario and click 'Load Selected Flood Scenario' to view it.")
    else:
        st.error("Flood-risk KML file not found. Keep your KML file in the Ladywood_Dashboard folder.")

with tab2:
    st.header("🌫️ Air Quality Monitoring")
    st.write("Explore monthly air pollution measurements for Ladywood, Birmingham.")
    air_files = list(folder.glob("*Air quality*.xlsx"))
    if air_files:
        air_file = air_files[0]
        df = load_air_data(str(air_file), air_file.stat().st_mtime)
        st.success("Air quality data loaded successfully!")
        st.subheader("📊 Air Pollution Analysis — 2026")
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
        st.subheader("📋 Monthly Measurements")
        st.dataframe(air, hide_index=True)
        if not air.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Average Concentration", f"{air['Concentration'].mean():.2f} µg/m³")
            col2.metric("Highest Concentration", f"{air['Concentration'].max():.2f} µg/m³")
            col3.metric("Lowest Concentration", f"{air['Concentration'].min():.2f} µg/m³")
    else:
        st.error("Air quality Excel file not found.")

with tab3:
    st.header("🌧️ Rainfall Analysis")
    st.write("Monthly rainfall measurements for Ladywood, Birmingham — 2024.")
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
        st.success("Rainfall data loaded successfully!")
        st.subheader("📊 Monthly Rainfall — 2024")
        chart_type = st.radio("Choose graph type:", ["Bar Chart", "Line Chart"], horizontal=True)
        if chart_type == "Bar Chart":
            fig_rain = px.bar(rain, x="Month", y="Rainfall (mm)",
                              title="Monthly Rainfall in Ladywood — 2024")
        else:
            fig_rain = px.line(rain, x="Month", y="Rainfall (mm)", markers=True,
                               title="Monthly Rainfall in Ladywood — 2024")
        fig_rain.update_layout(hovermode="x unified")
        st.plotly_chart(fig_rain, width="stretch")
        st.subheader("📊 Rainfall Summary")
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
        st.subheader("📋 Monthly Rainfall Data")
        st.dataframe(rain[["Month", "Rainfall (mm)"]], hide_index=True)
        st.caption("Source: Met Office HadUK-Grid, 1 km spatial resolution, 2024. Rainfall alone does not determine flood risk.")
    else:
        st.error("Rainfall Excel file not found.")

with tab4:
    st.header("🌳 Land Use and Rehabilitation")
    st.write("Explore documented land uses and identify potential environmental improvements in Ladywood.")

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
            st.success("Land-use information loaded successfully!")

            st.subheader("📍 Key Environmental Indicators")
            indicator_values = dict(zip(indicators["Indicator"], indicators["Ladywood value / finding"]))
            c1, c2, c3 = st.columns(3)
            c1.metric("Green Space per Person", str(indicator_values.get("Green space per person", "Not reported")))
            c2.metric("Tree Canopy Cover", str(indicator_values.get("Tree canopy cover", "Not reported")))
            c3.metric("Brownfield Example", "3.94 ha" if "3.94" in str(indicator_values.get("Brownfield example", "")) else "See dataset")
            st.caption("These indicators come from the supplied spreadsheet and may refer to different geographic boundaries and years. They are not a measured breakdown of land area by category.")

            st.subheader("🧭 Explore Land-Use Categories")
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

            st.subheader("🌱 Potential Rehabilitation Actions")
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

            st.subheader("📋 Land-Use Evidence Table")
            st.dataframe(land[["Land-use category", "Example / location", "Environmental significance", "Source"]],
                         hide_index=True, width="stretch")
            st.subheader("📊 Indicator Evidence")
            st.dataframe(indicators, hide_index=True, width="stretch")
            st.info("A true land-use area chart or land-use boundary map needs spatial land-cover data or measured area figures. This spreadsheet provides qualitative categories and selected indicators, not land-use percentages or polygon boundaries.")
        except Exception as error:
            st.error(f"Could not read the land-use spreadsheet: {error}")


# ==========================================
# TAB 5: REHABILITATION PRIORITY ANALYSIS
# ==========================================
with tab5:
    st.header("🎯 Rehabilitation Priority Analysis")
    st.write(
        "Compare possible rehabilitation opportunities across the documented "
        "Ladywood land-use categories using a transparent, adjustable screening score."
    )
    st.warning(
        "This is an illustrative category-level planning screen, NOT a measured "
        "site-specific risk assessment. The land-use spreadsheet does not contain "
        "mapped boundaries, so we cannot calculate where its categories overlap "
        "the flood polygons. Scores are planning assumptions, not observed data."
    )

    land_files = sorted(folder.glob("*Land_Use*.xlsx"))
    if not land_files:
        st.error("Place your Ladywood land-use Excel spreadsheet in the dashboard folder.")
    else:
        try:
            land_file = land_files[0]
            priorities_land = pd.read_excel(land_file, sheet_name="Land Use")
            priorities_land = priorities_land.dropna(subset=["Land-use category"])
            st.subheader("⚖️ Adjust the importance of each factor")
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
                st.subheader("📊 Illustrative priority ranking")
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
                st.subheader("📋 Ranking and assumptions")
                st.dataframe(ranking, hide_index=True, width="stretch")
                st.download_button(
                    "⬇️ Download screening results (CSV)",
                    ranking.to_csv(index=False).encode("utf-8-sig"),
                    file_name="ladywood_rehabilitation_screening.csv",
                    mime="text/csv",
                )
                st.subheader("🧭 How to use these results responsibly")
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
# TAB 6: PROFESSIONAL DOWNLOADABLE PDF REPORT
# ==========================================
with tab6:
    st.header("📄 Professional Environmental Assessment Report")
    st.write("Create a formatted report with a cover page, rainfall chart, tables, and recommendations.")
    report_title = st.text_input("Report title", value="Ladywood Environmental Assessment")
    report_author = st.text_input("Prepared by (optional)", value="")
    st.caption("Preliminary planning report; not a regulatory assessment or real-time flood warning.")

    if st.button("📄 Prepare professional PDF report", type="primary"):
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
            st.success("Your professional PDF is ready!")
            st.download_button("⬇️ Download professional assessment PDF",
                data=buffer.getvalue(),
                file_name="ladywood_professional_environmental_assessment.pdf",
                mime="application/pdf")
        except ImportError:
            st.error("Install ReportLab first: python -m pip install reportlab")
        except Exception as error:
            st.error(f"Could not prepare the PDF: {error}")
