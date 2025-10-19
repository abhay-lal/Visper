import os
import json
import asyncio
from uagents import Agent, Context, Model
import subprocess
import re
from datetime import datetime


class GenericMessage(Model):
    content: str


AGENT_HANDLE = os.getenv(
    "AGENT_HANDLE",
    "agent1qdwu9wmhzc4vywetrvkwuda5jvecx3rr2789eullwv8hpy8d9w80x4cw3sg"
)
REPO_URL = os.getenv(
    "GITHUB_URL",
    "https://github.com/KshitijD21/job-portal-ui"
)

# ✅ Add mailbox so remote agent can reply
controller = Agent(
    name="RouterAgent",
    seed="router-seed",
    mailbox=True,
    endpoint=None,              # ✅ remove endpoint so it uses mailbox
    publish_agent_details=True,
)


@controller.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"Sending repository analysis request to: {AGENT_HANDLE}")
    message = json.dumps({
        "action": "analyze_repository",
        "repository_url": REPO_URL
    })
    await ctx.send(AGENT_HANDLE, GenericMessage(content=message))
    ctx.logger.info("Request sent. Waiting for response...")


@controller.on_message(model=GenericMessage)
async def handle_response(ctx: Context, sender: str, msg: GenericMessage):
    """Handle JSON response from RepositoryAnalyzer."""
    try:
        result = json.loads(msg.content)
        print("\n🎉 Repository Analysis JSON:\n")
        print(json.dumps(result, indent=2))

        # Save JSON to disk
        with open("analysis.json", "w") as f:
            json.dump(result, f, indent=2)
        print("\n💾 Saved to analysis.json")

        # Optionally invoke run.py with the generated JSON
        if os.getenv("AUTO_RUN_PIPELINE", "").lower() in {"1", "true", "yes"}:
            out_dir = os.getenv("OUT_DIR", "media")
            tts_backend = os.getenv("TTS_BACKEND", "cloud")
            narration_model = os.getenv("NARRATION_MODEL", "gemini-2.5-flash-tts")
            gcs_uri = os.getenv("GCS_URI", "")
            status_file = os.getenv("VIDEO_STATUS_FILE", os.path.join(out_dir, "video_status.json"))
            cmd = [
                "python", "run.py", "all",
                "--slides_json", "analysis.json",
                "--out_dir", out_dir,
                "--tts_backend", tts_backend,
                "--auto_narration",
                "--narration_model", narration_model
            ]
            if gcs_uri:
                cmd.extend(["--gcs_uri", gcs_uri])

            print("\n▶️ Running pipeline:", " ".join(cmd))
            try:
                # Capture output to extract GCS URL after upload
                proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
                stdout = proc.stdout or ""
                stderr = proc.stderr or ""
                if stdout:
                    print(stdout)
                if stderr:
                    print(stderr)

                # Parse a line like: "Uploaded to gs://bucket/path.mp4"
                m = re.search(r"Uploaded to\s+(gs://[^\s]+)", stdout)
                if m:
                    uploaded_uri = m.group(1)
                    # Best-effort public URL (if the object is public)
                    public_url = None
                    try:
                        # Convert gs://bucket/path.mp4 -> https://storage.googleapis.com/bucket/path.mp4
                        without_scheme = uploaded_uri[len("gs://"):]
                        bucket, obj = without_scheme.split("/", 1)
                        public_url = f"https://storage.googleapis.com/{bucket}/{obj}"
                    except Exception:
                        public_url = None

                    payload = {
                        "status": "completed",
                        "gcs_uri": uploaded_uri,
                        "public_url": public_url,
                        "updated_at": datetime.utcnow().isoformat() + "Z"
                    }
                    try:
                        os.makedirs(os.path.dirname(status_file), exist_ok=True)
                        with open(status_file, "w", encoding="utf-8") as f:
                            json.dump(payload, f, indent=2)
                        print(f"💾 Wrote video status to {status_file}")
                    except Exception as write_err:
                        ctx.logger.warning(f"Failed to write video status file: {write_err}")
            except subprocess.CalledProcessError as e:
                ctx.logger.error(f"Pipeline failed: {e}")
                # Write error status
                try:
                    error_payload = {
                        "status": "error",
                        "error": str(e),
                        "updated_at": datetime.utcnow().isoformat() + "Z"
                    }
                    os.makedirs(os.path.dirname(status_file), exist_ok=True)
                    with open(status_file, "w", encoding="utf-8") as f:
                        json.dump(error_payload, f, indent=2)
                except Exception:
                    pass

        # Graceful exit
        asyncio.get_event_loop().call_later(1, os._exit, 0)

    except Exception as e:
        ctx.logger.error(f"Error handling response: {e}")


if __name__ == "__main__":
    print(f"🚀 Starting local router agent...")
    print(f"   Target agent: {AGENT_HANDLE}")
    print(f"   Repo:         {REPO_URL}\n")
    asyncio.run(controller.run())