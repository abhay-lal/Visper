import os
import sys
from typing import List

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip  # type: ignore


def compose(images: List[str], audio_path: str, out_path: str = "slides_with_audio.mp4", seconds_per_image: float = 2.0, logo_path: str | None = None, logo_scale: float = 0.12, logo_margin: int = 20) -> str:
    if not images:
        raise ValueError("No images provided")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    clips = [ImageClip(img).set_duration(seconds_per_image) for img in images]
    video = concatenate_videoclips(clips, method="compose")
    if logo_path and os.path.exists(logo_path):
        logo = ImageClip(logo_path)
        # scale logo relative to video width
        w = video.w
        logo = logo.resize(width=int(max(1, logo_scale * w)))
        # position bottom-right with margin
        logo = logo.set_position((video.w - logo.w - logo_margin, video.h - logo.h - logo_margin)).set_duration(video.duration)
        video = CompositeVideoClip([video, logo])
    audio = AudioFileClip(audio_path)
    video = video.set_audio(audio)
    # Ensure fps to avoid codec issues
    video.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
    return out_path


def compose_per_slide(images: List[str], audio_files: List[str], out_path: str = "slides_with_audio.mp4", logo_path: str | None = None, logo_scale: float = 0.12, logo_margin: int = 20) -> str:
    if not images:
        raise ValueError("No images provided")
    if not audio_files:
        raise ValueError("No audio files provided")
    if len(images) != len(audio_files):
        raise ValueError("images and audio_files must have same length")

    clips = []
    for img, aud in zip(images, audio_files):
        if not os.path.exists(aud):
            raise FileNotFoundError(f"Audio file not found: {aud}")
        audio = AudioFileClip(aud)
        clip = ImageClip(img).set_duration(audio.duration).set_audio(audio)
        clips.append(clip)
    video = concatenate_videoclips(clips, method="compose")
    if logo_path and os.path.exists(logo_path):
        logo = ImageClip(logo_path)
        w = video.w
        logo = logo.resize(width=int(max(1, logo_scale * w)))
        logo = logo.set_position((video.w - logo.w - logo_margin, video.h - logo.h - logo_margin)).set_duration(video.duration)
        video = CompositeVideoClip([video, logo])
    video.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
    return out_path


if __name__ == "__main__":
    # Example usage: read slides_* or generated_image_* files and narration.wav
    images = [p for p in sorted(os.listdir(".")) if p.lower().endswith((".png", ".jpg", ".jpeg")) and (p.startswith("slide_") or p.startswith("generated_image_"))]
    audio = os.getenv("COMPOSE_AUDIO", "narration.wav")
    out = os.getenv("COMPOSE_OUT", "slides_with_audio.mp4")
    try:
        result = compose(images, audio, out)
        print(f"Wrote {result}")
    except Exception as e:
        print(f"Failed to compose video: {e}")
        sys.exit(1)


