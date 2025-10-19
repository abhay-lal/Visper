# Multimodal Live API with Gemini + RAG

This repository provides quickstart examples for using the Gemini Multimodal Live API enhanced with Retrieval-Augmented Generation (RAG) capabilities using Vectara. It showcases how to interact with Gemini using various input and output modalities while leveraging your custom knowledge base.

> **Note:** This is an experimental API that may change in the future. The implementation uses API version 'v1beta1' for VertexAI and 'v1alpha' for Gemini Developer API (Google AI Studio). Documentation from Google is still evolving.

## Examples

### 1. Text-to-Audio Chat with RAG (text-to-audio-liveapi.py)
- Type messages in your terminal
- System searches your Vectara knowledge base for relevant context
- Listen to Gemini's responses enhanced with your custom knowledge
- Simple command-line interface
- Type `quit` to exit

### 2. Voice-to-Voice Chat with RAG (audio-to-audio-liveapi.py)
- Speak directly to Gemini using your microphone
- System transcribes your speech and searches Vectara for context
- Receive audio responses enhanced with your knowledge base
- Real-time voice conversation with RAG
- Press `ctrl+c` to quit

### 3. RAG Service (rag_service.py)
- Standalone service for Vectara integration
- Handles document search and context building
- Can be used independently or integrated with other applications

## Requirements

```
google-genai
pyaudio
requests
speechrecognition
```

Python 3.11+ is required for the voice-to-voice example, as it uses `asyncio.TaskGroup` for concurrent task management.

## Setup

1. Clone the repository:
```bash
git clone https://github.com/ontaptom/multimodal-live-api.git
cd multimodal-live-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Choose your authentication method:

### Option A: Google AI Studio API Key
- Visit [aistudio.google.com](https://aistudio.google.com) to get your API key
- Set the environment variable: `export GOOGLE_API_KEY=your_api_key`
- In both scripts, set `use_vertexai = False`

### Option B: Vertex AI
- Ensure you have a Google Cloud Project set up
- Set `use_vertexai = True` in both scripts
- Update the `PROJECT_ID` variable with your project ID
- Ensure you have the necessary permissions and have enabled the Vertex AI API

4. Configure Vectara for RAG capabilities:

### Vectara Setup
- Sign up for a Vectara account at [vectara.com](https://vectara.com)
- Create a corpus and upload your documents
- Get your Customer ID, Corpus ID, and API Key from the Vectara console
- Set environment variables:
  ```bash
  export VECTARA_CUSTOMER_ID=your_customer_id
  export VECTARA_CORPUS_ID=your_corpus_id
  export VECTARA_API_KEY=your_api_key
  ```
- Or copy `config_example.py` to `config.py` and fill in your credentials

## Usage

### Text-to-Audio Chat with RAG:
```bash
python text-to-audio-liveapi.py
```
- Type your message at the "You: " prompt
- System searches your Vectara knowledge base for relevant context
- Listen to Gemini's response enhanced with your custom knowledge
- Type "quit" to exit

### Voice-to-Voice Chat with RAG:
```bash
python audio-to-audio-liveapi.py
```
- Start speaking into your microphone
- System transcribes your speech and searches Vectara for context
- Listen to Gemini's responses enhanced with your knowledge base
- Press Ctrl+C to exit

> 💡 Headphones are recommended when using the voice-to-voice chat to prevent audio feedback loops.

### RAG Service Usage:
```python
from rag_service import VectaraRAGService

# Initialize the service
rag = VectaraRAGService(
    customer_id="your_customer_id",
    corpus_id="your_corpus_id", 
    api_key="your_api_key"
)

# Search for relevant documents
results = rag.search("your query here")

# Build enhanced prompt
enhanced_prompt = rag.build_context_prompt("your query", results)
```

## Implementation Details

The API is still not perfectly documented by Google, and there are important differences in how you must configure the client depending on which authentication method you use:

### API Version Differences
- VertexAI uses `v1beta1` 
- Google AI Studio uses `v1alpha`

### Model Name Format
- VertexAI: `"gemini-2.0-flash-exp"` (just the model name) - at least in `v1beta1` API version
- Google AI Studio: `"models/gemini-2.0-flash-exp"` (requires the "models/" prefix) - at least in `v1alpha` API version

### Configuration Format
- VertexAI: Uses `LiveConnectConfig` object with `Modality` enum - at least in `v1beta1` API version
- Google AI Studio: Uses dictionary format with nested "generation_config" object - at least in `v1alpha` API version

Here's how this looks in code:

```python
# For VertexAI:
client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location='us-central1',
    http_options=HttpOptions(api_version="v1beta1")
)
MODEL = "gemini-2.0-flash-exp"  # Just the model name
CONFIG = LiveConnectConfig(response_modalities=[Modality.AUDIO])

# For Google AI Studio:
client = genai.Client(
    http_options={"api_version": "v1alpha"}
)
MODEL = "models/gemini-2.0-flash-exp"  # Note the "models/" prefix
CONFIG = {"generation_config": {"response_modalities": ["AUDIO"]}}
```

These differences are critical for successful operation with either authentication method.

## RAG Implementation Details

The RAG integration follows **Approach A (Pre-retrieval)**:

1. **User Input**: Text or voice input is captured
2. **Vectara Search**: Query is sent to Vectara to retrieve relevant documents
3. **Context Building**: Retrieved documents are formatted into an enhanced prompt
4. **Gemini Processing**: Enhanced prompt (with context) is sent to Gemini
5. **Response**: Gemini generates a response informed by your knowledge base

### Key Features:
- **Fallback Mode**: If Vectara credentials are not configured, the system works without RAG
- **Context Display**: Shows retrieved documents and their relevance scores
- **Conversation History**: Maintains context across multiple turns
- **Error Handling**: Gracefully handles Vectara API failures

### Configuration Options:
- `num_results`: Number of documents to retrieve (default: 3)
- `silence_threshold`: Voice detection sensitivity (default: 1.0 seconds)
- Custom prompt formatting in `build_context_prompt()`

## Troubleshooting

### Common Issues:
1. **"RAG disabled" message**: Check your Vectara credentials
2. **Transcription errors**: Ensure microphone permissions are granted
3. **No audio output**: Check speaker/headphone connections
4. **Import errors**: Run `pip install -r requirements.txt`

### Vectara Setup:
1. Create a corpus in your Vectara account
2. Upload your documents (PDF, TXT, DOCX, etc.)
3. Wait for indexing to complete
4. Test with simple queries first

## License

```
Copyright 2025

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## **Google Cloud credits are provided for this project.** #VertexAISprint
