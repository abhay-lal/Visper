import os
import requests
from dotenv import load_dotenv

load_dotenv()

class VectaraQnA:
    def __init__(self):
        self.customer_id = os.getenv("VECTARA_CUSTOMER_ID")
        self.corpus_id = os.getenv("VECTARA_CORPUS_ID")
        self.api_key = os.getenv("VECTARA_API_KEY")
        self.base_url = "https://api.vectara.io/v1"
        
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
            response = requests.post(url, json=payload, headers=headers)
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
                return {"answer": "No results found", "sources": []}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
    
    def ask(self, question):
        """Simple Q&A interface"""
        result = self.query(question)
        
        if "error" in result:
            return None
        
        return result

def main():
    qna = VectaraQnA()
    
    question = input("\nAsk a question: ").strip()
    result = qna.ask(question)
    
    if result is None:
        print("Error occurred while processing the question")
        return
    
    print(f"\nQuestion: {question}")
    print(f"\nAnswer: {result['answer']}")
    
    if result['sources']:
        print(f"\n--- Source Snippets ---")
        for i, source in enumerate(result['sources'][:3], 1):
            print(f"\n{i}. (Score: {source['score']:.3f})")
            print(f"   {source['text'][:200]}...")
if __name__ == "__main__":
    main()

