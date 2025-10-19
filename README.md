# BlindVerse Slides + TTS Pipeline

Generate elegant, minimal slides with Imagen 4.0, synthesize narration (Cloud TTS fallback if Gemini TTS not allowlisted), and stitch into an MP4 with an optional Gemini logo overlay.

## Prerequisites
- Python 3.10+
- Google GenAI SDK and optional Google Cloud clients
- Vertex AI credentials via service account

## Setup
1) Create `.env` in project root:
```
VERTEX_AI_PROJECT_ID=your-project-id
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_CREDENTIALS_PATH=gemini_key.json
```
2) Install dependencies:
```
pip install google-genai python-dotenv pillow moviepy google-cloud-texttospeech
```
(If you see messages about storage or requests during downloads, also: `pip install google-cloud-storage requests`.)

3) Ensure `gemini_key.json` exists and has access to the project and Vertex APIs.

## One-shot Run (auto narration, minimal-box preset)
```
python run.py all \
  --preset minimal-box \
  --project_name "AI Safety Protocol" \
  --tagline "Multi-layer defense for safer AI" \
  --problem "Prompt injection, jailbreaks, and backdoors" \
  --architecture "Prompt filtering,Jailbreak defense,Guardrail policies,Audit logging" \
  --features "LLM-agnostic,Real-time filtering,Policy templates,Audit trail" \
  --repo "https://github.com/your/repo" \
  --auto_narration \
  --narration_model gemini-2.0-flash-001 \
  --narration_tone "clear, instructional" \
  --narration_sentences "2-3" \
  --narration_max_chars 220 \
  --tts_backend cloud \
  --logo media/gemini_logo.png \
  --logo_scale 0.12 \
  --logo_margin 20 \
  --out_dir media
```
- Slides are saved to `media/slide_1.png` …
- Per-slide WAVs to `media/narration_*.wav` (when using per-slide narration)
- Final MP4 to `media/slides_with_audio.mp4`

## Per-slide Narration (manual)
Create `narration_lines.txt` with one block per slide (separate blocks with a blank line or a line `---`). Example:
```
Intro line 1. Intro line 2.
---
Problem line 1. Problem line 2.
---
Solution blocks, 2-3 sentences.
---
Features overview.
---
Call to Action.
```
Then run:
```
python run.py all ... --text_file narration_lines.txt --tts_backend cloud --out_dir media
```

## Custom Slides
- Provide per-slide prompts directly:
```
python run.py all \
  --shared "Elegant minimal styling" \
  --slide "Title: ..." --slide "Problem: ..." --slide "Solution: ..." \
  --slide "Features: ..." --slide "CTA: ..." \
  --text_file narration_lines.txt \
  --tts_backend cloud \
  --out_dir media
```
- Or from file (one line per slide): `--slides_file slides.txt`

## Commands
- Generate only images:
```
python run.py images --shared "..." --slide "..." --out_dir media
```
- Generate only TTS:
```
python run.py tts --text "Hello" --voice Kore --out narration.wav --out_dir media
```
- Compose existing slides + audio:
```
python run.py compose --audio media/narration.wav --out media/slides_with_audio.mp4 --seconds 2.5
```

## Notes
- If Gemini TTS returns allowlist errors, the pipeline falls back to Google Cloud Text-to-Speech. Install `google-cloud-texttospeech` and ensure your service account has permission.
- Slides remain on screen until their own TTS finishes when per-slide narration is used.
- Use `--logo`, `--logo_scale`, `--logo_margin` to overlay a logo on the final video.
