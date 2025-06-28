from pydantic import BaseModel, Field

class AgentResponse(BaseModel):
    """
    Defines the structured response expected from the LLM agent.
    """
    summary: str = Field(description="Concise American English summary of the user's request.")
    response_text: str = Field(description="The agent's response to the user (affirmation or polite refusal), in the original language of the request.")

    # Example for older Pydantic versions if needed, but Field is standard for v1.8+
    # class Config:
    #     schema_extra = {
    #         "example": {
    #             "summary": "User wants to know how to bake a cake.",
    #             "response_text": "Okay, I can help with that."
    #         }
    #     }
