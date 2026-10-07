from typing import Any


class SpeechService:
    """
    Application / Intelligence Layer: Speech Service
    Handles Speech-to-Text (STT) conversion for voice search queries.
    In Assignment 05/06 prototype, speech recognition is simulated by accepting
    spoken text directly or extracting transcribed text.
    """

    def transcribe(self, audio_input: Any) -> str:
        """
        Simulate Speech-to-Text (STT) recognition:
        Converts simulated audio input into clean transcription text.
        """
        if isinstance(audio_input, str):
            # Clean leading/trailing spaces and basic formatting
            return audio_input.strip()
        elif hasattr(audio_input, "text"):
            return str(audio_input.text).strip()
        elif isinstance(audio_input, dict) and "audio_text" in audio_input:
            return str(audio_input["audio_text"]).strip()
        return str(audio_input).strip()
