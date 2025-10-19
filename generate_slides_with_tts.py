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


def _use_developer_api_env() -> bool:
    return os.getenv("USE_DEVELOPER_API", "").lower() in {"1", "true", "yes"}


def init_client(use_developer: bool | None = None) -> genai.Client:
    use_dev = _use_developer_api_env() if use_developer is None else use_developer
    if use_dev:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for Developer API (set in env or .env)")
        return genai.Client(api_key=api_key)
    project_id, location = ensure_adc()
    return genai.Client(vertexai=True, project=project_id, location=location)


def _default_image_model(use_developer: bool | None = None) -> str:
    use_dev = _use_developer_api_env() if use_developer is None else use_developer
    # Developer API Imagen model; adjust as needed for availability
    return "imagen-3.0-generate-001" if use_dev else "imagen-4.0-generate-001"


_CACHED_IMAGE_MODEL: str | None = None


def _resolve_developer_image_model(client: genai.Client, preferred: str | None) -> str:
    global _CACHED_IMAGE_MODEL
    if _CACHED_IMAGE_MODEL:
        return _CACHED_IMAGE_MODEL
    candidates = [
        m for m in [
            preferred,
            "imagen-3.0-generate-002",
            "imagen-3.0-generate-001",
            "imagen-3.0-fast",
            "imagen-3.0",
            "imagen-2.0-generate-001",
        ]
        if m
    ]
    try:
        # Try to list models and select by availability
        models = getattr(client.models, "list")()
        names: List[str] = []
        for md in models:
            # Accept both id and full resource names
            for attr in ("name", "model", "id"):
                try:
                    val = getattr(md, attr)
                except Exception:
                    val = None
                if isinstance(val, str):
                    names.append(val)
        def is_available(model_id: str) -> bool:
            for n in names:
                if n.endswith(model_id) or n == model_id or n.endswith("/" + model_id):
                    return True
            return False
        for cand in candidates:
            if is_available("models/" + cand) or is_available(cand):
                _CACHED_IMAGE_MODEL = cand
                return cand
        # Fallback: first imagen model found
        for n in names:
            if "imagen" in n:
                # Extract id after last '/'
                _CACHED_IMAGE_MODEL = n.split("/")[-1]
                return _CACHED_IMAGE_MODEL
    except Exception:
        # If listing fails, fall back to first candidate
        pass
    _CACHED_IMAGE_MODEL = candidates[0]
    return _CACHED_IMAGE_MODEL


def _is_gemini_image_model(model_id: str | None) -> bool:
    if not model_id:
        return False
    mid = model_id.lower()
    return mid.startswith("gemini-") and ("image" in mid)


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


def generate_images(prompt: str, count: int = 4, out_dir: str = ".", image_model: str | None = None, use_developer: bool | None = None) -> List[str]:
    client = init_client(use_developer=use_developer)
    model = image_model or _default_image_model(use_developer)
    if _use_developer_api_env() if use_developer is None else use_developer:
        model = _resolve_developer_image_model(client, model)

    os.makedirs(out_dir, exist_ok=True)
    paths: List[str] = []

    if _is_gemini_image_model(model):
        # Use generate_content; expect inline_data parts with image bytes
        for idx in range(1, count + 1):
            resp = client.models.generate_content(model=model, contents=[prompt])
            parts = getattr(getattr(resp.candidates[0], "content", None), "parts", []) if resp.candidates else []
            image_saved = False
            for part in parts:
                inline = getattr(part, "inline_data", None)
                if inline is not None and getattr(inline, "data", None):
                    img = Image.open(BytesIO(inline.data))
                    output_path = os.path.join(out_dir, f"slide_{idx}.png")
                    img.save(output_path)
                    paths.append(output_path)
                    image_saved = True
                    break
            if not image_saved:
                # Fallback: try text or skip
                output_path = os.path.join(out_dir, f"slide_{idx}.png")
                # Create a 1x1 placeholder if no image parts
                Image.new("RGB", (1, 1), color=(255, 255, 255)).save(output_path)
                paths.append(output_path)
        return paths

    # Imagen path
    response = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=count,
        ),
    )
    for idx, generated_image in enumerate(response.generated_images, start=1):
        output_path = os.path.join(out_dir, f"slide_{idx}.png")
        save_image_from_part(generated_image.image, output_path)
        paths.append(output_path)
    return paths


def generate_images_for_slides(shared_material: str, slide_prompts: List[str], out_dir: str = ".", image_model: str | None = None, use_developer: bool | None = None) -> List[str]:
    client = init_client(use_developer=use_developer)
    model = image_model or _default_image_model(use_developer)
    if _use_developer_api_env() if use_developer is None else use_developer:
        model = _resolve_developer_image_model(client, model)
    paths: List[str] = []
    os.makedirs(out_dir, exist_ok=True)
    for idx, slide_prompt in enumerate(slide_prompts, start=1):
        prompt = f"{shared_material}\nSlide {idx}: {slide_prompt}"
        output_path = os.path.join(out_dir, f"slide_{idx}.png")
        if _is_gemini_image_model(model):
            resp = client.models.generate_content(model=model, contents=[prompt])
            parts = getattr(getattr(resp.candidates[0], "content", None), "parts", []) if resp.candidates else []
            image_saved = False
            for part in parts:
                inline = getattr(part, "inline_data", None)
                if inline is not None and getattr(inline, "data", None):
                    img = Image.open(BytesIO(inline.data))
                    img.save(output_path)
                    paths.append(output_path)
                    image_saved = True
                    break
            if not image_saved:
                Image.new("RGB", (1, 1), color=(255, 255, 255)).save(output_path)
                paths.append(output_path)
            continue

        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            ),
        )
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


