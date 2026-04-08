import streamlit as st
import google.generativeai as genai
import requests
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Google Doc Chatbot", page_icon="📝")
st.title("📝 Google Doc Knowledge Bot")

# --- FUNCTION TO GET TEXT FROM GOOGLE DOC ---
def get_google_doc_text(url):
    try:
        # Extract the Document ID from the URL
        doc_id_match = re.search(r'/d/([^/]+)', url)
        if not doc_id_match:
            return None, "Invalid Google Doc URL format."
        
        doc_id = doc_id_match.group(1)
        # Use the 'export' endpoint to get plain text
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        
        response = requests.get(export_url)
        if response.status_code == 200:
            return response.text, None
        else:
            return None, "Could not fetch document. Make sure 'Anyone with the link' can view it."
    except Exception as e:
        return None, str(e)

# --- SIDEBAR SETUP ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gemini API Key:", type="password")
    
    # The URL you provided
    doc_url = st.text_input(
        "Google Doc URL:", 
        value="https://docs.google.com/document/d/1L-ZDGHXLOtzO2VmgSKtKYAmSnnMLJEymnf4ZAF2ZxtM/edit?usp=sharing"
    )
    
    if st.button("🔄 Reload Knowledge"):
        st.session_state.knowledge, error = get_google_doc_text(doc_url)
        if error:
            st.error(error)
        else:
            st.success("Knowledge updated!")

# --- LOAD INITIAL KNOWLEDGE ---
if "knowledge" not in st.session_state:
    text, error = get_google_doc_text(doc_url)
    st.session_state.knowledge = text if text else ""

# --- INITIALIZE GEMINI ---
if api_key and st.session_state.knowledge:
    genai.configure(api_key=api_key)
    
    # System Instruction incorporating your Doc's content
    system_prompt = f"""
    You are a specialized assistant. Your knowledge is strictly based on the following document.
    If the user asks something not mentioned in the text, say you don't know based on the provided document, 
    but try to be helpful using general knowledge if appropriate.
    
    DOCUMENT CONTENT:
    {st.session_state.knowledge}
    """
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_prompt
    )
elif not api_key:
    st.info("Enter your API Key in the sidebar to start.")
    st.stop()

# --- CHAT INTERFACE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask me about the document..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # Build history for context
        history = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
            for m in st.session_state.messages[:-1]
        ]
        
        chat = model.start_chat(history=history)
        
        try:
            response = chat.send_message(prompt, stream=True)
            for chunk in response:
                full_response += chunk.text
                response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"Error: {e}")