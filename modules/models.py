from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- Nested Schema for Quiz Options ---
class QuizOption(BaseModel):
    """A single multiple-choice option."""
    option_text: str = Field(description="The text of the multiple-choice option.")
    is_correct: bool = Field(description="True if this is the correct answer, False otherwise.")

# --- Schema for a Single Question (MCQ or Flashcard) ---
class QuizQuestion(BaseModel):
    """Schema for a single multiple-choice question or flashcard."""
    # Enforce type using Literal for structure adherence [2]
    question_type: Literal["multiple_choice", "flashcard"] = Field(
        description="Type of question: 'multiple_choice' or 'flashcard'."
    )
    question_text: str = Field(description="The main question text derived from the lecture content.")
    options: Optional[List[QuizOption]] = Field(
        default=None,
        description="List of options for multiple choice questions. Must contain exactly one correct answer."
    )
    rationale: str = Field(description="A brief explanation (1-2 sentences) of the correct answer or concept.")

# --- Master Schema for the Entire Quiz ---
class LectureQuiz(BaseModel):
    """Schema for the entire generated quiz."""
    title: str = Field(description="A descriptive title for the quiz derived from the lecture content.")
    questions: List[QuizQuestion]