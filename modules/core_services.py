import os
import time
from google import genai
from google.genai import types
# from google.genai.errors import APIError
import streamlit as st
import json

from modules.models import LectureQuiz

# Use an efficient model with multimodal capability [9]
GEMINI_MODEL_STT = "gemini-2.5-flash"
GEMINI_MODEL_NLP = "gemini-2.5-flash"

class GeminiService:
    """Manages all interactions with the Google Gemini API."""
    def __init__(self):
        # Client automatically reads GEMINI_API_KEY from environment [10, 11]
        self.client = genai.Client()
        st.session_state.gemini_key_ok = True

    def _safe_gemini_call(self, func, *args, **kwargs):
        """
        Wrapper to handle API errors and implement exponential backoff retry logic.[12]
        """
        max_retries = 3
        delay = 1  # Initial delay in seconds

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    st.warning(f"Gemini API transient error (Attempt {attempt + 1}/{max_retries}). Retrying in {delay}s: {e}")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    st.error(f"Gemini API failed after {max_retries} attempts: {e}")
                    raise

    def _transcribe_chunk(self, chunk_path, uploaded_files_ref):
        """
        Transcribes a single audio chunk using the Files API (Upload -> Use -> Delete).[8, 13]
        Returns the transcript text.
        """
        # Upload the file to the Files API
        file_obj = self._safe_gemini_call(
            self.client.files.upload,
            file=chunk_path
        )
        uploaded_files_ref.append(file_obj)

        try:
            # Construct the multimodal prompt with the file object
            contents = [file_obj]

            # Call the model for transcription
            response = self._safe_gemini_call(
                self.client.models.generate_content,
                model=GEMINI_MODEL_STT,
                contents=contents
            )
            return response.text
        
        except Exception as e:
            st.error(f"Transcription failed for file {file_obj.name}: {e}")
            raise

        finally:
            # CRITICAL STEP: Delete the staged file immediately to prevent quota exhaustion [13]
            self.client.files.delete(name=file_obj.name)
            # Remove local temporary file
            if os.path.exists(chunk_path):
                 os.remove(chunk_path)

    def transcribe_full_audio(self, chunk_paths, progress_bar, progress_text):
        """Manages the full chunked transcription process."""
        full_transcript = ""
        total_chunks = len(chunk_paths)
        uploaded_files_ref = []  # Track file objects for cleanup safety

        st.warning(f"Starting transcription for {total_chunks} chunks. This may take several minutes and consumes tokens.")

        try:
            for i, chunk_path in enumerate(chunk_paths):
                progress_value = 0.5 + (i * 0.5) / total_chunks # Start progress after chunking (0.5)
                progress_text.text(f"Transcribing chunk {i + 1} of {total_chunks}...")
                
                chunk_transcript = self._transcribe_chunk(chunk_path, uploaded_files_ref)
                
                # Append with a space for seamless concatenation
                full_transcript += chunk_transcript.strip() + " "
                
                progress_bar.progress(progress_value, text=f"Transcription: {i+1} chunks complete.")
            
            return full_transcript.strip()

        except Exception as e:
            st.error(f"Full transcription pipeline failed: {e}")
            return "Transcription failed."

    def generate_summary(self, transcript):
        """Generates concise study notes (abstractive summary).[14, 15]"""
        st.info("Generating concise study notes...")
        
        summary_prompt = f"""
        You are an expert academic summarizer. Analyze the provided lecture transcript and synthesize the key concepts, definitions, and major arguments into a set of concise, high-quality study notes.
        
        Requirements:
        1. Use clear Markdown formatting: headings, bolding key terms, and bullet points.
        2. The output must be concise and easily digestible for a student studying for an exam.
        3. Do not invent information; summarize only what is present in the text.
        
        LECTURE TRANSCRIPT:
        ---
        {transcript}
        ---
        """
        
        response = self._safe_gemini_call(
            self.client.models.generate_content,
            model=GEMINI_MODEL_NLP,
            contents=[summary_prompt],
            config={"temperature": 0.3},
        )
        return response.text

    def generate_quiz(self, transcript):
        """Generates structured quizzes/flashcards using Pydantic schema.[2]"""
        st.info("Generating structured quiz and flashcards...")
        
        quiz_prompt = f"""
        Based solely on the following lecture transcript, generate exactly 5 multiple-choice questions and 5 flashcards. 
        The questions must cover the most important concepts and definitions presented.
        
        Ensure the output strictly adheres to the provided JSON Schema for the 'LectureQuiz' object.
        For flashcards, use the 'question_text' for the concept and the 'options' list with one element for the definition/answer.
        
        LECTURE TRANSCRIPT:
        ---
        {transcript}
        ---
        """
        
        # Enforce structured JSON output using the Pydantic model [2]
        response = self._safe_gemini_call(
            self.client.models.generate_content,
            model=GEMINI_MODEL_NLP,
            contents=[quiz_prompt],
            config={
                "temperature": 0.5,
                "response_mime_type": "application/json",
                "response_schema": LectureQuiz,
            },
        )
        
        # The SDK automatically validates and parses the JSON into a Pydantic object [2]
        return response.parsed