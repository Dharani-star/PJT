import streamlit as st
from google.cloud import dialogflow
import os

# Set Google Application Credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\dhara\OneDrive\Documents\PJT FINAL\PJT FINAL\aimedicalreceptionist-aymp-98eb4c06c7f5.json"

# Function to send messages to Dialogflow and get a response
def detect_intent_texts(text, session_id="user-session", language_code="en"):
    project_id = "aimedicalreceptionist-aymp"
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(request={"session": session, "query_input": query_input})

    # Extract response from fulfillment messages
    fulfillment_messages = response.query_result.fulfillment_messages
    bot_reply = "\n".join([msg.text.text[0] for msg in fulfillment_messages if msg.text.text])

    return bot_reply

# Streamlit UI
st.set_page_config(page_title="Medical Chatbot", layout="wide")
st.title("🩺 AI Medical Receptionist Chatbot")

# Initialize session state for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Function to handle user input and update chat
def handle_user_input():
    user_message = st.session_state.user_input.strip()
    if user_message:
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "text": user_message})

        # Get response from Dialogflow
        bot_response = detect_intent_texts(user_message)

        # Add bot response to chat history
        st.session_state.chat_history.append({"role": "assistant", "text": bot_response})

    # Clear input field
    st.session_state.user_input = ""

# Display chat history (limit to last 20 messages)
st.subheader("Chat History")
for chat in st.session_state.chat_history[-20:]:  # Show only last 20 messages
    with st.chat_message(chat["role"]):
        st.markdown(chat["text"])

# User input box (auto-clears on submit)
st.text_input("Type your message:", key="user_input", on_change=handle_user_input)



