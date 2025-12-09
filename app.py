import pandas as pd
import streamlit as st
import plotly.express as px
import os

# Streamlit page configuration
st.set_page_config(page_title="✈️ Flight Dashboard", layout="wide")

# Function to load data from local Excel file
# Direct download URL from Google Drive
file_url = "https://drive.google.com/uc?id=1yZOgxaEroxK6_qmzwiTDwT4aDPlA5RB6"

@st.cache_data
def load_data(url):
    try:
        df = pd.read_excel(url, engine="openpyxl")
        return df
    except Exception as e:
        st.error(f"❌ Failed to load Excel file: {e}")
        return None
    
# Load data from Google Drive
df = load_data(file_url)

if df is not None:
    # Clean and convert date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df.dropna(subset=["Date"], inplace=True)

    # Add Year and Month for filtering
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Month_Name"] = df["Date"].dt.strftime("%B")

    # Fix and convert numeric columns
    numeric_cols = ["Total Price", "Commission", "No Passengers"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].replace(["NaN", "nan", "NAN", "Null", "NULL", "", " "], pd.NA)
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Safe integer conversion
    if "No Passengers" in df.columns:
        df["No Passengers"] = df["No Passengers"].fillna(0).astype(int)

    # Sidebar Filters - SIMPLIFIED VERSION
    st.sidebar.header("📅 Filter by Year & Month")
    
    # Year filter
    available_years = sorted(df["Year"].unique(), reverse=True)
    selected_years = st.sidebar.multiselect(
        "Select Years", 
        available_years, 
        default=available_years,
        help="Choose one or multiple years"
    )
    
    # Month filter
    available_months = sorted(df["Month_Name"].unique(), key=lambda x: pd.to_datetime(x, format='%B').month)
    selected_months = st.sidebar.multiselect(
        "Select Months", 
        available_months, 
        default=available_months,
        help="Choose one or multiple months"
    )

    # Apply filters
    filtered_df = df.copy()
    
    if selected_years:
        filtered_df = filtered_df[filtered_df["Year"].isin(selected_years)]
    if selected_months:
        filtered_df = filtered_df[filtered_df["Month_Name"].isin(selected_months)]

    # Display active filters
    st.sidebar.header("📊 Active Filters")
    if selected_years:
        st.sidebar.success(f"**Years:** {', '.join(map(str, selected_years))}")
    if selected_months:
        st.sidebar.success(f"**Months:** {', '.join(selected_months)}")
    
    # Show date range of filtered data
    if not filtered_df.empty:
        min_date = filtered_df["Date"].min().strftime("%b %d, %Y")
        max_date = filtered_df["Date"].max().strftime("%b %d, %Y")
        st.sidebar.info(f"**Date Range:** {min_date} to {max_date}")

    # Filter out "No Tickets"
    ticketed_df = filtered_df[filtered_df["Ticket Numbers"].astype(str).str.lower() != "no tickets"]

    # Drop rows with missing price or commission
    ticketed_df = ticketed_df.dropna(subset=["Total Price", "Commission"])

    # Dashboard Title
    st.title("✈️ Flight Booking Dashboard")
    st.markdown("## 📊 Key Metrics")

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Total Bookings", f"{len(filtered_df):,}")
    col2.metric("🎟️ Total Ticketed Passengers", f"{ticketed_df['No Passengers'].sum():,}")
    col3.metric("💰 Max Ticket Price (ETB)", f"{ticketed_df['Total Price'].max():,.0f}")

    with st.expander("💸 Sales Vs Commission", expanded=False):
        col4, col5, col6 = st.columns(3)
        col4.metric("💸 Total Commission (ETB)", f"{ticketed_df['Commission'].sum():,.0f}")
        col5.metric("💵 Total Sales (ETB)", f"{ticketed_df['Total Price'].sum():,.0f}")
        col6.metric("🎫 Avg. Ticket Price (ETB)", f"{ticketed_df['Total Price'].mean():,.0f}")

    # Create tabs for better organization
    tab1, tab2, tab3, tab4 = st.tabs(["🌍 Route Analysis", "💰 Financials", "🏦 Payment Methods", "🏢 Airport Analysis"])

    with tab1:
        # Create Route column for route analysis
        ticketed_df['Route'] = ticketed_df['From'] + ' → ' + ticketed_df['To']
        
        # Pie chart by Type
        st.subheader("🌍 Route Type: Domestic vs International")
        col1, col2 = st.columns(2)
        
        with col1:
            fig_type = px.pie(ticketed_df, names="Type", title="Flight Type Distribution", hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Set2)
            fig_type.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_type, use_container_width=True)

        with col2:
            # Top 10 Destinations
            st.subheader("🏁 Top 10 Destinations")
            top_dests = (
                ticketed_df.groupby("To")["Total Price"]
                .sum()
                .sort_values(ascending=False)
                .head(10)
                .reset_index()
            )
            fig_dest = px.bar(
                top_dests,
                x="To",
                y="Total Price",
                title="Top Destinations by Total Price",
                labels={"To": "Destination", "Total Price": "Total Price (ETB)"},
                color="Total Price",
                color_continuous_scale="viridis"
            )
            st.plotly_chart(fig_dest, use_container_width=True)

        # NEW: Top Routes by Commission
        st.subheader("💸 Top Routes by Commission")
        
        # Calculate top routes by commission
        top_routes_commission = (
            ticketed_df.groupby('Route')
            .agg({
                'Commission': 'sum',
                'Total Price': 'sum',
                'No Passengers': 'sum'
            })
            .reset_index()
            .sort_values('Commission', ascending=False)
            .head(15)
        )
        
        fig_routes_commission = px.bar(
            top_routes_commission,
            x='Route',
            y='Commission',
            title='Profitable Routes by Commission Earned',
            labels={'Route': 'From → To', 'Commission': 'Total Commission (ETB)'},
            color='Commission',
            color_continuous_scale='greens'
        )
        fig_routes_commission.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
        fig_routes_commission.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_routes_commission, use_container_width=True)

    with tab2:
        st.subheader("💰 Commission by Route Type")
        col1, col2 = st.columns(2)
        
        with col1:
            type_commission = (
                ticketed_df.dropna(subset=["Type"])
                .groupby("Type")["Commission"]
                .sum()
                .reset_index()
                .sort_values("Commission", ascending=False)
            )
            fig_commission_type = px.bar(
                type_commission,
                x="Type",
                y="Commission",
                title="💳 Total Commission by Flight Type",
                labels={"Type": "Flight Type", "Commission": "Total Commission (ETB)"},
                color="Commission",
                color_continuous_scale="Blues"
            )
            fig_commission_type.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
            fig_commission_type.update_layout(yaxis_title="Commission (ETB)", xaxis_title="Flight Type")
            st.plotly_chart(fig_commission_type, use_container_width=True)

        with col2:
            # Ticket Price Range Distribution
            st.subheader("🎯 Ticket Price Distribution")
            price_df = ticketed_df.copy()
            bins = [0, 5000, 10000, 15000, 20000, 30000, 40000, 60000, 100000, float("inf")]
            labels = ["0–5K", "5K–10K", "10K–15K", "15K–20K", "20K–30K", "30K–40K", "40K–60K", "60K–100K", "100K+"]
            price_df["Fixed Price Range"] = pd.cut(price_df["Total Price"], bins=bins, labels=labels, right=False)

            range_counts = (
                price_df.groupby("Fixed Price Range")
                .agg(
                    Ticket_Count=("Fixed Price Range", "count"),
                    Total_Commission=("Commission", "sum"),
                    Avg_Ticket_Price=("Total Price", "mean")
                )
                .reset_index()
            )

            fig_fixed = px.bar(
                range_counts,
                x="Fixed Price Range",
                y="Ticket_Count",
                text="Ticket_Count",
                color="Fixed Price Range",
                title="🎫 Ticket Count by Price Range",
                labels={"Ticket_Count": "Number of Tickets"},
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_fixed.update_traces(textposition='outside')
            fig_fixed.update_layout(xaxis_title="Price Range", yaxis_title="Tickets", xaxis_tickangle=-45)
            st.plotly_chart(fig_fixed, use_container_width=True)

    with tab3:
        st.subheader("🏦 Payment Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            # Commission by Payment Method
            bank_df = (
                ticketed_df.groupby("Payment Method")["Commission"]
                .sum()
                .reset_index()
                .sort_values("Commission", ascending=False)
                .head(10)
            )
            fig_bank = px.bar(
                bank_df,
                x="Payment Method",
                y="Commission",
                title="Top Banks by Commission",
                color="Commission",
                color_continuous_scale="Plasma"
            )
            st.plotly_chart(fig_bank, use_container_width=True)

        with col2:
            # Payment method distribution
            payment_counts = ticketed_df["Payment Method"].value_counts().reset_index()
            payment_counts.columns = ["Payment Method", "Count"]
            fig_payment = px.pie(
                payment_counts,
                names="Payment Method",
                values="Count",
                hole=0.4,
                title="Most Used Payment Methods",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_payment.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_payment, use_container_width=True)

    with tab4:
        st.subheader("🏢 Airport Performance Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            # Airport by Commission
            airport_commission = (
                ticketed_df.groupby("Airport")["Commission"]
                .sum()
                .reset_index()
                .sort_values("Commission", ascending=False)
                .head(10)
            )
            fig_airport_comm = px.bar(
                airport_commission,
                x="Airport",
                y="Commission",
                title="🏢 Top Airports by Commission",
                labels={"Commission": "Total Commission (ETB)"},
                color="Commission",
                color_continuous_scale="teal"
            )
            fig_airport_comm.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
            st.plotly_chart(fig_airport_comm, use_container_width=True)

        with col2:
            # Airport by Ticket Sales
            airport_sales = (
                ticketed_df.groupby("Airport")["Total Price"]
                .sum()
                .reset_index()
                .sort_values("Total Price", ascending=False)
                .head(10)
            )
            fig_airport_sales = px.bar(
                airport_sales,
                x="Airport",
                y="Total Price",
                title="🏢 Top Airports by Sales",
                labels={"Total Price": "Total Sales (ETB)"},
                color="Total Price",
                color_continuous_scale="oranges"
            )
            fig_airport_sales.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
            st.plotly_chart(fig_airport_sales, use_container_width=True)

        # Airport by Number of Bookings
        st.subheader("📊 Airport Booking Volume")
        airport_bookings = (
            ticketed_df["Airport"]
            .value_counts()
            .reset_index()
            .head(15)
        )
        airport_bookings.columns = ["Airport", "Number of Bookings"]
        
        fig_airport_volume = px.bar(
            airport_bookings,
            x="Airport",
            y="Number of Bookings",
            title="Most Active Airports by Number of Bookings",
            color="Number of Bookings",
            color_continuous_scale="purples"
        )
        fig_airport_volume.update_traces(texttemplate='%{y}', textposition='outside')
        st.plotly_chart(fig_airport_volume, use_container_width=True)

else:
    st.warning("📤 Please check if the Excel file exists at the specified path.")
    st.info("""
    **To use this dashboard:**
    1. Update the `file_path` variable in the code to point to your local Excel file
    2. Make sure your Excel file has the required columns:
       - Date, PNR, Payment Method, From, To, Airport, Type
       - Base Total Price, Total Price, Commission, No Passengers, Ticket Numbers
    3. Restart the application
    """)