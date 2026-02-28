import os
import io
import tempfile
import time
from pydub import AudioSegment
from pydub.utils import make_chunks
import streamlit as st
from fpdf import FPDF
from datetime import datetime
import subprocess

# Import Pydantic models for type hinting and PDF rendering
from modules.models import LectureQuiz

# Use 15-minute chunks for manageable API calls and progress reporting
CHUNK_LENGTH_MS = 900000  # 15 minutes in milliseconds

def save_uploaded_file(uploaded_file):
    """Saves uploaded Streamlit file to a temporary location for processing."""
    # Streamlit Cloud uses an ephemeral file system, so /tmp is the safe location
    file_name = f"{time.time()}_{uploaded_file.name}"
    file_path = os.path.join(tempfile.gettempdir(), file_name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def extract_audio_if_video(file_path, temp_audio_path):
    """Converts video files to MP3 audio using a direct ffmpeg call for memory efficiency."""
    if not file_path.lower().endswith(('.mp4', '.mov', '.avi')):
        os.rename(file_path, temp_audio_path)
        return temp_audio_path

    st.info("Video file detected. Extracting audio with ffmpeg...")
    
    try:
        # Command to extract audio using ffmpeg
        command = [
            "ffmpeg",
            "-i", file_path,
            "-vn",  # No video
            "-acodec", "libmp3lame", # More compatible mp3 codec
            "-y", # Overwrite output file if it exists
            temp_audio_path
        ]
        
        # Execute the command
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        
        # Delete the original video file after successful extraction
        os.remove(file_path)
        
        return temp_audio_path
        
    except subprocess.CalledProcessError as e:
        # If ffmpeg fails, log the error and raise an exception
        st.error(f"ffmpeg error: {e.stderr}")
        # Clean up the original file if it still exists
        if os.path.exists(file_path):
            os.remove(file_path)
        raise Exception(f"Audio extraction failed. ffmpeg error: {e.stderr}") from e
    except Exception as e:
        st.error(f"Error extracting audio from video: {e}")
        # Clean up the original file if it still exists
        if os.path.exists(file_path):
            os.remove(file_path)
        raise


def chunk_audio_file(audio_path, progress_text):
    """
    Chunks large audio files into smaller segments using pydub.[4, 5]
    Returns a list of temporary file paths for the chunks.
    """
    temp_chunk_files = []
    file_handle = None
    try:
        # Open the file and pass the handle to pydub to prevent file locking issues on Windows
        file_handle = open(audio_path, 'rb')
        audio = AudioSegment.from_file(file_handle)
        
        # Close the handle once the audio is loaded into memory
        file_handle.close()
        file_handle = None

        chunks = make_chunks(audio, CHUNK_LENGTH_MS)
        total_chunks = len(chunks)
        
        progress_text.text(f"Splitting audio into {total_chunks} chunks ({CHUNK_LENGTH_MS/60000:.0f} min each)...")

        for i, chunk in enumerate(chunks):
            # Use WAV format for reliable transcription
            chunk_name = os.path.join(tempfile.gettempdir(), f"chunk_{i}_{time.time()}.wav")
            
            # Export the chunk to a temporary file
            chunk.export(chunk_name, format="wav")
            temp_chunk_files.append(chunk_name)
        
        # Delete the single large audio file
        os.remove(audio_path)
        
        progress_text.text(f"Audio chunking complete. Ready to upload and transcribe.")
        return temp_chunk_files

    except Exception as e:
        st.error(f"Error during audio chunking (check FFmpeg/pydub setup): {e}")
        # Ensure cleanup of any partial chunks
        for f in temp_chunk_files:
            if os.path.exists(f):
                os.remove(f)
        
        # Explicitly close file handle if it's still open on error
        if file_handle:
            file_handle.close()
            
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise

# --- PDF Export Logic ---

class PDFGenerator(FPDF):
    """Custom FPDF class for professional document generation."""
    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "Lecture Voice-to-Notes Study Guide", 0, 1, "L")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d')}", 0, 1, "L")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        # {nb} is replaced by the total page count [6]
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", 0, 0, "C")

    def chapter_title(self, title):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, title, 0, 1, "L")
        self.line(self.get_x(), self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)

    def print_markdown(self, text, style=""):
        """Prints long text, handling line and page breaks automatically.[7, 6]"""
        self.set_font("Helvetica", style, 12)
        # Replace characters that are not supported by the default font
        safe_text = text.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 5, safe_text)
        self.ln(5)

def create_pdf(transcript, summary, quiz_obj: LectureQuiz):
    """Compiles all outputs into a single PDF document."""
    pdf = PDFGenerator()
    pdf.alias_nb_pages() # Enable {nb} alias for page numbering
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- 1. Full Transcript ---
    pdf.add_page()
    pdf.chapter_title("I. Full Lecture Transcript")
    pdf.print_markdown(transcript)

    # --- 2. Study Notes Summary ---
    pdf.add_page()
    pdf.chapter_title("II. Concise Study Notes")
    pdf.print_markdown(summary)

    # --- 3. Quiz and Flashcards ---
    pdf.add_page()
    pdf.chapter_title(f"III. Assessment Questions: {quiz_obj.title}")
    
    answer_key_content = ""
    
    # Content loop
    for i, q in enumerate(quiz_obj.questions):
        q_num = i + 1
        
        pdf.set_font("Arial", "B", 12)
        pdf.multi_cell(0, 7, f"Q{q_num}. {q.question_text}", 0, 'J')
        pdf.ln(2)
        
        pdf.set_font("Times", "", 11)

        if q.question_type == "multiple_choice" and q.options:
            correct_option = next((opt.option_text for opt in q.options if opt.is_correct), "N/A")
            options_str = ""
            for idx, opt in enumerate(q.options):
                # Use letters A, B, C, D for MCQs
                label = chr(65 + idx)
                options_str += f"{label}. {opt.option_text}\n"
            pdf.multi_cell(0, 5, options_str, 0, 'L')
            
            answer_key_content += f"Q{q_num} (MCQ): Correct Answer is {correct_option}.\nExplanation: {q.rationale}\n\n"
            
        elif q.question_type == "flashcard":
             pdf.multi_cell(0, 5, "Type: Flashcard/Key Concept (Answer in Key)", 0, 'L')
             answer_key_content += f"Q{q_num} (Flashcard): Concept: {q.question_text}\nDefinition/Answer: {q.options[0].option_text if q.options else 'N/A'}\nExplanation: {q.rationale}\n\n"
        
        pdf.ln(5)
        
    # --- 4. Answer Key ---
    pdf.add_page()
    pdf.chapter_title("IV. Answer Key")
    pdf.print_markdown(answer_key_content)

    # Output PDF as a byte stream for Streamlit download button
    return bytes(pdf.output(dest='B'))