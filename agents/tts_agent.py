import os
import logging
from gtts import gTTS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def text_to_mp3(text: str, filename: str) -> str:
    """
    Converts text to speech using Google Text-to-Speech (gTTS) and saves it as an MP3 file.

    Args:
        text (str): The text to convert to speech.
        filename (str): The desired name for the MP3 file (e.g., "narration.mp3").

    Returns:
        str: The full path to the saved MP3 file.
    """
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, filename)

    try:
        tts = gTTS(text=text, lang='en')
        tts.save(file_path)
        logging.info(f"Successfully saved speech to {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Error converting text to MP3: {e}")
        raise
