"""
Overview Page - Summary statistics and visualizations.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def show(db, ollama, orchestrator):
    """Display overview page."""

    st.markdown('<h1 class="main-header">📊 Product Analytics Overview</h1>', 
                unsafe_allow_html=True)

    # Get summary stats
    stats = db.get_summary_stats()

    if not stats:
        st.warning("⚠️ No data available. Please upload CSV files to watch_folder/")
        return

    # Summary cards
    st.markdown("### 📈 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Products",
            f"{int(stats.get('total_products', 0)):,}",
            delta=None
        )

    with col2:
        st.metric(
            "Total Brands",
            f"{int(stats.get('total_brands', 0)):,}",
            delta=None
        )

    with col3:
        st.metric(
            "Avg Price",
            f"₹{stats.get('avg_price', 0):.2f}",
            delta=None
        )

    with col4:
        st.metric(
            "Avg Rating",
            f"{stats.get('avg_rating', 0):.2f} ⭐",
            delta=None
        )

    st.markdown("---")

    # Visualizations
    st.markdown("### 📊 Data Visualizations")

    # Row 1: Brand Analysis
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Top Brands by Product Count")
        top_brands = db.query_top_brands(limit=10)

        if not top_brands.empty:
            fig = px.bar(
                top_brands,
                x='brand',
                y='product_count',
                color='avg_rating',
                title="Top 10 Brands",
                labels={'product_count': 'Products', 'brand': 'Brand'},
                color_continuous_scale='Viridis'
            )
            fig.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No brand data available")

    with col2:
        st.markdown("#### Average Price by Top Brands")
        if not top_brands.empty:
            fig = px.line(
                top_brands,
                x='brand',
                y='avg_price',
                markers=True,
                title="Price Trends",
                labels={'avg_price': 'Avg Price (₹)', 'brand': 'Brand'}
            )
            fig.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No price data available")

    # Row 2: Price and Rating Analysis
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Price vs Discount")
        price_discount = db.query_price_discount_correlation()

        if not price_discount.empty:
            fig = px.scatter(
                price_discount.head(500),
                x='price',
                y='discount_percent',
                color='rating',
                size='rating',
                hover_data=['brand'],
                title="Price-Discount Relationship",
                labels={'price': 'Price (₹)', 'discount_percent': 'Discount (%)'},
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No price-discount data available")

    with col2:
        st.markdown("#### Rating Distribution")
        rating_dist = db.query_rating_distribution()

        if not rating_dist.empty:
            fig = px.histogram(
                rating_dist,
                x='rating_bucket',
                y='count',
                title="Product Ratings Distribution",
                labels={'rating_bucket': 'Rating', 'count': 'Product Count'},
                color='count',
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No rating data available")

    # Row 3: Segmentation
    st.markdown("#### Product Segmentation (Price vs Rating)")
    segments = db.query_product_segments()

    if not segments.empty:
        # Create sunburst chart
        fig = px.sunburst(
            segments,
            path=['price_segment', 'rating_segment'],
            values='count',
            color='avg_price',
            title="Product Segments",
            color_continuous_scale='RdBu'
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        # Data table
        with st.expander("📋 View Segmentation Data"):
            st.dataframe(segments, use_container_width=True)
    else:
        st.info("No segmentation data available")
