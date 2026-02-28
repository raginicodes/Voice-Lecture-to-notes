# 🎤 Lecture Voice-to-Notes Generator

## 💡 Project Overview: The AI-Powered Study Assistant

The **Lecture Voice-to-Notes Generator** is an advanced AI-Powered Study Assistant designed to revolutionize the way students and professionals convert passive lecture recordings into actionable study materials. By integrating robust media handling with Google's Gemini API, this application automatically transcribes long video or audio files, generates concise academic study notes, and creates structured quizzes and flashcards for self-assessment.

## 🌐 Live Deployment
Try it yourself: [https://raginicodes-lvtng.streamlit.app/](https://lecture-to-voice-generator.streamlit.app/)


## ✨ Core Features & Technical Highlights

This Project is built around a resilient, multi-step pipeline designed to handle the complexities of real-world lecture files, including large file sizes and variable formats.

| Feature | Description | Key Technologies |
| :--- | :--- | :--- |
| **Multimodal Input** | Supports direct upload of various formats (`.mp4`, `.mov`, `.mp3`, `.wav`). `moviepy` extracts audio from video inputs seamlessly. | `Streamlit`, `moviepy` |
| **Scalable STT Processing** | Overcomes size limitations (Gemini's 20MB inline limit) by employing `pydub` to dynamically chunk audio into manageable segments. | `pydub`, `tempfile` |
| **Gemini Files API Workflow** | Implements the mandatory **Upload-Process-Delete** contract, staging chunks with `client.files.upload()` and rigorously deleting them immediately after transcription to manage the 20GB cloud quota. | `google-genai`, `try...finally` |
| **Abstractive Summarization** | Converts the full transcript into concise, structured study notes using the powerful generative capabilities of **Gemini 2.5 Flash**. | `Gemini 2.5 Flash` |
| **Structured Quiz Generation** | Generates reliable Multiple Choice Questions (MCQs) and flashcards by enforcing a strict Pydantic data schema, guaranteeing machine-readable JSON output. | `pydantic`, `Gemini Structured Output` |
| **Professional Export** | Provides a single-click download of the complete study guide (Transcript, Notes, Quiz, and Answer Key) as a professional, multi-page PDF document. | `fpdf2` |
| **Cloud Deployment Ready** | Architected for secure deployment on **Streamlit Cloud** using environment variables (`GEMINI_API_KEY`) managed via Streamlit Secrets. | `Streamlit`, `python-dotenv` |

## ⚙️ Technology Stack

| Category | Component | Purpose |
| :--- | :--- | :--- |
| **Frontend/Orchestration** | Python, Streamlit | UI, session state management, and workflow coordination. |
| **Artificial Intelligence** | Google Gemini 2.5 Flash | Core models for Transcription, Summarization, and Structured Output. |
| **File Processing** | `pydub`, `moviepy` | Audio chunking, segmentation, and video-to-audio extraction. **Requires FFmpeg.** |
| **Data Integrity** | `pydantic` | Defining schemas for reliable JSON output from the Gemini API. |
| **Export/Utilities** | `fpdf2`, `python-dotenv` | PDF generation and secure management of API keys. |

## 🏗️ Modular Architecture Diagram

````
The project uses a highly modular structure to maintain separation of concerns:
[User Upload MP4/MP3]
|
V
[streamlit\_app.py] (UI, State Mgmt)
|
V
[modules/utilities.py]
(1. Save File) -\> (2. Extract Audio) -\> (3. Chunk Audio)
|
V
[modules/core\_services.py] (Gemini Service)
(Chunk 1) --|
(Chunk 2) --| -\> (A. client.files.upload) -\> (B. Transcribe) -\> (C. client.files.delete)
(Chunk N) --|
|
V
[modules/core\_services.py]
(4. Merge Transcript) -\> (5. Summarize) -\> (6. Generate Quiz)
|
V
[streamlit\_app.py]
(7. Display in Tabs)
|
V
[modules/utilities.py] (PDF Generator)
(8. Download PDF)
````

## 🚀 Local Setup and Installation

Follow these steps to clone and run the application on your local machine.

### Prerequisites

1.  **Python 3.10+** installed.
2.  **FFmpeg** installed on your operating system and added to your system's PATH. This is a crucial non-Python dependency for `moviepy` and `pydub` to handle audio/video files.

### 1\. Clone the Repository

```bash
git clone [https://github.com/your-username/lecture_voice_to_notes.git](https://github.com/your-username/lecture_voice_to_notes.git)
cd lecture_voice_to_notes
````

### 2\. Create and Activate Virtual Environment

```bash
python -m venv venv
# Linux/macOS
source venv/bin/activate
# Windows (Command Prompt)
.\venv\Scripts\activate
```

### 3\. Install Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

### 4\. Configure API Key

Obtain your Gemini API Key from Google AI Studio.

Create a file named **`.env`** in the root directory and add your key:

```bash
#.env file content
GEMINI_API_KEY="AIzaSy...your...key...here"
```

### 5\. Run the Application

Execute the main Streamlit application:

```bash
streamlit run streamlit_app.py
```
The application will automatically open in your web browser, ready to process lecture files.

-----

## 🤝 Guidance and Contributors

This project was successfully completed as part of the **Edunet IBM Internship**, demonstrating the practical application of cutting-edge AI and cloud techniques under expert mentorship.

| Role | Name | LinkedIn Profile |
| :--- | :--- | :--- |
| **Intern/Developer** | Ragini Mishra |
| **Esteemed Guide** | Dr. Nanthini Mohan | [Profile Link](https://www.linkedin.com/in/dr-nanthini-mohan-9a727a105/) |

-----

*This project demonstrates proficiency in modern AI workflow design, cloud readiness, and large-scale data processing under the constraints of a robust, deployable MVP.*
