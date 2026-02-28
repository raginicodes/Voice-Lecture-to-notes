import streamlit as st
import os
import tempfile
import time
from dotenv import load_dotenv

# Import Custom Modules
from modules.core_services import GeminiService
from modules.utilities import (
    save_uploaded_file, 
    extract_audio_if_video, 
    chunk_audio_file, 
    create_pdf
)
from modules.models import LectureQuiz

# Load environment variables for local testing
load_dotenv()

# --- Configuration and Initialization ---
st.set_page_config(layout="wide", page_title="Lecture Voice-to-Notes Generator")

# Session State Initialization
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'quiz_obj' not in st.session_state:
    st.session_state.quiz_obj = None

# Ensure service is initialized only once
if 'gemini_service' not in st.session_state:
    try:
        st.session_state.gemini_service = GeminiService()
    except Exception as e:
        st.error(f"Failed to initialize Gemini Client: {e}")

def clear_session():
    """Clears all processing results for a new run."""
    st.session_state.processing_complete = False
    st.session_state.transcript = None
    st.session_state.summary = None
    st.session_state.quiz_obj = None
    # Re-initialize service to ensure connection if possible
    st.session_state.gemini_service = GeminiService()

# --- Streamlit UI Layout ---
st.title("🎓 Lecture Voice-to-Notes Generator")

if not os.getenv("GEMINI_API_KEY"):
    st.error("🚨 Configuration Error: `GEMINI_API_KEY` is not set. Please set it in your local `.env` file or Streamlit Secrets.")

st.markdown("""
Upload an audio or video lecture file. The system will process large files using the Gemini Files API, 
transcribe the content, generate concise study notes, and create structured quiz questions.
""")

uploaded_file = st.file_uploader(
    "Upload Lecture File (.mp3,.mp4,.wav,.mov, etc.)",
    type=["mp3", "mp4", "wav", "m4a", "mov"],
    on_change=clear_session 
)

process_button = st.button("Generate Notes and Quiz", disabled=not uploaded_file or not os.getenv("GEMINI_API_KEY"))

# --- Main Processing Logic ---
if process_button and uploaded_file:
    clear_session()
    
    # Containers for progress updates and final output
    progress_container = st.empty()
    progress_bar = progress_container.progress(0, text="Initializing processing...")
    progress_text = st.empty()
    
    # Initial file paths
    input_path = None
    temp_audio_path = os.path.join(tempfile.gettempdir(), f"temp_audio_{time.time()}.mp3")
    
    try:
        service = st.session_state.gemini_service

        # Step 1: Save and Preprocess Media
        progress_text.text("Step 1/5: Saving and preparing media file...")
        input_path = save_uploaded_file(uploaded_file)
        audio_path = extract_audio_if_video(input_path, temp_audio_path)
        progress_bar.progress(0.1, text="Media ready.")

        # Step 2: Audio Chunking (Preparation for Files API upload)
        progress_text.text("Step 2/5: Analyzing audio and chunking...")
        chunk_paths = chunk_audio_file(audio_path, progress_text)
        progress_bar.progress(0.5, text="Audio chunking complete.")
        
        # Step 3: Speech-to-Text (STT) Transcription
        progress_text.text(f"Step 3/5: Transcribing {len(chunk_paths)} audio chunks via Files API...")
        st.session_state.transcript = service.transcribe_full_audio(chunk_paths, progress_bar, progress_text)
        
        if st.session_state.transcript == "Transcription failed.":
            raise Exception("Transcription failed. Check API key and quota.")

        progress_bar.progress(0.8, text="Transcription complete!")
        
        # Step 4: Summarization
        progress_text.text("Step 4/5: Generating study notes...")
        st.session_state.summary = service.generate_summary(st.session_state.transcript)
        progress_bar.progress(0.9, text="Study notes generated.")

        # Step 5: Quiz Generation (Structured Output)
        progress_text.text("Step 5/5: Generating structured quiz...")
        st.session_state.quiz_obj = service.generate_quiz(st.session_state.transcript)
        progress_bar.progress(1.0, text="All processing complete!")
        
        st.session_state.processing_complete = True
        
    except Exception as e:
        progress_container.empty()
        st.session_state.processing_complete = False
        st.error(f"A critical error occurred during processing. Please check logs and API key/quota: {e}")
        # Final cleanup attempt for any lingering local files if process failed
        if input_path and os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(temp_audio_path): os.remove(temp_audio_path)


# --- Output Display and Download ---
if st.session_state.processing_complete:
    
    st.success("✅ Lecture processing finished successfully!")
    
    # PDF Download Button
    if st.session_state.quiz_obj and st.session_state.summary and st.session_state.transcript:
        pdf_bytes = create_pdf(
            st.session_state.transcript,
            st.session_state.summary,
            st.session_state.quiz_obj
        )
        st.download_button(
            label="⬇️ Download Complete Study Guide (PDF)",
            data=pdf_bytes,
            file_name="Lecture_Study_Guide.pdf",
            mime="application/pdf"
        )
    
    # Tabbed Display
    tab_notes, tab_quiz, tab_transcript = st.tabs(["Study Notes", "Quiz/Flashcards", "Full Transcript"])

    with tab_notes:
        st.header("Concise Study Notes")
        st.markdown(st.session_state.summary)

    with tab_quiz:
        st.header("Quiz and Flashcards")
        
        if st.session_state.quiz_obj:
            quiz_data: LectureQuiz = st.session_state.quiz_obj
            st.subheader(quiz_data.title)

            for i, q in enumerate(quiz_data.questions):
                st.markdown(f"**Q{i+1}.** {q.question_text}")
                
                if q.question_type == "multiple_choice" and q.options:
                    # Display options
                    for idx, opt in enumerate(q.options):
                        label = chr(65 + idx)
                        st.markdown(f" - **{label}**: {opt.option_text}")
                    
                    with st.expander("Show Answer"):
                        correct_option = next((opt.option_text for opt in q.options if opt.is_correct), "N/A")
                        st.markdown(f"**Correct Answer:** {correct_option}")
                        st.markdown(f"**Explanation:** {q.rationale}")
                        
                elif q.question_type == "flashcard":
                    st.info("Flashcard/Key Concept. Test yourself on the definition below.")
                    with st.expander("Show Definition/Answer"):
                        # For flashcards, the answer is stored in the single QuizOption in the list
                        answer_text = q.options[0].option_text if q.options else "N/A"
                        st.markdown(f"**Answer:** {answer_text}")
                        st.markdown(f"**Explanation:** {q.rationale}")
                
                st.markdown("---")
        else:
            st.warning("Quiz generation failed or returned no data.")

    with tab_transcript:
        st.header("Raw Transcript")
        st.code(st.session_state.transcript, language='text')

