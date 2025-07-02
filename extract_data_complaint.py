"""
This script demonstrates how to use PydanticAI’s Agent to extract structured complaints
from free-form text using a Pydantic model schema.
"""

from enum import Enum
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field
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
    phone_number: str = Field(..., description="Phone number of the complainant")
    seriousness: Seriousness = Field(..., description="Seriousness level of the matter")
    potential_officials: List[str] = Field(
        default_factory=list,
        description="List of potential officials or employees involved",
    )


# Specify the LLM model and tell the Agent to output a Complaint instance
MODEL_NAME = "anthropic:claude-sonnet-4-0"
agent = Agent(
    MODEL_NAME,
    output_type=Complaint,  # 🚀 PydanticAI will validate and parse the LLM response into this model
)


def extract_complaint():
    """
    Read raw complaint text from file, invoke the PydanticAI Agent synchronously,
    and print the resulting structured Complaint in JSON format.
    """
    # Load the unstructured complaint text
    complaint_text = Path("demo_complaint.txt").read_text(encoding="utf-8")

    # Run the Agent: internally calls the LLM, then uses Pydantic to parse/validate
    result = agent.run_sync(complaint_text)

    # The Agent result contains a .output attribute typed as Complaint
    complaint: Complaint = result.output

    # Print out the structured data as JSON, with indentation for readability
    print(complaint.model_dump_json(indent=2))


if __name__ == "__main__":
    extract_complaint()
