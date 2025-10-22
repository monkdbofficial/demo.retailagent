"""
Streamlit Dashboard - Main Application
Multi-page interactive dashboard for product analytics.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.env_loader import load_config
from core.monkdb_client import MonkDBClient
from core.ollama_client import OllamaClient
from agents.orchestrator_agent import OrchestratorAgent

# Page configuration
st.set_page_config(
    page_title="MonkDB Product Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"], [data-testid="stSidebarHeader"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_clients():
    """Initialize database and AI clients."""
    config = load_config()

    db_client = MonkDBClient(
        host=config['monkdb']['host'],
        port=int(config['monkdb']['port']),
        user=config['monkdb']['user'],
        password=config['monkdb']['password'],
        schema=config['monkdb']['schema']
    )

    ollama_client = OllamaClient(
        base_url=config['ollama']['base_url'],
        model=config['ollama']['model']
    )

    orchestrator = OrchestratorAgent(db_client, ollama_client)

    return db_client, ollama_client, orchestrator

# Initialize
try:
    db, ollama, orchestrator = init_clients()

    # Sidebar
    with st.sidebar:
        st.image("core/logo.svg", width=250)  # Adjust width as needed
        st.markdown("## 🎯 Navigation")

        page = st.radio(
            "Select Page",
            ["📊 Overview", "💡 Insights", "💬 Chatbot", "📄 Reports"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Database status
        st.markdown("### 🗄️ Database Status")
        health = db.health_check()
        if health['status'] == 'ok':
            st.success("✅ Connected")
        else:
            st.error(f"❌ {health['message']}")

        # Refresh button
        if st.button("🔄 Regenerate Insights"):
            with st.spinner("Generating insights..."):
                orchestrator.regenerate_insights()
                st.success("✅ Insights regenerated!")
                st.rerun()

    # Route to pages
    if page == "📊 Overview":
        from pages import overview
        overview.show(db, ollama, orchestrator)
    elif page == "💡 Insights":
        from pages import insights
        insights.show(db, ollama, orchestrator)
    elif page == "💬 Chatbot":
        from pages import chatbot
        chatbot.show(db, ollama, orchestrator)
    elif page == "📄 Reports":
        from pages import reports
        reports.show(db, ollama, orchestrator)

except Exception as e:
    st.error(f"❌ Application Error: {e}")
    st.info("Please check your configuration and ensure MonkDB and Ollama are running.")
