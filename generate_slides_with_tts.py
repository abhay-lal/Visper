import os
import sys
import base64
import wave
from io import BytesIO
from typing import List

from PIL import Image  # type: ignore
from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass


def ensure_adc() -> tuple[str, str]:
    credentials_path = os.getenv("VERTEX_AI_CREDENTIALS_PATH")
    if credentials_path and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(credentials_path)
    project_id = os.getenv("VERTEX_AI_PROJECT_ID")
    location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    if not project_id:
        print("Missing VERTEX_AI_PROJECT_ID in environment/.env")
        sys.exit(1)
    return project_id, location


def init_client() -> genai.Client:
    project_id, location = ensure_adc()
    return genai.Client(vertexai=True, project=project_id, location=location)


def save_image_from_part(image_part, output_path: str) -> None:
    # Try developer client route
    try:
        client = init_client()
        client.files.download(file=image_part)
        image_part.save(output_path)
        return
    except Exception:
        pass

    # Try direct bytes/data
    for attr in ["bytes", "image_bytes", "data"]:
        try:
            value = getattr(image_part, attr)
        except Exception:
            value = None
        if isinstance(value, (bytes, bytearray)):
            Image.open(BytesIO(bytes(value))).save(output_path)
            return
        if isinstance(value, str) and attr.endswith("bytes"):
            try:
                Image.open(BytesIO(base64.b64decode(value))).save(output_path)
                return
            except Exception:
                pass

    # Try data URI
    try:
        uri = getattr(image_part, "uri")
    except Exception:
        uri = None
    if isinstance(uri, str) and uri.startswith("data:") and ";base64," in uri:
        Image.open(BytesIO(base64.b64decode(uri.split(",", 1)[1]))).save(output_path)
        return

    raise RuntimeError("Unable to save image from part; no bytes/URI available")


def generate_images(prompt: str, count: int = 4, out_dir: str = ".") -> List[str]:
    client = init_client()
    response = client.models.generate_images(
        model="imagen-4.0-generate-001",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=count,
        ),
    )
    paths: List[str] = []
    for idx, generated_image in enumerate(response.generated_images, start=1):
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"slide_{idx}.png")
        save_image_from_part(generated_image.image, output_path)
        paths.append(output_path)
    return paths


def generate_images_for_slides(shared_material: str, slide_prompts: List[str], out_dir: str = ".") -> List[str]:
    client = init_client()
    paths: List[str] = []
    for idx, slide_prompt in enumerate(slide_prompts, start=1):
        prompt = f"{shared_material}\nSlide {idx}: {slide_prompt}"
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            ),
        )
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"slide_{idx}.png")
        save_image_from_part(response.generated_images[0].image, output_path)
        paths.append(output_path)
    return paths


def wave_file(filename: str, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> None:
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def generate_tts(text: str, voice_name: str = "Kore", outfile: str = "narration.wav") -> str:
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
    wave_file(outfile, data)
    return outfile


def main() -> None:
    # 1) Generate slides
    prompt = os.getenv("SLIDES_PROMPT", "Robot holding a red skateboard")
    count = int(os.getenv("SLIDES_COUNT", "4"))
    slides = generate_images(prompt, count)
    print("Slides:")
    for p in slides:
        print(p)

    # 2) Generate narration
    narration_text = os.getenv("TTS_TEXT", "Say cheerfully: Have a wonderful day!")
    voice = os.getenv("TTS_VOICE", "Kore")
    wav = generate_tts(text=narration_text, voice_name=voice, outfile=os.getenv("TTS_OUT", "narration.wav"))
    print(f"Saved narration to {wav}")


if __name__ == "__main__":
    main()


