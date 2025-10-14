from pydantic import BaseModel, Field
from typing import List, Optional

class WebSearch(BaseModel):
    """Use this tool to search for information on the web."""
    query: str = Field(description="The question to be searched.")

class UpdateUserProfile(BaseModel):
    """
    Use this tool to UPDATE a user's profile with NEW information.
    This tool adds information; it does not replace the entire profile.
    """
    name: Optional[str] = Field(default=None, description="The user's new name, if mentioned.")
    location: Optional[str] = Field(default=None, description="The user's new location, if mentioned.")
    interests_to_add: Optional[List[str]] = Field(
        default=None, 
        description="A list containing ONLY THE NEW interests to be ADDED to the profile. Do not repeat interests that may already exist."
    )

class SaveGrammarCorrection(BaseModel):
    """Use this tool to SAVE an identified grammar correction."""
    original_text: str
    corrected_text: str
    explanation: str
    improvement: str