import os
import json
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from google import genai
from uagents import Agent, Context, Model, Protocol

# --- Load environment variables ---
load_dotenv()


# --- Shared message model (used by router or other agents) ---
class GenericMessage(Model):
    content: str


# ================================================================
#   🧠 VECTARA QnA CLASS (Direct API Integration)
# ================================================================
class VectaraQnA:
    def __init__(self):
        self.customer_id = os.getenv("VECTARA_CUSTOMER_ID")
        self.corpus_id = os.getenv("VECTARA_CORPUS_ID")
        self.api_key = os.getenv("VECTARA_API_KEY")
        self.base_url = "https://api.vectara.io/v1"

        # Validation for debugging
        if not all([self.customer_id, self.corpus_id, self.api_key]):
            print("⚠️ Missing one or more Vectara credentials in environment variables!")

    def query(self, question, num_results=5):
        """Query Vectara for answers"""
        url = f"{self.base_url}/query"

        headers = {
            "Content-Type": "application/json",
            "customer-id": self.customer_id,
            "x-api-key": self.api_key
        }

        payload = {
            "query": [
                {
                    "query": question,
                    "num_results": num_results,
                    "corpus_key": [
                        {
                            "customer_id": self.customer_id,
                            "corpus_id": self.corpus_id
                        }
                    ],
                    "summary": [
                        {
                            "summarizerPromptName": "vectara-summary-ext-v1.2.0",
                            "responseLang": "eng",
                            "maxSummarizedResults": num_results
                        }
                    ]
                }
            ]
        }

        try:
            print(f"[Vectara] 🔍 Querying: {question}")
            response = requests.post(url, json=payload, headers=headers, timeout=25)
            print(f"[Vectara] Status: {response.status_code}")
            response.raise_for_status()
            result = response.json()

            # Extract summary and sources
            if result.get("responseSet") and len(result["responseSet"]) > 0:
                response_set = result["responseSet"][0]
                summary = response_set.get("summary", [{}])[0].get("text", "No summary available")

                # Extract document snippets
                documents = []
                for doc in response_set.get("response", []):
                    documents.append({
                        "text": doc.get("text", ""),
                        "score": doc.get("score", 0)
                    })

                return {
                    "answer": summary,
                    "sources": documents
                }
            else:
                print("[Vectara] No results found.")
                return {"answer": "No results found", "sources": []}

        except requests.exceptions.RequestException as e:
            print(f"[Vectara] ❌ API error: {e}")
            return {"error": f"API request failed: {str(e)}"}

    def ask(self, question):
        """Simple Q&A interface"""
        result = self.query(question)
        if "error" in result:
            return None
        return result


# ================================================================
#   🤖 GEMINI CLIENT SETUP
# ================================================================
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# ================================================================
#   🔍 REPOSITORY ANALYZER CORE LOGIC
# ================================================================
def extract_repo_title(git_url: str):
    """Extract repository name from GitHub URL."""
    parsed = urlparse(git_url)
    path = parsed.path.strip("/")
    return path if path else "Unknown Repository"


def analyze_repository(git_url: str):
    """Run analysis combining Vectara for repo insight + Gemini for summarization."""
    qna = VectaraQnA()
    info = {
        "title": extract_repo_title(git_url),
        "description": "",
        "user_journey": "",
        "repository": git_url,
    }

    # 1️⃣ Repository description
    q1 = "What does this repository do? What is its main purpose?"
    r1 = qna.ask(q1)
    if r1:
        try:
            g1 = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Summarize this repository info: {r1['answer']} {r1['sources']} "
                         f"into 2 concise sentences describing what the repository does."
            )
            info["description"] = g1.text.strip()
        except Exception as e:
            info["description"] = f"Gemini summarization failed: {e}"

    # 2️⃣ User journey
    q2 = "Explain the user flow or user journey in this repository."
    r2 = qna.ask(q2)
    if r2:
        try:
            g2 = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Summarize this repository info: {r2['answer']} {r2['sources']} "
                         f"into 2 concise sentences describing the user journey or flow."
            )
            info["user_journey"] = g2.text.strip()
        except Exception as e:
            info["user_journey"] = f"Gemini summarization failed: {e}"

    return info


# ================================================================
#   📨 PROTOCOL (chat-compatible + router-friendly)
# ================================================================
chat_protocol = Protocol("chat")


@chat_protocol.on_message(model=GenericMessage)
async def handle_message(ctx: Context, sender: str, msg: GenericMessage):
    """Handle incoming analysis requests."""
    try:
        payload = json.loads(msg.content)
        git_url = payload.get("repository_url", "").strip()

        if not git_url:
            ctx.logger.error("No repository URL provided in message.")
            await ctx.send(sender, GenericMessage(content=json.dumps({"error": "Missing repository_url"})))
            return

        ctx.logger.info(f"🔍 Analyzing repository: {git_url}")
        result = analyze_repository(git_url)

        ctx.logger.info("✅ Analysis complete. Sending response...")
        await ctx.send(sender, GenericMessage(content=json.dumps(result)))

    except Exception as e:
        ctx.logger.error(f"Error in handler: {e}")
        await ctx.send(sender, GenericMessage(content=json.dumps({"error": str(e)})))


# ================================================================
#   🧩 AGENT SETUP
# ================================================================
agent = Agent(
    name="RepositoryAnalyzer-Agent",
    seed=os.getenv("AGENT_SEED", "repository-analyzer-seed"),
    mailbox=True,
    publish_agent_details=True,
    default_protocol="chat",
)

agent.include(chat_protocol)


# ================================================================
#   🚀 ENTRY POINT
# ================================================================
if __name__ == "__main__":
    print("🚀 Starting RepositoryAnalyzer-Agent...")
    print(f"Agent address: {agent.address}")
    print("Inspect at: https://agentverse.ai/inspect/?address=" + agent.address)
    agent.run()
