import streamlit as st
from core.preload import get_model, get_collection
from sentence_transformers import SentenceTransformer
import re
from gtts import gTTS
import tempfile
import base64
import io

def text_to_audio_html(text):
    """Convert text to speech and return HTML audio player."""
    try:
        tts = gTTS(text)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_file.name)

        with open(temp_file.name, "rb") as f:
            audio_bytes = f.read()

        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        audio_html = f"""
        <audio controls autoplay style="width: 300px;">
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
        </audio>
        """
        return audio_html
    except Exception as e:
        st.error(f"Audio generation error: {e}")
        return ""



def clean_output(text):
    # Remove markdown formatting characters only
    text = re.sub(r'[\\*_`~#]', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(
        r"(I can help clarify.*?\.|If you have.*?handbook\.|Next Steps:.*)",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )
    return text.strip()



st.set_page_config(page_title="FrontShiftAI", layout="wide", initial_sidebar_state="collapsed")


hide_sidebar_css = """
    <style>
        [data-testid="stSidebar"], 
        [data-testid="stSidebarNav"], 
        [data-testid="stSidebarCollapsedControl"],
        section[data-testid="stSidebarNav"],
        div[data-testid="stDecoration"] {
            display: none !important;
        }
        #MainMenu, footer, header {visibility: hidden !important;}
    </style>
    <script>
        // Actively keep sidebar hidden during rerenders
        const hideSidebar = () => {
            const s = window.parent.document.querySelector('section[data-testid="stSidebar"]');
            if (s) s.style.display = 'none';
        };
        hideSidebar();
        setInterval(hideSidebar, 100);
    </script>
"""
st.markdown(hide_sidebar_css, unsafe_allow_html=True)


if "email" not in st.session_state or "company" not in st.session_state:
    # Clear everything and redirect to login immediately
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.switch_page("app.py")
    st.stop()


user_email = st.session_state.email
company_name = st.session_state.company


# Derive display name from email
display_name = user_email.split("@")[0].replace(".", " ").title()

# Function to add spaces and title case the company name
def format_company_name(name):
    name = name.replace("_", " ").strip()
    if name.islower() and " " not in name:
        parts = re.findall(r"[A-Z]?[a-z]+", name)
        name = " ".join(parts).title()
    else:
        name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name).title()
    return name

company_display = format_company_name(company_name)

# Custom CSS for centering and layout
st.markdown("""
    <style>
        .center-header {
            text-align: center;
            margin-top: 40px;
            margin-bottom: 10px;
        }
        .welcome-text {
            font-size: 1.8rem;
            font-weight: 600;
            color: #FFFFFF;
        }
        .company-text {
            font-size: 1.2rem;
            color: #BBBBBB;
        }
        .logout-btn {
            position: fixed;
            top: 20px;
            right: 30px;
            z-index: 9999;
        }
        .logout-btn button {
            background-color: #262730;
            color: white;
            border: none;
            padding: 6px 16px;
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
        }
        .logout-btn button:hover {
            background-color: #444;
        }
        hr {border: 1px solid #333;}
    </style>
""", unsafe_allow_html=True)

# Logout button (functional Streamlit component, not HTML)
logout_col = st.columns([10, 1])[1]
with logout_col:
    if st.button("🚪 Logout", key="logout_btn"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("app.py")

# Centered welcome header
st.markdown(f"""
    <div class="center-header">
        <div class="welcome-text">Welcome, <b>{display_name}</b></div>
        <div class="company-text">Connected to <b>{company_display}</b> handbook</div>
    </div>
    <hr>
""", unsafe_allow_html=True)

# Voice chat button - RIGHT HERE, remove the duplicate sections
col_voice1, col_voice2, col_voice3 = st.columns([2, 1, 2])
with col_voice2:
    if st.button("🎙️ Switch to Voice Chat", use_container_width=True):
        st.switch_page("pages/voice_chat.py")
st.markdown("---")


llm = get_model()
collection = get_collection()
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def query_docs(query, company):
    try:
        normalized_company = company.lower().replace(" ", "").replace("_", "")
        all_meta = collection.get(include=["metadatas"])

        possible_company = None
        for m in all_meta["metadatas"]:
            if not m:
                continue
            stored_name = str(m.get("company", "")).lower().replace(" ", "")
            if normalized_company in stored_name:
                possible_company = m.get("company")
                break

        if not possible_company:
            st.warning("⚠️ Could not find matching company in Chroma metadata.")
            return None, None

        # --- Explicit cosine retrieval using manual embeddings ---
        query_emb = embedder.encode([query])[0].tolist()
        results = collection.query(
            query_embeddings=[query_emb],
            where={"company": {"$eq": possible_company}},
            n_results=10,
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        if not docs:
            return None, None

        # --- Filter generic HR boilerplate only ---
        banned_phrases = [
            "equal opportunity employer",
            "code of conduct",
            "drug and alcohol policy",
            "safety regulations",
            "driving under the influence",
            "sexual harassment policy",
            "this handbook does not constitute",
            "employment at will",
        ]
        filtered_docs = [
            d for d in docs if d and not any(bad in d.lower() for bad in banned_phrases)
        ]

        if not filtered_docs:
            return None, None

        # --- High recall (no reranking) ---
        context = "\n\n".join(filtered_docs[:4])
        return context[:5000], metas

    except Exception as e:
        st.error(f"❌ Retrieval error: {e}")
        return None, None



def stream_answer(context, question):
    # --- Contextual memory from chat history ---
    conversation_context = ""
    if "messages" in st.session_state and len(st.session_state.messages) > 0:
        recent_msgs = st.session_state.messages[-4:]
        conversation_context = "\n".join(
            [f"{m['role'].capitalize()}: {m['content']}" for m in recent_msgs]
        )

    # --- Early response for casual greetings ---
    greetings = ["hi", "hello", "hey", "what's up", "whats up", "yo", "sup", "how are you", "good morning", "good afternoon", "good evening"]
    if question.strip().lower() in greetings:
        response = (
            "Hello! I’m FrontShiftAI, your company’s HR assistant. "
            "You can ask me questions about company policies such as PTO, holidays attendance, or leave rules. "
            "I’m here to help you understand your company handbook."
        )
        st.markdown(response)
        return response

    # --- Inappropriate content handling ---
    inappropriate_keywords = [
        "hit", "kill", "hurt", "fight", "violence", "harass", "abuse", "weapon",
        "dating", "love", "salary negotiation", "personal advice"
    ]
    if any(word in question.lower() for word in inappropriate_keywords):
        response = (
            "That’s not an appropriate workplace question. "
            "If this is about workplace behavior or safety, please remember that violence or harassment is strictly prohibited under company policy. "
            "If you need to report an incident, please contact your HR representative immediately."
        )
        st.markdown(response)
        return response

    # --- Clean irrelevant context lines ---
    banned_phrases = [
        "please contact human resources",
        "contact hr for more information",
        "for additional information",
        "refer to hr department",
        "reach out to your supervisor",
        "refer to the handbook",
    ]
    for phrase in banned_phrases:
        context = "\n".join(
            [line for line in context.splitlines() if phrase.lower() not in line.lower()]
        )

    # --- System prompt ---
    system_prompt = """
You are FrontShiftAI, the company’s professional HR assistant.
You are friendly, concise, and factual.

Guidelines:
- Answer strictly using the provided company handbook context.
- Respond only in complete sentences and paragraphs.
- Do NOT use bullet points, numbered lists, markdown, or special formatting.
- Maintain a neutral and professional tone — factual, not conversational.
- Do NOT refer users to the handbook — you *are* the handbook.
- If an answer truly cannot be found, respond exactly with:
  "I’m sorry, I couldn’t find details on that topic in the company handbook."
- For inappropriate, violent, or off-topic questions, give a professional HR-style safety reminder.
"""

    # --- Build structured prompt (includes contextual memory) ---
    prompt = f"""{system_prompt}

    ### Context (includes company handbook and recent conversation):
    {context}

    ### User Question:
    {question}

    Respond directly as the HR assistant, without repeating section headers.
    """


    # --- Stream model output ---
    output_container = st.empty()
    partial_text = ""
    try:
        for token in llm.create_completion(
            prompt=prompt,
            max_tokens=512,
            temperature=0.7,
            top_p=0.9,
            stream=True,
        ):
            chunk = token.get("choices", [{}])[0].get("text", "")
            if chunk:
                partial_text += chunk
                cleaned_stream = clean_output(partial_text)
                output_container.markdown(
                    f"<div style='font-family: Inter, sans-serif; white-space: pre-wrap; color: #FFFFFF;'>{cleaned_stream}▌</div>",
                    unsafe_allow_html=True
                )

        cleaned_final = clean_output(partial_text)
        output_container.markdown(
            f"<div style='font-family: Inter, sans-serif; white-space: pre-wrap; color: #FFFFFF;'>{cleaned_final}</div>",
            unsafe_allow_html=True
        )
        return cleaned_final


    except Exception as e:
        st.error(f" Model error: {e}")
        return "I’m sorry, something went wrong while processing your question."


if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# Handle new input
if query := st.chat_input("Ask about your company policies..."):
    # --- User message ---
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # --- Assistant message ---
    with st.chat_message("assistant"):
        recent_user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        if len(recent_user_msgs) > 1:
            combined_query = " ".join(recent_user_msgs[-2:])
        else:
            combined_query = query

        context, metas = query_docs(combined_query, company_name)
        if not context:
            answer = "I’m sorry, I couldn’t find details on that topic in the company handbook."
        else:
            answer = stream_answer(context, query)

        st.session_state.messages.append({"role": "assistant", "content": answer})
        msg_index = len(st.session_state.messages) - 1
