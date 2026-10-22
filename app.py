import streamlit as st

st.set_page_config(
    page_title="Ladywood Environmental Dashboard",
    page_icon="🌍",
    layout="wide"
)

st.title("Community Environmental Monitoring and Rehabilitation Planning")
st.subheader("Ladywood, Birmingham")

st.write(
    "This dashboard presents environmental information collected "
    "for Ladywood, Birmingham, focusing on air quality, water and "
    "flooding, climate, and land use."
)

st.divider()

st.header("Environmental Monitoring")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Air Quality", "BMLD")

with col2:
    st.metric("Rainfall", "2024")

with col3:
    st.metric("Flood Scenarios", "3")

with col4:
    st.metric("Study Area", "Ladywood")

st.divider()

st.header("Environmental Areas")

st.write("""
The dashboard will be developed using four main environmental
categories:

- Air Quality
- Water and Flooding
- Climate and Rainfall
- Land Use
""")

st.info(
    "More environmental data and interactive graphs will be added "
    "as the datasets are incorporated."
)