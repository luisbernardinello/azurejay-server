import requests
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class GrammarError(BaseModel):
    """Represents a grammar error found by LanguageTool"""
    message: str
    short_message: str
    offset: int
    length: int
    rule_id: str
    category: str
    replacements: List[str]
    context: str

class LanguageToolCorrection(BaseModel):
    """Complete correction information from LanguageTool"""
    original_text: str
    corrected_text: str
    errors: List[GrammarError]
    explanation: str
    timestamp: datetime

class LanguageToolAPI:
    """Client for LanguageTool API"""
    
    def __init__(self, base_url: str = "https://api.languagetoolplus.com/v2"):
        """
        Initialize LanguageTool API client
        
        Args:
            base_url: LanguageTool API base URL. You can use:
                     - Free public API: "https://api.languagetool.org/v2"
                     - Premium API: "https://api.languagetoolplus.com/v2"
        """
        self.base_url = base_url
        self.check_url = f"{base_url}/check"
    
    def check_text(self, text: str, language: str = "en-US", api_key: Optional[str] = None) -> LanguageToolCorrection:
        """
        Check text for grammar errors using LanguageTool API
        
        Args:
            text: Text to check
            language: Language code (e.g., 'en-US', 'pt-BR')
            api_key: API key for premium features (optional)
            
        Returns:
            LanguageToolCorrection object with errors and corrections
        """
        
        data = {
            'text': text,
            'language': language,
            'enabledOnly': 'false'
        }
        
        headers = {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        try:
            response = requests.post(self.check_url, data=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            errors = []
            corrected_text = text
            
            matches = sorted(result.get('matches', []), key=lambda x: x['offset'], reverse=True)
            
            for match in matches:
                error = GrammarError(
                    message=match.get('message', ''),
                    short_message=match.get('shortMessage', ''),
                    offset=match['offset'],
                    length=match['length'],
                    rule_id=match.get('rule', {}).get('id', ''),
                    category=match.get('rule', {}).get('category', {}).get('name', ''),
                    replacements=[r['value'] for r in match.get('replacements', [])],
                    context=match.get('context', {}).get('text', '')
                )
                errors.append(error)
                
                if error.replacements:
                    start = error.offset
                    end = error.offset + error.length
                    corrected_text = corrected_text[:start] + error.replacements[0] + corrected_text[end:]
            
            explanation = self._create_explanation(errors)
            
            return LanguageToolCorrection(
                original_text=text,
                corrected_text=corrected_text,
                errors=errors,
                explanation=explanation,
                timestamp=datetime.now()
            )
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling LanguageTool API: {e}")
            return LanguageToolCorrection(
                original_text=text,
                corrected_text=text,
                errors=[],
                explanation="Unable to check grammar at this time.",
                timestamp=datetime.now()
            )
        except Exception as e:
            print(f"Unexpected error in LanguageTool: {e}")
            return LanguageToolCorrection(
                original_text=text,
                corrected_text=text,
                errors=[],
                explanation="Unable to check grammar at this time.",
                timestamp=datetime.now()
            )
    
    def _create_explanation(self, errors: List[GrammarError]) -> str:
        """Create a human-friendly explanation of the errors found"""
        if not errors:
            return "No grammar errors found."
        
        if len(errors) == 1:
            error = errors[0]
            if error.replacements:
                return f"Found 1 error: {error.short_message or error.message}. Suggested correction: '{error.replacements[0]}'"
            else:
                return f"Found 1 error: {error.short_message or error.message}"
        
        # Multiple errors
        explanations = []
        for i, error in enumerate(errors, 1):
            if error.replacements:
                explanations.append(f"{i}. {error.short_message or error.message} → '{error.replacements[0]}'")
            else:
                explanations.append(f"{i}. {error.short_message or error.message}")
        
        return f"Found {len(errors)} errors:\n" + "\n".join(explanations)

    def has_errors(self, text: str, language: str = "en-US", api_key: Optional[str] = None) -> bool:
        """
        Quick check if text has grammar errors
        
        Args:
            text: Text to check
            language: Language code
            api_key: API key for premium features
            
        Returns:
            True if errors found, False otherwise
        """
        correction = self.check_text(text, language, api_key)
        return len(correction.errors) > 0

def check_grammar(text: str, language: str = "en-US", api_key: Optional[str] = None, base_url: str = "https://api.languagetool.org/v2") -> LanguageToolCorrection:
    """
    Convenience function to check grammar using LanguageTool
    
    Args:
        text: Text to check
        language: Language code (default: en-US)
        api_key: API key for premium features (optional)
        base_url: LanguageTool API URL
        
    Returns:
        LanguageToolCorrection object
    """
    api = LanguageToolAPI(base_url)
    return api.check_grammar(text, language, api_key)

