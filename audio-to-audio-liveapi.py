"""
Voice-to-Voice Chat with Gemini 2.0 Flash exp + RAG

This script creates a real-time voice conversation with Gemini AI enhanced with RAG capabilities.
It captures your voice from the microphone, searches Vectara for relevant context, and plays 
Gemini's voice responses through speakers.

Dependencies:
- google-genai
- pyaudio
- requests
- speechrecognition

Setup:
1. Install dependencies: pip install google-genai pyaudio requests speechrecognition
2. For Google AI Studio; Set GOOGLE_API_KEY environment variable with your API key and set use_vertexai to False in line 50.
   If you are using VertexAI check provide PROJECT_ID in line 51 and set use_vertexai to True in line 50.
3. Set Vectara credentials: VECTARA_CUSTOMER_ID, VECTARA_CORPUS_ID, VECTARA_API_KEY

Usage:
1. Run the script: python audio-to-audio-liveapi.py
2. Start speaking into your microphone
3. Listen to Gemini's responses enhanced with your knowledge base
4. Press Ctrl+C to exit

Note: Headphones are recommended to prevent audio feedback
"""

import asyncio
import os
import sys
import traceback
import pyaudio
import speech_recognition as sr
from google import genai
from google.genai.types import LiveConnectConfig, HttpOptions, Modality
from rag_service import VectaraRAGService

# # check if  Python >= 3.11
# if sys.version_info < (3, 11, 0):
#     print("Error: This script requires Python 3.11 or newer.")
#     print("Python 3.11 introduced asyncio.TaskGroup, which this script uses")
#     print("for concurrent task management with proper error handling.")
#     print("Please upgrade your Python installation.")
#     sys.exit(1)

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000     # Microphone input rate
RECEIVE_SAMPLE_RATE = 24000  # Gemini output rate
CHUNK_SIZE = 1024

# Response length configuration
MAX_RESPONSE_LENGTH = 100  # Maximum number of words in Gemini's response

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


pya = pyaudio.PyAudio()

# Initialize speech recognition
recognizer = sr.Recognizer()


class AudioLoopWithRAG:
    """Manages bidirectional audio streaming with Gemini enhanced with RAG capabilities."""
    
    def __init__(self):
        self.audio_in_queue = None  # Audio from Gemini to speakers
        self.out_queue = None       # Audio from microphone to Gemini
        self.session = None         # Gemini API session
        self.audio_stream = None    # Microphone stream
        self.rag_service = rag_service
        self.recognizer = recognizer
        self.conversation_history = []  # Store conversation context
        self.is_gemini_speaking = False  # Track if Gemini is currently speaking
        self.interruption_buffer = b""   # Buffer for interruption detection
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Convert audio to text for RAG processing."""
        try:
            # Convert audio data to AudioData object
            audio_file = sr.AudioData(audio_data, SEND_SAMPLE_RATE, 2)
            text = await asyncio.to_thread(
                self.recognizer.recognize_google, audio_file
            )
            return text
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
    
    async def process_with_rag(self, user_text: str) -> str:
        """Process user input with RAG retrieval."""
        if not user_text.strip() or not self.rag_service:
            return user_text
        
        # Search for relevant context
        retrieved_docs = self.rag_service.search(user_text, num_results=3)
        
        # Build enhanced prompt with context
        enhanced_prompt = self.rag_service.build_context_prompt(user_text, retrieved_docs, MAX_RESPONSE_LENGTH)
        
        # Store in conversation history
        self.conversation_history.append({
            "user": user_text,
            "context_docs": retrieved_docs,
            "enhanced_prompt": enhanced_prompt
        })
        
        # Show retrieved context
        if retrieved_docs:
            print(f"\nRetrieved {len(retrieved_docs)} relevant documents:")
            for i, doc in enumerate(retrieved_docs, 1):
                print(f"  {i}. Score: {doc['score']:.3f} - {doc['text'][:100]}...")
            print()
        
        return enhanced_prompt
    
    async def detect_interruption(self, audio_data: bytes) -> bool:
        """Detect if user is speaking (interrupting Gemini)."""
        if not self.is_gemini_speaking:
            return False
            
        # Add to interruption buffer
        self.interruption_buffer += audio_data
        
        # Check audio level for interruption
        if audio_data:
            import struct
            audio_samples = struct.unpack(f'{len(audio_data)//2}h', audio_data)
            rms = (sum(sample * sample for sample in audio_samples) / len(audio_samples)) ** 0.5
            audio_level = int(rms)
            
            # If audio level is high enough, it's an interruption
            if audio_level > 200:  # Higher threshold for interruption detection
                return True
        
        # Keep buffer size manageable
        if len(self.interruption_buffer) > SEND_SAMPLE_RATE * 2:  # 2 seconds max
            self.interruption_buffer = self.interruption_buffer[-SEND_SAMPLE_RATE:]
            
        return False
    
    async def listen_audio(self):
        """Captures audio from microphone and processes with RAG before sending."""
        # Get default microphone
        mic_info = pya.get_default_input_device_info()
        
        # Open microphone stream
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT, 
            channels=CHANNELS, 
            rate=SEND_SAMPLE_RATE,
            input=True, 
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        
        # Handle buffer overflow silently
        kwargs = {"exception_on_overflow": False} if __debug__ else {}
        
        # Buffer for collecting audio chunks
        audio_buffer = b""
        silence_threshold = 1.5  # seconds of silence before processing
        min_audio_length = SEND_SAMPLE_RATE * 2  # minimum 2 seconds of audio
        last_audio_time = 0
        is_recording = False
        
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            audio_buffer += data
            current_time = asyncio.get_event_loop().time()
            
            # Check for interruption first
            is_interruption = await self.detect_interruption(data)
            if is_interruption:
                print(f"\n🛑 Interruption detected! Stopping Gemini...")
                self.is_gemini_speaking = False
                # Clear any pending audio from Gemini
                while not self.audio_in_queue.empty():
                    try:
                        self.audio_in_queue.get_nowait()
                    except:
                        pass
                # Reset recording state to process the interruption
                is_recording = True
                last_audio_time = current_time
                audio_buffer = self.interruption_buffer  # Use interruption buffer
                self.interruption_buffer = b""
                continue
            
            # Check if we have audio (proper volume calculation for 16-bit audio)
            if data:
                # Convert bytes to 16-bit integers and calculate RMS (Root Mean Square)
                import struct
                audio_samples = struct.unpack(f'{len(data)//2}h', data)
                rms = (sum(sample * sample for sample in audio_samples) / len(audio_samples)) ** 0.5
                audio_level = int(rms)
            else:
                audio_level = 0
            
            # Debug: Always show audio level
            status = "🔊" if self.is_gemini_speaking else "🎤"
            print(f"{status} Audio level: {audio_level}", end="\r")
            
            if audio_level > 100:  # Adjusted threshold for RMS calculation
                if not is_recording:
                    print(f"\n🎤 Started recording (level: {audio_level})")
                is_recording = True
                last_audio_time = current_time
            else:
                # No audio detected - update silence time
                if is_recording:
                    silence_time = current_time - last_audio_time
                    print(f"🎤 Recording... (buffer: {len(audio_buffer)}, silence: {silence_time:.1f}s, min: {min_audio_length})", end="\r")
            
            # Process audio if we have enough and there's been silence
            if (is_recording and 
                len(audio_buffer) > min_audio_length and 
                (current_time - last_audio_time) > silence_threshold):
                
                print(f"\n🔄 Processing audio (length: {len(audio_buffer)} bytes, duration: {len(audio_buffer)/SEND_SAMPLE_RATE:.1f}s)")
                
                # Transcribe the buffered audio
                print("🎤 Transcribing...")
                user_text = await self.transcribe_audio(audio_buffer)
                
                if user_text and len(user_text.strip()) > 3:  # Only process if we have meaningful text
                    print(f"📝 You said: '{user_text}'")
                    print("🔍 Searching knowledge base...")
                    # Process with RAG
                    enhanced_prompt = await self.process_with_rag(user_text)
                    print("🤖 Sending to Gemini...")
                    # Send enhanced prompt to Gemini as text
                    await self.out_queue.put({"text": enhanced_prompt})
                else:
                    print(f"❌ Transcription failed or too short: '{user_text}'")
                    print("💡 Try speaking louder or more clearly")
                
                # Reset buffer and recording state
                audio_buffer = b""
                is_recording = False
                last_audio_time = current_time
    
    async def receive_audio(self):
        """Receives audio responses from Gemini."""
        while True:
            # Get next response from Gemini
            turn = self.session.receive()
            
            # Mark that Gemini is starting to speak
            self.is_gemini_speaking = True
            
            async for response in turn:
                # Handle audio data
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                
                # Handle text (if model includes it)
                if text := response.text:
                    print("Gemini:", text, end="")
            
            # Mark that Gemini has finished speaking
            self.is_gemini_speaking = False
            print()  # New line after Gemini's turn completes
    
    async def play_audio(self):
        """Plays audio responses through speakers."""
        # Open audio output stream
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT, 
            channels=CHANNELS, 
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        
        # Play each audio chunk as it arrives
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)
    
    async def send_realtime(self):
        """Sends microphone audio or text to Gemini API."""
        while True:
            msg = await self.out_queue.get()
            if "text" in msg:
                # Send as text input
                await self.session.send(input=msg["text"], end_of_turn=True)
            else:
                # Send as audio input
                await self.session.send(input=msg)
    
    async def run(self):
        """Coordinates all audio streaming tasks."""
        try:
            # Connect to Gemini API
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)  # Limit buffer size
                
                if self.rag_service:
                    print("RAG-enhanced voice chat started. Speak into your microphone. Press Ctrl+C to quit.")
                    print("The system will search your knowledge base for relevant context.")
                else:
                    print("Voice chat started (RAG disabled - check Vectara credentials). Speak into your microphone. Press Ctrl+C to quit.")
                print("Note: Using headphones is recommended to prevent feedback.")
                print("🎤 Testing microphone... Speak now to see audio levels!")
                print("🔍 If you don't see changing audio levels, check microphone permissions!")
                
                # Start all tasks
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())
                
                # Run until interrupted
                await asyncio.Future() 
                
        except asyncio.CancelledError:
            pass
        except ExceptionGroup as EG:
            if self.audio_stream:
                self.audio_stream.close()
            traceback.print_exception(EG)
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            print("RAG-enhanced voice chat session ended.")


if __name__ == "__main__":
    try:
        main = AudioLoopWithRAG()
        asyncio.run(main.run())
    except KeyboardInterrupt:
        print("\nChat terminated by user.")
    finally:
        pya.terminate()
        print("Audio resources released.")