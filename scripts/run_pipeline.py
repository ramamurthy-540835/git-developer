import argparse
import os
import datetime

from agents.llm import generate_script
from agents.tts_agent import text_to_mp3
from agents.gcs_agent import upload_to_gcs

def run_pipeline(prompt: str):
    """
    Runs the full pipeline: generates a script, converts it to MP3, and uploads to GCS.
    """
    print(f"Generating script for prompt: '{prompt}'...")
    narration_script = generate_script(prompt)
    print("\n--- Script Preview ---")
    print(narration_script[:500] + "..." if len(narration_script) > 500 else narration_script)
    print("----------------------\n")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    mp3_filename = f"narration_{timestamp}.mp3"

    print(f"Converting script to MP3: {mp3_filename}...")
    local_mp3_path = text_to_mp3(narration_script, mp3_filename)
    print(f"Local file path: {local_mp3_path}")

    print(f"Uploading {local_mp3_path} to GCS...")
    gcs_path = upload_to_gcs(local_mp3_path)
    print(f"GCS path: {gcs_path}")
    
    print("\nPipeline completed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a narration script, convert to MP3, and upload to GCS.")
    parser.add_argument("prompt", type=str, help="The prompt for the narration script.")
    args = parser.parse_args()

    # Ensure output directory exists if not already handled by tts_agent
    os.makedirs("output", exist_ok=True)

    run_pipeline(args.prompt)
