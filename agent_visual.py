import argparse
import os
from typing import List

from generate_slides_with_tts import generate_images, generate_images_for_slides
from compose_slides_with_audio import compose, compose_per_slide


def find_slides(out_dir: str) -> List[str]:
    if not os.path.isdir(out_dir):
        return []
    return [os.path.join(out_dir, p) for p in sorted(os.listdir(out_dir)) if p.lower().endswith((".png", ".jpg", ".jpeg")) and p.startswith("slide_")]


def maybe_collect_audio(out_dir: str) -> List[str]:
    if not os.path.isdir(out_dir):
        return []
    wavs = [os.path.join(out_dir, p) for p in sorted(os.listdir(out_dir)) if p.lower().endswith(".wav") and p.startswith("narration_")]
    return wavs


def main() -> None:
    parser = argparse.ArgumentParser(description="Visual agent: generate slides and assemble video")
    parser.add_argument("--out_dir", default=os.getenv("OUT_DIR", "media"))
    parser.add_argument("--shared", default=os.getenv("SLIDES_SHARED", ""))
    parser.add_argument("--slide", action="append", default=None)
    parser.add_argument("--slides_file", default=os.getenv("SLIDES_FILE"))
    parser.add_argument("--preset", choices=["minimal-box"], default=None)
    parser.add_argument("--project_name", default=os.getenv("PROJECT_NAME"))
    parser.add_argument("--tagline", default=os.getenv("TAGLINE"))
    parser.add_argument("--problem", default=os.getenv("PROBLEM"))
    parser.add_argument("--architecture", default=os.getenv("ARCHITECTURE"))
    parser.add_argument("--features", default=os.getenv("FEATURES"))
    parser.add_argument("--repo", default=os.getenv("REPO"))
    parser.add_argument("--seconds", type=float, default=float(os.getenv("SECONDS_PER_IMAGE", "2.0")))
    parser.add_argument("--video_out", default=os.getenv("COMPOSE_OUT", "slides_with_audio.mp4"))
    parser.add_argument("--logo", default=os.getenv("COMPOSE_LOGO"))
    parser.add_argument("--logo_scale", type=float, default=float(os.getenv("COMPOSE_LOGO_SCALE", "0.12")))
    parser.add_argument("--logo_margin", type=int, default=int(os.getenv("COMPOSE_LOGO_MARGIN", "20")))
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # Build slide prompts
    used_prompts: List[str] | None = None
    if args.preset == "minimal-box":
        arch_list = [s.strip() for s in (args.architecture or "").split(",") if s.strip()]
        feat_list = [s.strip() for s in (args.features or "").split(",") if s.strip()]
        used_prompts = [
            f"Minimal intro slide with centered title and subtitle boxes.\n• Title (bold): [{args.project_name or 'Project'}]\n• Subtitle (regular): [{args.tagline or ''}]\n• Lots of whitespace, balanced alignment, subtle divider.\nFlat, elegant UI.",
            f"Problem slide with a header and one content box.\n• Header (bold): Problem\n• Body: [{args.problem or 'Problem Statement'}]\n• Use light borders and gentle spacing.\nNeutral background.",
            ("Solution slide with stacked boxes.\n• Header (bold): Solution\n• Steps: evenly stacked boxes for architecture elements.\n• Use minimal dividers.\n" + ("Architecture elements: " + "; ".join(arch_list) if arch_list else "")).strip(),
            ("Key Features slide with small equal boxes.\n• Header: Key Features\n• 3–4 boxes each with a short bullet.\n• Clean text, light borders, no icons.\n" + ("Features: " + "; ".join(feat_list) if feat_list else "")).strip(),
            f"CTA slide with two centered boxes.\n• Top: Check it out on GitHub\n• Bottom (monospace or underlined): [{args.repo or 'https://github.com/...'}]\n• Simple divider and ample whitespace.",
        ]
        slides = generate_images_for_slides((args.shared or "") + "\nStyle: elegant, minimal, readable.", used_prompts, out_dir=args.out_dir)
    elif args.slide or args.slides_file:
        slide_prompts = args.slide or []
        if args.slides_file and os.path.exists(args.slides_file):
            with open(args.slides_file, "r", encoding="utf-8") as f:
                slide_prompts.extend([line.strip() for line in f if line.strip()])
        used_prompts = slide_prompts
        slides = generate_images_for_slides(args.shared or "", slide_prompts, out_dir=args.out_dir)
    else:
        # If no prompts provided, just ensure any existing slides are picked up
        slides = find_slides(args.out_dir)
        if not slides:
            # Create a single placeholder
            slides = generate_images("Minimal placeholder slide", 1, out_dir=args.out_dir)

    # Compose
    wavs = maybe_collect_audio(args.out_dir)
    video_out_path = args.video_out if os.path.dirname(args.video_out) else os.path.join(args.out_dir, args.video_out)
    if len(wavs) == len(slides) and len(wavs) > 0:
        result = compose_per_slide(slides, wavs, video_out_path, logo_path=args.logo, logo_scale=args.logo_scale, logo_margin=args.logo_margin)
    elif os.path.exists(os.path.join(args.out_dir, "narration.wav")):
        result = compose(slides, os.path.join(args.out_dir, "narration.wav"), video_out_path, seconds_per_image=args.seconds, logo_path=args.logo, logo_scale=args.logo_scale, logo_margin=args.logo_margin)
    else:
        # No audio: compose silent video with fixed seconds per image using a blank audio workaround
        result = compose(slides, os.path.join(args.out_dir, "narration.wav"), video_out_path, seconds_per_image=args.seconds, logo_path=args.logo, logo_scale=args.logo_scale, logo_margin=args.logo_margin)
    print(f"Wrote {result}")


if __name__ == "__main__":
    main()


