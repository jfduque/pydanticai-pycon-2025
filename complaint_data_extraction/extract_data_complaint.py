import argparse
import json
from pathlib import Path
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError
from pydantic_ai import Agent


class Seriousness(Enum):
    """
    Enumeration of seriousness levels for a complaint.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Complaint(BaseModel):
    """
    Pydantic model defining the schema for a complaint.

    Fields:
    - full_name: Name of the complainant.
    - phone_number: Complainant’s contact number.
    - seriousness: Mapped to our Seriousness enum.
    - potential_officials: Optional list of involved officials or employees.
    """

    full_name: str = Field(..., description="Full name of the complainant")
    phone_number: Optional[str] = Field(
        None, description="Phone number of the complainant"
    )
    seriousness: Seriousness = Field(..., description="Seriousness level of the matter")
    potential_officials: List[str] = Field(
        default_factory=list,
        description="List of potential officials or employees involved",
    )


# Specify the LLM model and tell the Agent to output a Complaint instance
MODEL_NAME = "anthropic:claude-sonnet-4-0"
agent = Agent(
    MODEL_NAME,
    output_type=Complaint,
)


def extract_complaint(text: str, mode: str = "formal") -> Complaint:
    """
    Extract complaint based on mode:
      - formal: treat as a formal complaint note
      - transcript: treat as a customer service call transcript
    """
    # Always try direct JSON first
    try:
        data = json.loads(text)
        return Complaint.parse_obj(data)
    except (json.JSONDecodeError, ValidationError):
        pass

    if mode == "formal":
        prompt = text
    else:
        # Transcript processing: generic instructions
        transcript_instruction = (
            "You are given a transcript of a customer support call. "
            "Extract the details of the complaint from the customer's statements. "
            "Do NOT confuse the service agent(s) with the complainant."
        )
        prompt = f"{transcript_instruction}\n\n{text}"

    # Invoke PydanticAI Agent
    result = agent.run_sync(prompt)
    return result.output


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured complaint data from text or JSON file."
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the complaint text, structured JSON, or transcript file.",
    )
    parser.add_argument(
        "--mode",
        choices=["formal", "transcript"],
        default="formal",
        help="Extraction mode: 'formal' for letters, 'transcript' for call logs.",
    )
    args = parser.parse_args()

    raw_text = args.input_file.read_text(encoding="utf-8")
    try:
        complaint = extract_complaint(raw_text, mode=args.mode)
    except ValidationError as e:
        print("Error parsing complaint:", e)
        return

    # Output the structured data
    print(complaint.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
