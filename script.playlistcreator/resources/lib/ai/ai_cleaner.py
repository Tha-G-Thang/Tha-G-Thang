import re
from resources.lib.utils import log, get_setting, ai_log # Added ai_log

class AICleaner:
    def __init__(self):
        # AI models can be initialized here if needed for advanced cleaning (e.g., GPT-4)
        # For now, it will use regex and string operations.
        pass

    def clean_filename(self, filename, remove_words=None, switch_words=None, regex_enable=False, regex_pattern="", regex_replace=""):
        """
        Applies cleaning rules to a filename.
        Args:
            filename (str): The original filename.
            remove_words (list): List of words to remove.
            switch_words (list): List of 'old=new' pairs to replace.
            regex_enable (bool): Whether to apply regex replacement.
            regex_pattern (str): Regex pattern to find.
            regex_replace (str): String to replace with.
        Returns:
            str: The cleaned filename.
        """
        ai_log(f"AICleaner: Cleaning '{filename}' with remove_words={remove_words}, switch_words={switch_words}, regex_enable={regex_enable}")
        cleaned_filename = filename

        # General cleaning: replace common separators with spaces
        cleaned_filename = re.sub(r"[._-]", " ", cleaned_filename)

        # Apply remove words
        if remove_words:
            for word in remove_words:
                if word:
                    # Use word boundaries to prevent partial matches within words
                    cleaned_filename = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned_filename, flags=re.IGNORECASE).strip()
                    ai_log(f"AICleaner: After removing '{word}': '{cleaned_filename}'")

        # Apply switch words
        if switch_words:
            for switch_pair in switch_words:
                if '=' in switch_pair:
                    old, new = switch_pair.split('=', 1)
                    # Use re.escape for safety, but be aware it might escape too much for dynamic regex patterns
                    cleaned_filename = re.sub(re.escape(old), new, cleaned_filename, flags=re.IGNORECASE)
                    ai_log(f"AICleaner: After switching '{old}' to '{new}': '{cleaned_filename}'")

        # Apply regex replacement
        if regex_enable and regex_pattern:
            try:
                cleaned_filename = re.sub(regex_pattern, regex_replace, cleaned_filename, flags=re.IGNORECASE)
                ai_log(f"AICleaner: After regex '{regex_pattern}' -> '{regex_replace}': '{cleaned_filename}'")
            except re.error as e:
                log(f"AICleaner: Invalid regex pattern '{regex_pattern}': {e}", xbmc.LOGERROR)
            
        # Remove any multiple spaces and trim
        cleaned_filename = re.sub(r'\s+', ' ', cleaned_filename).strip()
        
        ai_log(f"AICleaner: Final cleaned filename: {filename} -> {cleaned_filename}")
        return cleaned_filename