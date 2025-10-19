"""
Command Line Chat with Gemini 2.0 Flash exp Audio Response + RAG

This script creates a simple command-line chat application that sends text to the
Gemini API enhanced with RAG capabilities and plays back the audio responses through your speakers.

Requirements:
- google-genai
- pyaudio
- requests

Setup:
1. Install dependencies: `pip install google-genai pyaudio requests`
2. For Google AI Studio; Set GOOGLE_API_KEY environment variable with your API key and set use_vertexai to False in line 37.
   If you are using VertexAI check provide PROJECT_ID in line 38 and set use_vertexai to True in line 37.
3. Set Vectara credentials: VECTARA_CUSTOMER_ID, VECTARA_CORPUS_ID, VECTARA_API_KEY

Usage:
1. Run the script
2. Type your message at the "You: " prompt and press Enter
3. Listen to Gemini's response enhanced with your knowledge base
4. Type "quit" to exit
"""

import asyncio
import sys
import os
import pyaudio
from google import genai
from google.genai.types import LiveConnectConfig, HttpOptions, Modality
from rag_service import VectaraRAGService

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 24000  # Gemini uses 24kHz for audio output
CHUNK_SIZE = 1024


# Choose if you want to use VertexAI or Gemini Developer API
use_vertexai = False  # Set to True for Vertex AI, False for Gemini Developer API (Google AI Studio API_KEY)
PROJECT_ID = 'set-me-up'  # set this value with proper Project ID if you plan to use Vertex AI

# RAG Configuration
VECTARA_CUSTOMER_ID = os.getenv('VECTARA_CUSTOMER_ID')
VECTARA_CORPUS_ID = os.getenv('VECTARA_CORPUS_ID') 
VECTARA_API_KEY = os.getenv('VECTARA_API_KEY')

# Initialize RAG service
rag_service = VectaraRAGService(
    customer_id=VECTARA_CUSTOMER_ID,
    corpus_id=VECTARA_CORPUS_ID,
    api_key=VECTARA_API_KEY
) if all([VECTARA_CUSTOMER_ID, VECTARA_CORPUS_ID, VECTARA_API_KEY]) else None

# Configure API client and model based on selection
if use_vertexai:
    # Vertex AI configuration
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location='us-central1',
        http_options=HttpOptions(api_version="v1beta1")
    )
    MODEL = "gemini-2.0-flash-exp"  # Just the model name for Vertex AI
    CONFIG = LiveConnectConfig(response_modalities=[Modality.AUDIO])
else:
    # Gemini Developer API configuration
    # Make sure you have 'GOOGLE_API_KEY' variable set with API KEY or pass the api_key='...' in genai.Client()

    client = genai.Client(
        http_options={"api_version": "v1alpha"}
    )
    MODEL = "models/gemini-2.0-flash-exp"
    CONFIG = {"generation_config": {"response_modalities": ["AUDIO"]}}


# Initialize PyAudio
pya = pyaudio.PyAudio()

async def play_audio(audio_queue):
    """Plays audio chunks from the queue until receiving None signal."""
    # Open audio output stream
    stream = await asyncio.to_thread(
        pya.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        output=True,
    )
    
    try:
        while True:
            # Get the next audio chunk from the queue
            audio_bytes = await audio_queue.get()
            
            # None is our signal to stop
            if audio_bytes is None:
                break
                
            # Play the audio chunk
            await asyncio.to_thread(stream.write, audio_bytes)
    finally:
        # Clean up audio resources
        stream.stop_stream()
        stream.close()


async def chat_session():
    """Manages the chat session with Gemini enhanced with RAG, handling text input and audio output."""
    audio_queue = asyncio.Queue()
    conversation_history = []
    
    try:
        # Connect to Gemini API
        async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
            # Start audio playback task
            audio_task = asyncio.create_task(play_audio(audio_queue))
            
            if rag_service:
                print("RAG-enhanced chat started! Type 'quit' to exit.")
                print("The system will search your knowledge base for relevant context.")
            else:
                print("Chat started (RAG disabled - check Vectara credentials). Type 'quit' to exit.")
            
            # Main chat loop
            while True:
                # Get user input
                user_message = await asyncio.to_thread(input, "You: ")
                if user_message.lower() == "quit":
                    break
                
                # Process with RAG if available
                if rag_service and user_message.strip():
                    # Search for relevant context
                    retrieved_docs = rag_service.search(user_message, num_results=3)
                    
                    # Build enhanced prompt with context
                    enhanced_prompt = rag_service.build_context_prompt(user_message, retrieved_docs)
                    
                    # Store conversation context
                    conversation_history.append({
                        "user": user_message,
                        "context_docs": retrieved_docs,
                        "enhanced_prompt": enhanced_prompt
                    })
                    
                    # Show retrieved context
                    if retrieved_docs:
                        print(f"\nRetrieved {len(retrieved_docs)} relevant documents:")
                        for i, doc in enumerate(retrieved_docs, 1):
                            print(f"  {i}. Score: {doc['score']:.3f} - {doc['text'][:100]}...")
                        print()
                    
                    # Send enhanced prompt to Gemini
                    await session.send(input=enhanced_prompt, end_of_turn=True)
                else:
                    # Send original message if RAG is not available
                    await session.send(input=user_message or "Hello", end_of_turn=True)
                
                # Process Gemini's response
                async for response in session.receive():
                    if audio_data := response.data:
                        # Queue audio data for playback
                        audio_queue.put_nowait(audio_data)
                    elif text := response.text:
                        # Print any text responses
                        print("Gemini:", text, end="")
                
                print()  # New line after Gemini's full response
            
            # Clean up
            await session.close()
            await audio_queue.put(None)  # Signal audio player to stop
            await audio_task  # Wait for audio player to finish
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("RAG-enhanced chat session ended.")


if __name__ == "__main__":
    try:
        asyncio.run(chat_session())
    except KeyboardInterrupt:
        print("\nChat terminated by user.")
    finally:
        pya.terminate()
        print("Resources cleaned up.")