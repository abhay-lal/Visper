import argparse
import os
import re
from typing import List

from generate_tts import generate_tts
from generate_slides_with_tts import init_client


def read_blocks(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    if '---' in raw:
        blocks = [b.strip() for b in raw.split('---') if b.strip()]
    else:
        blocks = [b.strip() for b in re.split(r"\n\s*\n", raw) if b.strip()]
    return blocks


def auto_narration(slide_prompts: List[str], model: str, tone: str, sentences: str, max_chars: int) -> List[str]:
    client = init_client()
    n = len(slide_prompts)
    lines = [
        "You are writing spoken narration for a slide deck.",
        f"Return exactly {n} blocks, one per slide, in order.",
        f"Each block should be {sentences} sentences, natural and clear.",
        f"Aim for <= {max_chars} characters per block.",
        "Separate blocks with a line containing exactly three dashes: ---",
        "Do not number or label the blocks. Output only the blocks.",
        "Slides:",
    ]
    for i, sp in enumerate(slide_prompts, start=1):
        lines.append(f"Slide {i}: {sp}")
    prompt_text = "\n".join(lines)
    resp = client.models.generate_content(model=model, contents=prompt_text)
    raw_text = getattr(resp, "text", None) or ""
    blocks = [b.strip() for b in raw_text.split('---') if b.strip()]
    if len(blocks) < n:
        blocks = [b.strip() for b in re.split(r"\n\s*\n", raw_text) if b.strip()]
    if len(blocks) >= n:
        return blocks[:n]
    while len(blocks) < n:
        blocks.append(blocks[-1] if blocks else "")
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser(description="Audio agent: generate per-slide narration WAVs")
    parser.add_argument("--out_dir", default=os.getenv("OUT_DIR", "media"))
    parser.add_argument("--text_file", default=os.getenv("TTS_TEXT_FILE"))
    parser.add_argument("--auto_narration", action="store_true")
    parser.add_argument("--narration_model", default=os.getenv("NARRATION_MODEL", "gemini-2.5-flash-tts"))
    parser.add_argument("--narration_tone", default=os.getenv("NARRATION_TONE", "concise, friendly"))
    parser.add_argument("--narration_sentences", default=os.getenv("NARRATION_SENTENCES", "2-3"))
    parser.add_argument("--narration_max_chars", type=int, default=int(os.getenv("NARRATION_MAX_CHARS", "220")))
    parser.add_argument("--voice", default=os.getenv("TTS_VOICE", "Kore"))
    parser.add_argument("--tts_backend", default=os.getenv("TTS_BACKEND", "auto"))
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    slide_prompts_file = os.getenv("SLIDES_FILE")
    slide_prompts_env = [os.getenv(f"SLIDE_{i}") for i in range(1, 100) if os.getenv(f"SLIDE_{i}")]
    slide_prompts: List[str] = []
    if slide_prompts_file and os.path.exists(slide_prompts_file):
        with open(slide_prompts_file, "r", encoding="utf-8") as f:
            slide_prompts = [ln.strip() for ln in f if ln.strip()]
    elif slide_prompts_env:
        slide_prompts = slide_prompts_env

    per_slide_texts: List[str] = []
    if args.text_file and os.path.exists(args.text_file):
        per_slide_texts = read_blocks(args.text_file)
    elif args.auto_narration and slide_prompts:
        per_slide_texts = auto_narration(slide_prompts, args.narration_model, args.narration_tone, args.narration_sentences, args.narration_max_chars)
    else:
        raise SystemExit("Provide --text_file or --auto_narration with slide prompts via SLIDES_FILE/SLIDE_1..")

    wavs: List[str] = []
    for i, txt in enumerate(per_slide_texts, start=1):
        wav_path = os.path.join(args.out_dir, f"narration_{i}.wav")
        generate_tts(text=txt, voice_name=args.voice, outfile=wav_path, backend=args.tts_backend)
        wavs.append(wav_path)
    print("Generated:")
    for w in wavs:
        print(w)


if __name__ == "__main__":
    main()


