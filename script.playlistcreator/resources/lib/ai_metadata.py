from mutagen import File as AudioFile
from resources.lib.utils import log

class AIMetadata:
    def extract_audio_metadata(self, filepath):
        audio = AudioFile(filepath)
        metadata = {key: audio.get(key, '') for key in audio.keys()}
        log(f"Extracted metadata from {filepath}: {metadata}")
        return metadata