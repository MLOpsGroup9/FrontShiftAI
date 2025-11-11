# pages/voice_chat.py
# Voice-only interaction page integrated with RAG system

import os
import time
import threading
import asyncio
import traceback
import queue
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write
from faster_whisper import WhisperModel
from dotenv import load_dotenv
from pydub import AudioSegment
import streamlit as st
import edge_tts
import pygame
import re
from core.preload import get_model, get_collection
from sentence_transformers import SentenceTransformer

# Check authentication
if "email" not in st.session_state or "company" not in st.session_state:
    st.switch_page("app.py")
    st.stop()

# ---------- Session State init ----------
if "voice_running" not in st.session_state:
    st.session_state.voice_running = False
if "voice_ai_speaking" not in st.session_state:
    st.session_state.voice_ai_speaking = False
if "voice_status" not in st.session_state:
    st.session_state.voice_status = "Idle"
if "voice_thread" not in st.session_state:
    st.session_state.voice_thread = None
if "voice_stop_event" not in st.session_state:
    st.session_state.voice_stop_event = threading.Event()
if "voice_messages" not in st.session_state:
    st.session_state.voice_messages = []
if "voice_error_msg" not in st.session_state:
    st.session_state.voice_error_msg = None
if "voice_debug_log" not in st.session_state:
    st.session_state.voice_debug_log = []
if "voice_status_queue" not in st.session_state:
    st.session_state.voice_status_queue = queue.Queue()
if "voice_message_queue" not in st.session_state:
    st.session_state.voice_message_queue = queue.Queue()

# ---------- Config ----------
load_dotenv()

SAMPLE_RATE = 16000
FRAME_DUR = 0.05
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_DUR)
MAX_SILENCE = 2.0
CALIBRATION_SEC = 0.5
VOICE_UP_MULT = 4.0
MIN_UTTER_SEC = 0.6
WHISPER_MODEL_NAME = "base.en"

# Initialize pygame mixer
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
except:
    pass

# Load RAG components
llm = get_model()
collection = get_collection()
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
company_name = st.session_state.company
user_email = st.session_state.email
display_name = user_email.split("@")[0].replace(".", " ").title()

# ---------- Page styling ----------
st.set_page_config(page_title="Voice Chat - FrontShiftAI", layout="wide", initial_sidebar_state="collapsed")

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
        .voice-header {text-align: center; margin: 30px 0 20px 0;}
        .voice-title {font-size: 2.8rem; font-weight: 700; color: #FFFFFF; margin-bottom: 10px;}
        .voice-subtitle {font-size: 1.3rem; color: #BBBBBB; margin-top: 5px;}
        .status-box {
            background: linear-gradient(135deg, #1e1e1e 0%, #2a2a2a 100%);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            margin: 25px 0;
            border: 1px solid #333;
        }
        .status-text {
            font-size: 1.5rem;
            font-weight: 600;
            color: #FFFFFF;
        }
        hr {border: 1px solid #333;}
    </style>
"""   

st.markdown(hide_sidebar_css, unsafe_allow_html=True)

# ---------- Helper functions ----------
def debug_log(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    try:
        st.session_state.voice_status_queue.put(("log", log_msg))
    except:
        pass

def set_status(text: str):
    try:
        st.session_state.voice_status_queue.put(("status", text))
    except:
        pass
    debug_log(f"Status: {text}")

def set_error(text: str):
    try:
        st.session_state.voice_status_queue.put(("error", text))
    except:
        pass
    debug_log(f"ERROR: {text}")

def add_message(role: str, text: str):
    try:
        st.session_state.voice_message_queue.put({"role": role, "text": text})
    except:
        pass

def write_wav_from_float(path: str, audio_f32: np.ndarray):
    audio_i16 = np.int16(np.clip(audio_f32, -1.0, 1.0) * 32767)
    wav_write(path, SAMPLE_RATE, audio_i16)

def clean_output(text):
    text = re.sub(r'[\\*_`~#]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ---------- RAG Query Function ----------
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
            return None, None

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

        banned_phrases = [
            "equal opportunity employer", "code of conduct", "drug and alcohol policy",
            "safety regulations", "driving under the influence", "sexual harassment policy",
            "this handbook does not constitute", "employment at will",
        ]
        filtered_docs = [
            d for d in docs if d and not any(bad in d.lower() for bad in banned_phrases)
        ]

        if not filtered_docs:
            return None, None

        context = "\n\n".join(filtered_docs[:4])
        return context[:5000], metas

    except Exception as e:
        debug_log(f"Retrieval error: {e}")
        return None, None

# ---------- Answer Generation ----------
def generate_answer(context, question):
    greetings = ["hi", "hello", "hey", "what's up", "whats up", "yo", "sup"]
    if question.strip().lower() in greetings:
        return "Hello! I'm FrontShiftAI, your company's HR assistant. Ask me about company policies like PTO, holidays, or attendance."

    inappropriate_keywords = [
        "hit", "kill", "hurt", "fight", "violence", "harass", "abuse", "weapon",
        "dating", "love", "salary negotiation"
    ]
    if any(word in question.lower() for word in inappropriate_keywords):
        return "That's not an appropriate workplace question. Please contact HR for sensitive matters."

    system_prompt = """
You are FrontShiftAI, a professional HR assistant.
Answer using the company handbook context.
Be concise and factual - respond in 2-3 sentences maximum for voice.
No bullet points or lists - only natural speech.
If you don't know, say: "I couldn't find that in the handbook."
"""

    prompt = f"""{system_prompt}

Context:
{context}

Question: {question}

Answer briefly and naturally:"""

    try:
        response = ""
        for token in llm.create_completion(
            prompt=prompt,
            max_tokens=200,
            temperature=0.7,
            stream=True,
        ):
            chunk = token.get("choices", [{}])[0].get("text", "")
            if chunk:
                response += chunk

        return clean_output(response)
    except Exception as e:
        debug_log(f"LLM error: {e}")
        return "I'm sorry, I encountered an error."

# ---------- Voice Functions ----------
def vad_listen_once(stop_event, ai_speaking_flag):
    debug_log("Listening...")
    
    while not stop_event.is_set() and ai_speaking_flag.get("speaking", False):
        time.sleep(0.05)
    
    if stop_event.is_set():
        return np.zeros((0, 1), dtype=np.float32)

    set_status("🎤 Listening...")
    buff = []
    silence_time = 0.0
    collecting = False

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, 
                           dtype="float32", blocksize=FRAME_SAMPLES) as stream:

            noise_frames = max(1, int(CALIBRATION_SEC / FRAME_DUR))
            noise_vals = []
            for _ in range(noise_frames):
                if stop_event.is_set():
                    return np.zeros((0, 1), dtype=np.float32)
                data, _ = stream.read(FRAME_SAMPLES)
                noise_vals.append(float(np.sqrt(np.mean(data**2)) + 1e-9))
            
            noise_rms = float(np.median(noise_vals))
            threshold = max(0.005, noise_rms * VOICE_UP_MULT)

            while not stop_event.is_set():
                if ai_speaking_flag.get("speaking", False):
                    return np.zeros((0, 1), dtype=np.float32)

                data, _ = stream.read(FRAME_SAMPLES)
                rms = float(np.sqrt(np.mean(data**2)) + 1e-9)

                if not collecting:
                    if rms >= threshold:
                        collecting = True
                        buff.append(data)
                        silence_time = 0.0
                        set_status(f"🎤 Recording...")
                else:
                    buff.append(data)
                    if rms < (threshold * 0.6):
                        silence_time += FRAME_DUR
                    else:
                        silence_time = 0.0
                    
                    if silence_time >= MAX_SILENCE:
                        break

    except Exception as e:
        set_error(f"Microphone error: {e}")
        return np.zeros((0, 1), dtype=np.float32)

    if not buff:
        return np.zeros((0, 1), dtype=np.float32)

    audio = np.concatenate(buff, axis=0)
    dur = audio.shape[0] / SAMPLE_RATE
    
    if dur < MIN_UTTER_SEC:
        return np.zeros((0, 1), dtype=np.float32)
    
    return audio

def transcribe_wav(path: str, model: WhisperModel) -> str:
    set_status("📝 Transcribing...")
    try:
        segments, info = model.transcribe(path, language="en")
        text = "".join(seg.text for seg in segments).strip()
        debug_log(f"Transcription: '{text}'")
        return text
    except Exception as e:
        debug_log(f"Transcription error: {e}")
        return ""

async def tts_to_mp3(text: str, out_path: str = "voice_out.mp3"):
    tts = edge_tts.Communicate(text, "en-US-JennyNeural")
    await tts.save(out_path)

def speak_blocking(text: str, ai_speaking_flag: dict):
    try:
        set_status("🔊 Generating speech...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(tts_to_mp3(text, "voice_out.mp3"))
        loop.close()

        sound = AudioSegment.from_mp3("voice_out.mp3")
        sound.export("voice_out.wav", format="wav")

        ai_speaking_flag["speaking"] = True
        set_status("🔊 Speaking...")

        pygame.mixer.music.load("voice_out.wav")
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.01)

        ai_speaking_flag["speaking"] = False
        
    except Exception as e:
        debug_log(f"TTS error: {e}")
        ai_speaking_flag["speaking"] = False

# ---------- Conversation Loop ----------
def conversation_loop(stop_event, running_flag, ai_speaking_flag):
    debug_log("=== VOICE CONVERSATION STARTED ===")
    model = None
    
    try:
        set_status("🚀 Loading Whisper model...")
        model = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
        debug_log("Model loaded!")
        set_status("✅ Ready! Say something...")
        
        iteration = 0
        while running_flag.get("running", False) and not stop_event.is_set():
            iteration += 1
            debug_log(f"=== Iteration {iteration} ===")
            
            audio_chunk = vad_listen_once(stop_event, ai_speaking_flag)
            
            if not running_flag.get("running", False) or stop_event.is_set():
                break

            if audio_chunk.shape[0] == 0:
                time.sleep(0.05)
                continue

            write_wav_from_float("voice_in.wav", audio_chunk)
            user_text = transcribe_wav("voice_in.wav", model)
            
            if not user_text:
                set_status("⚠️ No speech detected.")
                continue

            set_status(f"👤 You: {user_text}")
            add_message("user", user_text)

            # Query RAG system
            context, metas = query_docs(user_text, company_name)
            if not context:
                reply = "I couldn't find that information in the company handbook."
            else:
                reply = generate_answer(context, user_text)

            set_status(f"🤖 AI: {reply}")
            add_message("assistant", reply)

            speak_blocking(reply, ai_speaking_flag)
            set_status("🎤 Listening...")

    except Exception as e:
        debug_log(f"=== FATAL ERROR ===")
        debug_log(traceback.format_exc())
        set_error(f"Fatal error: {e}")

    finally:
        debug_log("=== LOOP ENDING ===")
        running_flag["running"] = False
        ai_speaking_flag["speaking"] = False
        try:
            stop_event.clear()
        except:
            pass
        set_status("⏹️ Stopped.")

# Process queued updates
def process_queues():
    try:
        while not st.session_state.voice_status_queue.empty():
            msg_type, msg_data = st.session_state.voice_status_queue.get_nowait()
            if msg_type == "status":
                st.session_state.voice_status = msg_data
            elif msg_type == "error":
                st.session_state.voice_error_msg = msg_data
            elif msg_type == "log":
                st.session_state.voice_debug_log.append(msg_data)
                if len(st.session_state.voice_debug_log) > 50:
                    st.session_state.voice_debug_log.pop(0)
    except:
        pass
    
    try:
        while not st.session_state.voice_message_queue.empty():
            msg = st.session_state.voice_message_queue.get_nowait()
            st.session_state.voice_messages.append(msg)
    except:
        pass

process_queues()

# ---------- UI ----------
st.markdown(f"""
    <div class="voice-header">
        <div class="voice-title">🎙️ Voice Chat</div>
        <div class="voice-subtitle">Hands-free HR Assistant for {display_name}</div>
    </div>
""", unsafe_allow_html=True)

if st.button("← Back to Text Chat", key="back_btn"):
    st.switch_page("pages/user_chat.py")

st.markdown("---")

if st.session_state.voice_error_msg:
    st.error(f"❌ {st.session_state.voice_error_msg}")
    if st.button("Clear Error"):
        st.session_state.voice_error_msg = None
        st.rerun()

col1, col2 = st.columns(2)

def start_clicked():
    if st.session_state.voice_running:
        return
    
    st.session_state.voice_error_msg = None
    st.session_state.voice_running = True
    st.session_state.voice_ai_speaking = False
    st.session_state.voice_stop_event.clear()
    
    running_flag = {"running": True}
    ai_speaking_flag = {"speaking": False}
    
    t = threading.Thread(
        target=conversation_loop,
        args=(st.session_state.voice_stop_event, running_flag, ai_speaking_flag),
        daemon=True
    )
    st.session_state.voice_thread = t
    t.start()

def stop_clicked():
    if not st.session_state.voice_running:
        return
    st.session_state.voice_running = False
    st.session_state.voice_stop_event.set()

with col1:
    st.button("▶️ Start Voice Chat", on_click=start_clicked, 
             disabled=st.session_state.voice_running, use_container_width=True)

with col2:
    st.button("⏹️ Stop Voice Chat", on_click=stop_clicked, 
             disabled=not st.session_state.voice_running, use_container_width=True)

# Status display
st.markdown(f"""
    <div class="status-box">
        <div class="status-text">{st.session_state.voice_status}</div>
    </div>
""", unsafe_allow_html=True)

# Running indicator
if st.session_state.voice_running:
    st.success("🟢 Voice chat is active - speak your question!")
else:
    st.info("⚪ Voice chat is idle - click Start to begin")

# Conversation history
if st.session_state.voice_messages:
    st.markdown("---")
    st.markdown("### 💬 Conversation History")
    for msg in st.session_state.voice_messages[-10:]:
        if msg["role"] == "user":
            st.markdown(f"**👤 You:** {msg['text']}")
        else:
            st.markdown(f"**🤖 AI:** {msg['text']}")

if st.session_state.voice_running:
    if st.button("🔄 Refresh Status"):
        st.rerun()

st.markdown("---")
st.caption("💡 **How to use:** Click Start, speak your question clearly, and pause for 2 seconds")
st.caption("🎤 The AI will search the company handbook and respond with voice")

# Debug panel
# with st.expander("🔧 Debug Logs"):
#     if st.session_state.voice_debug_log:
#         for log_entry in st.session_state.voice_debug_log[-15:]:
#             st.text(log_entry)
#     else:
#         st.text("No logs yet")