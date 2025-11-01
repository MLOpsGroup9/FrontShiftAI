import streamlit as st
from core.preload import get_model, get_collection
import re

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



import re

# Derive display name from email
display_name = user_email.split("@")[0].replace(".", " ").title()

# Function to add spaces and title case the company name
def format_company_name(name):
    # Replace underscores with spaces
    name = name.replace("_", " ").strip()

    # If it's a single lowercase word like "crousemedicalpractice"
    if name.islower() and " " not in name:
        # Try to split at transitions between letters (e.g. medicalpractice -> Medical Practice)
        # We'll insert a space before sequences of uppercase or by length grouping
        parts = re.findall(r"[A-Z]?[a-z]+", name)
        name = " ".join(parts).title()

    # Handle mixed or camel case words like "CrouseMedicalPractice"
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



llm = get_model()
collection = get_collection()



def query_docs(query, company):
    try:
        # Normalize company name for flexible matching
        normalized_company = company.lower().replace(" ", "").replace("_", "")

        # Fetch all metadata once (lightweight, just names)
        all_meta = collection.get(include=["metadatas"])

        # Try to find the correct company key by fuzzy matching
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

        # Perform the actual semantic query for that company
        results = collection.query(
            query_texts=[query],
            where={"company": {"$eq": possible_company}},
            n_results=10,  # fetch more chunks to improve context
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        if not docs:
            return None, None

        # --- Filter out irrelevant or generic handbook sections ---
        filtered_docs = []
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
        for d in docs:
            if not d or not d.strip():
                continue
            if any(bad_phrase in d.lower() for bad_phrase in banned_phrases):
                continue
            filtered_docs.append(d)

        if not filtered_docs:
            return None, None

        # --- Simple reranking by keyword overlap for precision ---
        ranked_docs = sorted(
            filtered_docs,
            key=lambda x: sum(word in x.lower() for word in query.lower().split()),
            reverse=True,
        )

        # --- Join top 4 for the final context ---
        context = "\n\n".join(ranked_docs[:4])
        return context[:5000], metas

    except Exception as e:
        st.error(f"❌ Retrieval error: {e}")
        return None, None




def stream_answer(context, question):
    # --- Early response for casual greetings ---
    greetings = ["hi", "hello", "hey", "what's up", "whats up", "yo", "sup", "how are you", "good morning", "good afternoon", "good evening"]
    if question.strip().lower() in greetings:
        response = (
            "Hello! I’m **FrontShiftAI**, your company’s HR assistant. "
            "You can ask me questions about company policies such as **PTO**, **holidays**, **attendance**, or **leave rules**. "
            "I’m here to help you understand your company handbook."
        )
        st.markdown(response)
        return response

    # --- Check for inappropriate or off-topic content ---
    inappropriate_keywords = [
        "hit", "kill", "hurt", "fight", "violence", "harass", "abuse", "weapon",
        "dating", "love", "salary negotiation", "personal advice"
    ]
    if any(word in question.lower() for word in inappropriate_keywords):
        response = (
            "That’s not an appropriate workplace question. "
            "If this is about **workplace behavior or safety**, please remember that **violence or harassment is strictly prohibited** under company policy. "
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

    # --- Refined system prompt ---
    system_prompt = """
You are FrontShiftAI, the company’s professional HR assistant.
You are friendly, concise, and factual.

Guidelines:
- Answer questions using only the provided company handbook context.
- You represent HR: maintain professionalism and empathy.
- Do NOT refer users to the handbook — you *are* the handbook.
- If an answer truly cannot be found, respond with:
  "I’m sorry, I couldn’t find details on that topic in the company handbook."
- For inappropriate, violent, or off-topic questions, give a professional HR-style safety reminder.
- Use **bold** for key terms and bullet points for clarity.
"""

    # --- Build structured prompt ---
    prompt = f"{system_prompt}\n\n### Company Handbook Context:\n{context}\n\n### Employee Question:\n{question}\n\n### HR Assistant Answer:\n"

    # --- Stream the model output ---
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
                output_container.markdown(partial_text + "▌")

        output_container.markdown(partial_text.strip())
        return partial_text.strip()

    except Exception as e:
        st.error(f"❌ Model error: {e}")
        return "I’m sorry, something went wrong while processing your question."

   


if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new input
if query := st.chat_input("Ask about your company policies..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        context, metas = query_docs(query, company_name)
        if not context:
            answer = "I’m sorry, I couldn’t find details on that topic in the company handbook."
        else:
            # ✅ Stream output directly from LLaMA
            answer = stream_answer(context, query)

    st.session_state.messages.append({"role": "assistant", "content": answer})
