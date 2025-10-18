import argparse
import os
import sys
import importlib
import re


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

    # all
    p_all = sub.add_parser("all", help="Run full pipeline: images -> TTS -> compose")
    p_all.add_argument("--shared", default=os.getenv("SLIDES_SHARED", ""), help="Shared material included in every slide prompt")
    p_all.add_argument("--slide", action="append", default=None, help="Per-slide prompt; repeat flag for multiple slides")
    p_all.add_argument("--slides_file", default=os.getenv("SLIDES_FILE"), help="Path to a text file with one slide prompt per line")
    p_all.add_argument("--text", default=os.getenv("TTS_TEXT", "Say cheerfully: Have a wonderful day!"))
    p_all.add_argument("--text_file", default=os.getenv("TTS_TEXT_FILE"), help="Path to a text file for narration")
    p_all.add_argument("--voice", default=os.getenv("TTS_VOICE", "Kore"))
    p_all.add_argument("--tts_out", default=os.getenv("TTS_OUT", "narration.wav"))
    p_all.add_argument("--tts_backend", default=os.getenv("TTS_BACKEND", "auto"), choices=["auto", "gemini", "cloud"], help="Choose TTS backend")
    p_all.add_argument("--video_out", default=os.getenv("COMPOSE_OUT", "slides_with_audio.mp4"))
    p_all.add_argument("--seconds", type=float, default=float(os.getenv("SECONDS_PER_IMAGE", "2.0")))
    p_all.add_argument("--out_dir", default=os.getenv("OUT_DIR", "media"), help="Directory to write narration and video outputs")
    # auto narration generation via Gemini text model
    p_all.add_argument("--auto_narration", action="store_true", help="Generate narration per slide via Gemini text model")
    p_all.add_argument("--narration_model", default=os.getenv("NARRATION_MODEL", "gemini-2.0-flash-001"))
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
            paths = mod.generate_images_for_slides(args.shared or "", slide_prompts)
        else:
            mod = importlib.import_module("generate_robot_images")
            paths = mod.main() if hasattr(mod, "main") else None
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
        images = [p for p in sorted(os.listdir(".")) if p.lower().endswith((".png", ".jpg", ".jpeg")) and (p.startswith("slide_") or p.startswith("generated_image_"))]
        os.makedirs(args.out_dir, exist_ok=True)
        out_path = args.out if os.path.dirname(args.out) else os.path.join(args.out_dir, args.out)
        result = mod.compose(images, args.audio, out_path, seconds_per_image=args.seconds)
        print(f"Wrote {result}")

    elif args.cmd == "all":
        # 1) images (per-slide prompts from preset/file/flags)
        img_mod = importlib.import_module("generate_slides_with_tts")
        used_slide_prompts = None
        if args.preset == "minimal-box":
            shared = (args.shared or "") + "\nStyle: elegant, minimal, readable. Neutral or off-white background. Clean boxes with subtle shadows and light borders. Use short bullet lines (•) with plenty of spacing."
            arch_list = [s.strip() for s in (args.architecture or "").split(",") if s.strip()]
            feat_list = [s.strip() for s in (args.features or "").split(",") if s.strip()]
            slides_prompts = [
                f"Minimal intro slide with centered title and subtitle boxes.\n• Title (bold): [{args.project_name or 'Project'}]\n• Subtitle (regular): [{args.tagline or ''}]\n• Lots of whitespace, balanced alignment, subtle divider.\nFlat, elegant UI.",
                f"Problem slide with a header and one content box.\n• Header (bold): Problem\n• Body: [{args.problem or 'Problem Statement'}]\n• Use light borders and gentle spacing.\nNeutral background.",
                ("Solution slide with stacked boxes.\n• Header (bold): Solution\n• Steps: evenly stacked boxes for architecture elements.\n• Use minimal dividers.\n" + ("Architecture elements: " + "; ".join(arch_list) if arch_list else "")).strip(),
                ("Key Features slide with small equal boxes.\n• Header: Key Features\n• 3–4 boxes each with a short bullet.\n• Clean text, light borders, no icons.\n" + ("Features: " + "; ".join(feat_list) if feat_list else "")).strip(),
                f"CTA slide with two centered boxes.\n• Top: Check it out on GitHub\n• Bottom (monospace or underlined): [{args.repo or 'https://github.com/...'}]\n• Simple divider and ample whitespace.",
            ]
            slides = img_mod.generate_images_for_slides(shared, slides_prompts)
            used_slide_prompts = slides_prompts
        elif args.slide or args.slides_file:
            prompts = args.slide or []
            if args.slides_file and os.path.exists(args.slides_file):
                with open(args.slides_file, "r", encoding="utf-8") as f:
                    prompts.extend([line.strip() for line in f if line.strip()])
            slides = img_mod.generate_images_for_slides(args.shared or "", prompts)
            used_slide_prompts = prompts
        else:
            # Fallback to simple prompt+count env vars if nothing provided
            prompt = os.getenv("SLIDES_PROMPT", "Robot holding a red skateboard")
            count = int(os.getenv("SLIDES_COUNT", "4"))
            slides = img_mod.generate_images(prompt, count)
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
        # Auto-generate narration if requested and no explicit per-slide text provided
        if per_slide_texts is None and args.auto_narration and used_slide_prompts:
            try:
                # Reuse Vertex-initialized client
                narr_mod = importlib.import_module("generate_slides_with_tts")
                client = narr_mod.init_client()
                n = len(slides)
                prompt_lines = [
                    "You are writing spoken narration for a slide deck.",
                    f"Return exactly {n} blocks, one per slide, in order.",
                    f"Each block should be {args.narration_sentences} sentences, natural and clear.",
                    f"Aim for <= {args.narration_max_chars} characters per block.",
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


if __name__ == "__main__":
    main()


