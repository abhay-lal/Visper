import argparse
import os
import sys
import importlib
import re
import json


def _upload_to_gcs(gcs_uri: str, local_path: str) -> str:
    if not gcs_uri.startswith("gs://"):
        raise ValueError("gcs_uri must start with gs://")
    try:
        from google.cloud import storage  # type: ignore
    except Exception:
        raise RuntimeError(
            "Missing dependency google-cloud-storage. Install with: pip install google-cloud-storage"
        )

    path = gcs_uri[len("gs://"):]
    if "/" not in path:
        raise ValueError("gcs_uri must be of form gs://bucket/obj")
    bucket_name, blob_name = path.split("/", 1)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)
    return gcs_uri


def main() -> None:
    parser = argparse.ArgumentParser(description="BlindVerse pipeline runner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # images
    p_img = sub.add_parser("images", help="Generate slides/images")
    p_img.add_argument("--prompt", default=os.getenv("SLIDES_PROMPT", "Robot holding a red skateboard"))
    p_img.add_argument("--count", type=int, default=int(os.getenv("SLIDES_COUNT", "4")))
    p_img.add_argument("--shared", default=os.getenv("SLIDES_SHARED", ""), help="Shared material included in every slide prompt")
    p_img.add_argument("--slide", action="append", default=None, help="Per-slide prompt; repeat flag for multiple slides")
    p_img.add_argument("--slides_file", default=None, help="Path to a text file with one slide prompt per line")
    p_img.add_argument("--use_developer_api", action="store_true", help="Use Google AI Studio Developer API (requires GOOGLE_API_KEY)")
    p_img.add_argument("--image_model", default=os.getenv("IMAGE_MODEL"), help="Override image model id")

    # tts
    p_tts = sub.add_parser("tts", help="Generate TTS WAV")
    p_tts.add_argument("--text", default=os.getenv("TTS_TEXT", "Say cheerfully: Have a wonderful day!"))
    p_tts.add_argument("--voice", default=os.getenv("TTS_VOICE", "Kore"))
    p_tts.add_argument("--out", default=os.getenv("TTS_OUT", "narration.wav"))
    p_tts.add_argument("--tts_backend", default=os.getenv("TTS_BACKEND", "auto"), choices=["auto", "gemini", "cloud"], help="Choose TTS backend")
    p_tts.add_argument("--out_dir", default=os.getenv("OUT_DIR", "media"), help="Directory to write narration/output files")

    # compose
    p_comp = sub.add_parser("compose", help="Compose slides and audio to MP4")
    p_comp.add_argument("--audio", default=os.getenv("COMPOSE_AUDIO", "narration.wav"))
    p_comp.add_argument("--out", default=os.getenv("COMPOSE_OUT", "slides_with_audio.mp4"))
    p_comp.add_argument("--seconds", type=float, default=float(os.getenv("SECONDS_PER_IMAGE", "2.0")))
    p_comp.add_argument("--out_dir", default=os.getenv("OUT_DIR", "media"), help="Directory to write output video")
    p_comp.add_argument("--gcs_uri", default=os.getenv("GCS_URI"), help="Upload final MP4 to this GCS URI (gs://bucket/path.mp4)")

    # all
    p_all = sub.add_parser("all", help="Run full pipeline: images -> TTS -> compose")
    p_all.add_argument("--shared", default=os.getenv("SLIDES_SHARED", ""), help="Shared material included in every slide prompt")
    p_all.add_argument("--slide", action="append", default=None, help="Per-slide prompt; repeat flag for multiple slides")
    p_all.add_argument("--slides_file", default=os.getenv("SLIDES_FILE"), help="Path to a text file with one slide prompt per line")
    p_all.add_argument("--slides_json", default=os.getenv("SLIDES_JSON"), help="Path to JSON or raw JSON to derive slide prompts")
    p_all.add_argument("--text", default=os.getenv("TTS_TEXT", "Say cheerfully: Have a wonderful day!"))
    p_all.add_argument("--text_file", default=os.getenv("TTS_TEXT_FILE"), help="Path to a text file for narration")
    p_all.add_argument("--voice", default=os.getenv("TTS_VOICE", "Kore"))
    p_all.add_argument("--tts_out", default=os.getenv("TTS_OUT", "narration.wav"))
    p_all.add_argument("--tts_backend", default=os.getenv("TTS_BACKEND", "auto"), choices=["auto", "gemini", "cloud"], help="Choose TTS backend")
    p_all.add_argument("--video_out", default=os.getenv("COMPOSE_OUT", "slides_with_audio.mp4"))
    p_all.add_argument("--seconds", type=float, default=float(os.getenv("SECONDS_PER_IMAGE", "2.0")))
    p_all.add_argument("--out_dir", default=os.getenv("OUT_DIR", "media"), help="Directory to write narration and video outputs")
    p_all.add_argument("--gcs_uri", default=os.getenv("GCS_URI"), help="Upload final MP4 to this GCS URI (gs://bucket/path.mp4)")
    # auto narration generation via Gemini text model
    p_all.add_argument("--auto_narration", action="store_true", help="Generate narration per slide via Gemini text model")
    p_all.add_argument("--narration_model", default=os.getenv("NARRATION_MODEL", "gemini-2.5-flash-tts"))
    p_all.add_argument("--narration_tone", default=os.getenv("NARRATION_TONE", "concise, friendly"))
    p_all.add_argument("--narration_sentences", default=os.getenv("NARRATION_SENTENCES", "2-3"), help="Target sentences per slide block")
    p_all.add_argument("--narration_max_chars", type=int, default=int(os.getenv("NARRATION_MAX_CHARS", "220")))
    # preset for minimal box-style deck
    p_all.add_argument("--preset", choices=["minimal-box"], default=None, help="Use a preset to build slide prompts")
    p_all.add_argument("--project_name", default=os.getenv("PROJECT_NAME"))
    p_all.add_argument("--tagline", default=os.getenv("TAGLINE"))
    p_all.add_argument("--problem", default=os.getenv("PROBLEM"))
    p_all.add_argument("--architecture", default=os.getenv("ARCHITECTURE"), help="Comma-separated steps/elements")
    p_all.add_argument("--features", default=os.getenv("FEATURES"), help="Comma-separated features")
    p_all.add_argument("--repo", default=os.getenv("REPO"))
    # optional logo overlay during compose
    p_all.add_argument("--logo", default=os.getenv("COMPOSE_LOGO"), help="Path to logo image to overlay bottom-right")
    p_all.add_argument("--logo_scale", type=float, default=float(os.getenv("COMPOSE_LOGO_SCALE", "0.12")), help="Logo width as fraction of video width")
    p_all.add_argument("--logo_margin", type=int, default=int(os.getenv("COMPOSE_LOGO_MARGIN", "20")), help="Margin in pixels from bottom-right")

    args = parser.parse_args()

    if args.cmd == "images":
        # If per-slide prompts provided, use generate_slides_with_tts.generate_images_for_slides
        if args.slide or args.slides_file:
            slide_prompts = args.slide or []
            if args.slides_file:
                with open(args.slides_file, "r", encoding="utf-8") as f:
                    slide_prompts.extend([line.strip() for line in f if line.strip()])
            mod = importlib.import_module("generate_slides_with_tts")
            paths = mod.generate_images_for_slides(args.shared or "", slide_prompts, out_dir=os.getenv("OUT_DIR", "media"), image_model=args.image_model, use_developer=args.use_developer_api)
        else:
            paths = mod.generate_images(args.prompt, args.count, out_dir=os.getenv("OUT_DIR", "media"), image_model=args.image_model, use_developer=args.use_developer_api)
        if paths is not None:
            print("Saved:")
            for p in paths:
                print(p)

    elif args.cmd == "tts":
        mod = importlib.import_module("generate_tts")
        os.makedirs(args.out_dir, exist_ok=True)
        out_path = args.out if os.path.dirname(args.out) else os.path.join(args.out_dir, args.out)
        out = mod.generate_tts(text=args.text, voice_name=args.voice, outfile=out_path, backend=args.tts_backend)
        print(f"Saved TTS to {out}")

    elif args.cmd == "compose":
        mod = importlib.import_module("compose_slides_with_audio")
        search_dir = args.out_dir if os.path.isdir(args.out_dir) else "."
        images = [os.path.join(search_dir, p) for p in sorted(os.listdir(search_dir)) if p.lower().endswith((".png", ".jpg", ".jpeg")) and (p.startswith("slide_") or p.startswith("generated_image_"))]
        os.makedirs(args.out_dir, exist_ok=True)
        out_path = args.out if os.path.dirname(args.out) else os.path.join(args.out_dir, args.out)
        result = mod.compose(images, args.audio, out_path, seconds_per_image=args.seconds)
        print(f"Wrote {result}")
        if args.gcs_uri:
            try:
                uri = _upload_to_gcs(args.gcs_uri, result)
                print(f"Uploaded to {uri}")
            except Exception as e:
                print(f"GCS upload failed: {e}")

    elif args.cmd == "all":
        # 1) images (per-slide prompts from preset/file/flags)
        img_mod = importlib.import_module("generate_slides_with_tts")
        used_slide_prompts = None
        if args.preset == "minimal-box":
            # Deprecated static preset path retained for compatibility; prefer --slides_json
            shared = (args.shared or "") + "\nStyle: elegant, minimal, readable. Neutral or off-white background. Clean boxes with subtle shadows and light borders. Use short bullets (•)."
            slides = []
            used_slide_prompts = None
        elif args.slides_json:
            # Build prompts dynamically from JSON (file path or raw JSON string)
            raw = args.slides_json
            try:
                if os.path.exists(raw):
                    with open(raw, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = json.loads(raw)
            except Exception:
                data = {}

            # Safe getters with variants
            def get_any(dct, keys, default=""):
                for k in keys:
                    if k in dct and isinstance(dct[k], str) and dct[k].strip():
                        return dct[k].strip()
                return default

            title = get_any(data, ["title", "name", "repo", "repository_name"], os.getenv("PROJECT_NAME", "Project"))
            description = get_any(data, ["description", "summary", "readme", "about"], "")
            user_journey = get_any(data, ["user_journey", "usage", "flow", "how_it_works"], "")
            repo = get_any(data, ["repository", "repo_url", "url"], os.getenv("REPO", "https://github.com/..."))
            tech_stack = get_any(data, ["tech_stack", "stack", "technologies", "tech"], "")

            # Fallbacks: also scan all string values for keywords
            def flatten_strings(obj):
                out = []
                if isinstance(obj, dict):
                    for v in obj.values():
                        out.extend(flatten_strings(v))
                elif isinstance(obj, list):
                    for v in obj:
                        out.extend(flatten_strings(v))
                elif isinstance(obj, str):
                    out.append(obj)
                return out

            all_text = "\n".join(flatten_strings(data)).lower()

            def first_sentence(text: str, limit: int = 160) -> str:
                if not text:
                    return ""
                cut = text.strip().replace("\n", " ")
                if len(cut) > limit:
                    cut = cut[:limit]
                for p in [". ", "! ", "? "]:
                    idx = cut.find(p)
                    if idx != -1:
                        return cut[: idx + 1].strip()
                return cut.strip()

            tagline = first_sentence(description) or first_sentence(all_text)

            # Problem statement heuristics
            problem_stmt = first_sentence(user_journey, 220)
            if not problem_stmt:
                # Look for cues
                if "problem" in all_text:
                    problem_stmt = "Users face challenges addressed by this project; this slide summarizes them."
                elif "auth" in all_text or "login" in all_text:
                    problem_stmt = "Users need a secure, simple way to sign in and access the app."
                else:
                    problem_stmt = first_sentence(description, 220) or "Users need a streamlined experience to accomplish their core tasks."

            # Tech bullets (parse markdown-ish lists)
            tech_lines = []
            for ln in tech_stack.splitlines():
                t = ln.strip().lstrip("*- ")
                if t:
                    tech_lines.append(t)
            tech_bullets = [t for t in tech_lines if ":" in t]

            

            # Architecture bullets (generic)
            
            shared = (args.shared or "") + "\nStyle: elegant, minimal, readable. Neutral/off-white background. Subtle borders, clean typography, short bullets (•)."

            # Prepare tech stack items for a dedicated slide (prefer explicit lines)
            tech_stack_items = tech_lines[:4] if tech_lines else [
                "Languages & Frameworks",
                "Libraries & Tooling",
                "Services & APIs",
                "CI/CD & Infrastructure",
            ]

            slides_prompts = [
            # Slide 1 — Title & Hook
            (
                "Minimal intro slide with centered box layout. "
                "• First line: short project title (≤3 words) derived from: "
                f"[{data['title']}]. "
                "• Second line: 1-line short tagline (≤5 words) summarizing: "
                f"[{data['description']}]. "
                "Design: clean background, subtle geometric art, high contrast typography, no logos."
            ),

            # Slide 2 — User Journey / Problem
            (
                "Slide with 3–4 minimal boxed bullets. "
                "• Each bullet: 1–3 words summarizing key steps or problems. "
                "• Condense from: "
                f"[{data['user_journey']}]. "
                "• Keep all bullets evenly spaced in a single column. "
                "• Simple background, no icons or extra decoration."
            ),

            # Slide 3 — Tech Stack
            (
                "Tech Stack grid of pills. "
                "• Each pill: single token or short tech name (e.g., 'Next.js', 'TypeScript'). "
                "• Derive from: "
                f"[{data['tech_stack']}]. "
                "• 2–3 rows, evenly spaced, rounded pills with light borders. "
                "• One simple heading: 'Tech Stack' (2 words max). "
                "• No logos, no captions."
            ),

            # Slide 4 — CTA
            (
                "Closing slide with minimal CTA. "
                "• Top line: 'Open Repo' "
                "• Bottom line: shortened repo link derived from: "
                f"[{data['repository']}]. "
                "• Clean background, subtle divider, generous margins. "
                "• No QR codes or extra elements."
            )
            ]
            slides = img_mod.generate_images_for_slides(shared, slides_prompts, out_dir=args.out_dir, image_model=os.getenv("IMAGE_MODEL"), use_developer=os.getenv("USE_DEVELOPER_API", "").lower() in {"1","true","yes"})
            used_slide_prompts = slides_prompts
        elif args.slide or args.slides_file:
            prompts = args.slide or []
            if args.slides_file and os.path.exists(args.slides_file):
                with open(args.slides_file, "r", encoding="utf-8") as f:
                    prompts.extend([line.strip() for line in f if line.strip()])
            slides = img_mod.generate_images_for_slides(args.shared or "", prompts, out_dir=args.out_dir, image_model=os.getenv("IMAGE_MODEL"), use_developer=os.getenv("USE_DEVELOPER_API", "").lower() in {"1","true","yes"})
            used_slide_prompts = prompts
        else:
            # Fallback to simple prompt+count env vars if nothing provided
            prompt = os.getenv("SLIDES_PROMPT", "Robot holding a red skateboard")
            count = int(os.getenv("SLIDES_COUNT", "4"))
            slides = img_mod.generate_images(prompt, count, out_dir=args.out_dir, image_model=os.getenv("IMAGE_MODEL"), use_developer=os.getenv("USE_DEVELOPER_API", "").lower() in {"1","true","yes"})
        # 2) tts (single or per-slide)
        os.makedirs(args.out_dir, exist_ok=True)
        tts_mod = importlib.import_module("generate_tts")
        per_slide_texts = None
        if args.text_file and os.path.exists(args.text_file):
            with open(args.text_file, "r", encoding="utf-8") as f:
                raw = f.read()
            # Prefer explicit '---' block separators if present
            if '---' in raw:
                blocks = [b.strip() for b in raw.split('---') if b.strip()]
            else:
                # Split on blank lines
                blocks = [b.strip() for b in re.split(r"\n\s*\n", raw) if b.strip()]
            if len(blocks) > 1:
                per_slide_texts = blocks
        # Auto-generate narration if requested or when slides come from JSON, and no explicit per-slide text provided
        if per_slide_texts is None and (args.auto_narration or args.slides_json) and used_slide_prompts:
            try:
                # Reuse Vertex-initialized client
                narr_mod = importlib.import_module("generate_slides_with_tts")
                client = narr_mod.init_client()
                n = len(slides)
                target_sentences = "1-2" if args.slides_json else args.narration_sentences
                prompt_lines = [
                    "You are writing spoken narration for a slide deck.",
                    f"Return exactly {n} blocks, one per slide, in order.",
                    f"Each block should be {target_sentences} full sentences, natural and clear.",
                    f"Aim for <= {args.narration_max_chars} characters per block.",
                    "Write complete explanatory sentences that briefly describe what's on the slide.",
                    "Do not use bullet points, lists, or headings in narration.",
                    "Do not copy the slide prompt verbatim; paraphrase to sound natural.",
                    "Separate blocks with a line containing exactly three dashes: ---",
                    "Do not number or label the blocks. Output only the blocks.",
                    "Slides:",
                ]
                for i, sp in enumerate(used_slide_prompts, start=1):
                    prompt_lines.append(f"Slide {i}: {sp}")
                prompt_text = "\n".join(prompt_lines)
                resp = client.models.generate_content(
                    model=args.narration_model,
                    contents=prompt_text,
                )
                raw_text = getattr(resp, "text", None) or ""
                blocks = [b.strip() for b in raw_text.split('---') if b.strip()]
                if len(blocks) < n:
                    # Fallback: split by blank lines
                    blocks = [b.strip() for b in re.split(r"\n\s*\n", raw_text) if b.strip()]
                if len(blocks) >= n:
                    per_slide_texts = blocks[:n]
                else:
                    while len(blocks) < n:
                        blocks.append(blocks[-1] if blocks else "")
                    per_slide_texts = blocks
            except Exception:
                per_slide_texts = None
        if per_slide_texts and len(per_slide_texts) == len(slides):
            wavs = []
            for i, txt in enumerate(per_slide_texts, start=1):
                wav_basename = f"narration_{i}.wav"
                wav_path = os.path.join(args.out_dir, wav_basename)
                tts_mod.generate_tts(text=txt, voice_name=args.voice, outfile=wav_path, backend=args.tts_backend)
                wavs.append(wav_path)
            # 3) compose per slide
            comp_mod = importlib.import_module("compose_slides_with_audio")
            video_out_path = args.video_out if os.path.dirname(args.video_out) else os.path.join(args.out_dir, args.video_out)
            video = comp_mod.compose_per_slide(slides, wavs, video_out_path, logo_path=args.logo, logo_scale=args.logo_scale, logo_margin=args.logo_margin)
        else:
            narration_text = args.text
            if args.text_file and os.path.exists(args.text_file):
                with open(args.text_file, "r", encoding="utf-8") as f:
                    narration_text = f.read().strip()
            wav_out_path = args.tts_out if os.path.dirname(args.tts_out) else os.path.join(args.out_dir, args.tts_out)
            wav = tts_mod.generate_tts(text=narration_text, voice_name=args.voice, outfile=wav_out_path, backend=args.tts_backend)
            # 3) compose single track
            comp_mod = importlib.import_module("compose_slides_with_audio")
            video_out_path = args.video_out if os.path.dirname(args.video_out) else os.path.join(args.out_dir, args.video_out)
            video = comp_mod.compose(slides, wav, video_out_path, seconds_per_image=args.seconds, logo_path=args.logo, logo_scale=args.logo_scale, logo_margin=args.logo_margin)
        print(f"Wrote {video}")
        if args.gcs_uri:
            try:
                uri = _upload_to_gcs(args.gcs_uri, video)
                print(f"Uploaded to {uri}")
            except Exception as e:
                print(f"GCS upload failed: {e}")


if __name__ == "__main__":
    main()


