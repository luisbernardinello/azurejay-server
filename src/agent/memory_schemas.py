from typing import List, Optional
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    """This is the profile of the user you are chatting with."""
    name: Optional[str] = Field(description="The user's name", default=None)
    location: Optional[str] = Field(description="The user's location", default=None)
    interests: List[str] = Field(
        description="Topics the user is interested in discussing in English",
        default_factory=list,
    )

class GrammarCorrection(BaseModel):
    """Record of grammar corrections made for the user."""
    original_text: str = Field(description="The user's original text with errors")
    corrected_text: str = Field(description="The corrected version of the text")
    explanation: str = Field(description="Explanation of the grammar rules and corrections")
    improvement: str = Field(description="A more native-sounding rewrite of the user's text")