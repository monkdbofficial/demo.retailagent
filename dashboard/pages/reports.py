"""
Reports Page - Generate and download PDF reports.
"""

import streamlit as st
from datetime import datetime
import os
from pathlib import Path


def show(db, ollama, orchestrator):
    """Display reports page."""

    st.markdown('<h1 class="main-header">📄 Report Generator</h1>', 
                unsafe_allow_html=True)

    st.markdown("""
    Generate comprehensive PDF reports with AI insights, visualizations, and data tables.
    """)

    # Report configuration
    st.markdown("### ⚙️ Report Configuration")

    col1, col2 = st.columns(2)

    with col1:
        include_charts = st.checkbox("Include Visualizations", value=True)
        include_ai_insights = st.checkbox("Include AI Insights", value=True)

    with col2:
        include_data_tables = st.checkbox("Include Data Tables", value=True)
        include_exec_summary = st.checkbox("Include Executive Summary", value=True)

    st.markdown("---")

    # Generate report button
    if st.button("📊 Generate Report", type="primary"):
        with st.spinner("Generating PDF report..."):
            try:
                # Load insights
                insights = orchestrator.insight_agent.load_insights()

                if not insights:
                    st.warning("⚠️ No insights available. Generating new insights...")
                    insights = orchestrator.regenerate_insights()

                # Generate report
                pdf_path = orchestrator.generate_report(insights)

                if pdf_path and os.path.exists(pdf_path):
                    st.success(f"✅ Report generated successfully!")

                    # Download button
                    with open(pdf_path, 'rb') as f:
                        pdf_data = f.read()

                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_data,
                        file_name=Path(pdf_path).name,
                        mime="application/pdf"
                    )
                else:
                    st.error("❌ Failed to generate report")

            except Exception as e:
                st.error(f"❌ Error: {e}")

    st.markdown("---")

    # Report history
    st.markdown("### 📚 Report History")

    reports_dir = Path("reports")
    if reports_dir.exists():
        report_files = sorted(
            reports_dir.glob("*.pdf"),
            key=os.path.getmtime,
            reverse=True
        )

        if report_files:
            st.info(f"Found {len(report_files)} previous reports")

            for report_file in report_files[:10]:  # Show last 10
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.text(report_file.name)

                with col2:
                    modified_time = datetime.fromtimestamp(os.path.getmtime(report_file))
                    st.text(modified_time.strftime("%Y-%m-%d %H:%M"))

                with col3:
                    with open(report_file, 'rb') as f:
                        st.download_button(
                            label="📥",
                            data=f.read(),
                            file_name=report_file.name,
                            mime="application/pdf",
                            key=f"download_{report_file.name}"
                        )
        else:
            st.info("No previous reports found")
    else:
        st.info("Reports directory not found")
