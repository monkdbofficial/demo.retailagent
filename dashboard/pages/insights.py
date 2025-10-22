"""
Insights Page - AI-generated insights and analysis.
"""

import streamlit as st
import json


def show(db, ollama, orchestrator):
    """Display insights page."""

    st.markdown('<h1 class="main-header">💡 AI-Generated Insights</h1>', 
                unsafe_allow_html=True)

    # Load insights
    try:
        insights = orchestrator.insight_agent.load_insights()

        if not insights:
            st.warning("⚠️ No insights available. Click 'Regenerate Insights' in the sidebar.")
            return

        # Display timestamp
        st.info(f"📅 Generated: {insights.get('generated_at', 'N/A')}")

        # Executive Summary
        st.markdown("### 📝 Executive Summary")
        exec_summary = insights.get('executive_summary', 'No summary available.')
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 1.5rem; border-radius: 0.5rem; 
                    border-left: 4px solid #1f77b4;">
            {exec_summary}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # AI Insights
        st.markdown("### 🤖 AI Analysis")
        ai_insights = insights.get('ai_insights', 'No insights available.')
        st.markdown(f"""
        <div style="background-color: #e8f4f8; padding: 1.5rem; border-radius: 0.5rem;">
            {ai_insights}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Top Performing Brands
        st.markdown("### 🏆 Top Performing Brands")
        top_brands = insights.get('top_brands', [])

        if top_brands:
            cols = st.columns(3)
            for idx, brand in enumerate(top_brands[:3]):
                with cols[idx]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>{brand.get('brand', 'N/A')}</h3>
                        <p><strong>Products:</strong> {brand.get('product_count', 0)}</p>
                        <p><strong>Avg Rating:</strong> {brand.get('avg_rating', 0):.2f} ⭐</p>
                        <p><strong>Avg Price:</strong> ₹{brand.get('avg_price', 0):.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)

            # Full table
            with st.expander("📊 View All Top Brands"):
                import pandas as pd
                df = pd.DataFrame(top_brands)
                st.dataframe(df, use_container_width=True)
        else:
            st.info("No brand data available")

        st.markdown("---")

        # Product Segments
        st.markdown("### 📦 Product Segments")
        segments = insights.get('product_segments', [])

        if segments:
            import pandas as pd
            df = pd.DataFrame(segments)

            # Display as heatmap-style table
            st.dataframe(
                df.style.background_gradient(cmap='YlOrRd', subset=['count']),
                use_container_width=True
            )
        else:
            st.info("No segmentation data available")

        st.markdown("---")

        # Outliers
        st.markdown("### ⚠️ Price Outliers")
        outliers = insights.get('outliers', [])

        if outliers:
            st.warning(f"Found {len(outliers)} outlier products ( product have prices much higher or lower than the usual range )")

            
            import pandas as pd
            df = pd.DataFrame(outliers)
            st.dataframe(df, use_container_width=True)
        else:
            st.success("No significant outliers detected")

        # Download insights
        st.markdown("---")
        st.markdown("### 💾 Download Insights")

        json_str = json.dumps(insights, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name="insights.json",
            mime="application/json"
        )

    except Exception as e:
        st.error(f"❌ Error loading insights: {e}")
