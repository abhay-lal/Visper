import os
import sys
import wave
from typing import Optional

from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass


def wave_file(filename: str, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> None:
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def init_client() -> genai.Client:
    credentials_path = os.getenv("VERTEX_AI_CREDENTIALS_PATH")
    if credentials_path and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(credentials_path)

    project_id = os.getenv("VERTEX_AI_PROJECT_ID")
    location = os.getenv("VERTEX_AI_LOCATION", "us-central1")

    if not project_id:
        print("Missing VERTEX_AI_PROJECT_ID in environment/.env")
        sys.exit(1)

    return genai.Client(vertexai=True, project=project_id, location=location)


def _tts_gemini(text: str, voice_name: str) -> bytes:
    client = init_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name,
                    )
                )
            ),
        ),
    )
    part = response.candidates[0].content.parts[0]
    data = getattr(getattr(part, "inline_data", None), "data", None)
    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data)
    return data


def _tts_cloud(text: str, voice_name: str) -> bytes:
    # Fallback using Google Cloud Text-to-Speech
    try:
        from google.cloud import texttospeech  # type: ignore
    except Exception:
        print("Missing dependency google-cloud-texttospeech. Install with: pip install google-cloud-texttospeech")
        sys.exit(1)

    client = texttospeech.TextToSpeechClient()
    # Map Gemini voice to Cloud TTS voice if needed; default to en-US-Neural2-C
    mapped_voice = {
        "Kore": "en-US-Neural2-C",
    }.get(voice_name, "en-US-Neural2-C")

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name=mapped_voice,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=24000,
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    return response.audio_content


def generate_tts(text: str, voice_name: str = "Kore", outfile: str = "out.wav", backend: str = "auto") -> str:
    data: Optional[bytes] = None
    if backend in ("auto", "gemini"):
        try:
            data = _tts_gemini(text, voice_name)
        except Exception as e:
            # Fall back if not allowlisted or any Gemini error
            if backend == "gemini":
                print(f"Gemini TTS failed: {e}")
                sys.exit(1)
            data = None
    if data is None:
        data = _tts_cloud(text, voice_name)

    wave_file(outfile, data)
    return outfile


if __name__ == "__main__":
    text = os.getenv("TTS_TEXT", "Say cheerfully: Have a wonderful day!")
    out = generate_tts(text=text, voice_name=os.getenv("TTS_VOICE", "Kore"), outfile=os.getenv("TTS_OUT", "out.wav"))
    print(f"Saved TTS to {out}")


