"""
Chatbot Page - Interactive AI assistant for data queries.
"""

import streamlit as st
import pandas as pd

def show(db, ollama, orchestrator):
    """Display chatbot page."""

    # ------------------------
    # Page Header
    # ------------------------
    st.markdown(
        '<h1 class="main-header">💬 AI Chatbot Assistant</h1>',
        unsafe_allow_html=True
    )

    st.markdown("""
    Ask me anything about your product data! I can help you with:
    - Brand analysis
    - Price trends
    - Rating insights
    - Discount patterns
    - And much more!
    """)

    # ------------------------
    # Initialize session state
    # ------------------------
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm your product analytics assistant. How can I help you today?"}
        ]

    if "current_prompt" not in st.session_state:
        st.session_state.current_prompt = ""

    # ------------------------
    # Display chat history
    # ------------------------
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ------------------------
    # Chat input
    # ------------------------
    user_input = st.chat_input("Ask a question about your products...")

    if user_input:
        st.session_state.current_prompt = user_input

    # ------------------------
    # Example Questions Section (Below Chat Input)
    # ------------------------
    st.markdown("### 💡 Try Example Questions")
    example_questions = [
        "Which brands have the highest average rating?",
        "Show me products priced under ₹1000",
        "What's the average discount across all products?",
        "Which brand offers the biggest discounts?",
        "List low-rated premium products",
        "Top 5 products with most reviews",
        "Average rating per brand",
        "Discount trends over last 3 months",
        "Products with price drop above 20%",
        "Brands with highest revenue contribution"
    ]

    cols = st.columns(2)  # display buttons in 2 columns for cleaner look
    for i, question in enumerate(example_questions):
        if cols[i % 2].button(question, key=f"example_{i}"):
            st.session_state.current_prompt = question

    # ------------------------
    # Process new prompt
    # ------------------------
    if st.session_state.current_prompt:
        prompt = st.session_state.current_prompt

        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = orchestrator.get_chatbot_response(prompt)
                    answer = response.get("answer", "Sorry, I could not process your request.")

                    # Display answer as markdown
                    st.markdown(f"**Answer:** {answer}")

                    # Display structured data if present
                    if "data_context" in response and response["data_context"]:
                        data = response["data_context"]

                        # If it's a DataFrame
                        if isinstance(data, pd.DataFrame):
                            st.markdown("**📊 Related Data:**")
                            st.dataframe(data)

                        # If it's a list of dicts
                        elif isinstance(data, list) and all(isinstance(d, dict) for d in data):
                            df = pd.DataFrame(data)
                            st.markdown("**📊 Related Data:**")
                            st.dataframe(df)

                        # Otherwise, treat as text
                        else:
                            st.markdown("**📊 Related Data:**")
                            st.markdown(f"```\n{str(data)[:1000]}\n```")  # limit display

                except Exception as e:
                    st.error(f"❌ Error fetching response: {e}")
                    answer = "Error in processing the request."

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.session_state.current_prompt = ""

    # ------------------------
    # Clear chat button
    # ------------------------
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm your product analytics assistant. How can I help you today?"}
        ]
        st.session_state.current_prompt = ""
        st.experimental_rerun()
