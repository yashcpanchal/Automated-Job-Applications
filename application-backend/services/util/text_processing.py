import re
import string

def preprocess_text(text: str) -> str:
    """
    Preprocesses text
    """
    if not isinstance(text, str):
        return ""
    
    text = text.lower().strip()

    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))

    # White space normalization
    text = re.sub(r'\s+', ' ', text)
    

    return text

