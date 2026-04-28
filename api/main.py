import os
import asyncio
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Load environment variables from .env.local if present
load_dotenv(dotenv_path='./.env.local')

# Assuming agents.transcript_agent exists and has generate_transcript
try:
    from agents.transcript_agent import generate_transcript
except ImportError as import_error:
    app.logger.error(f"Failed to import generate_transcript: {import_error}")
    # Define a fallback if import fails, to prevent app crash
    async def generate_transcript(app_data):
        return (f"Error: Transcript generation service not available. "
                f"Missing dependency: {import_error}", {})


@app.route('/api/transcript', methods=['POST'])
def get_generated_transcript_sync():
    """
    Receives app details, generates a transcript using URL content,
    and returns the transcript and source context.
    This is a synchronous Flask route that calls an async function.
    """
    if not request.is_json:
        app.logger.warning("Received non-JSON request for /api/transcript")
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    app_data = data.get('app')

    if not app_data:
        app.logger.warning("Missing 'app' data in request for /api/transcript")
        return jsonify({"error": "Missing 'app' data in request"}), 400

    app.logger.info(f"Received request for transcript generation for app: {app_data.get('name')}")

    try:
        # Run the async generate_transcript function using asyncio.run
        # This blocks the current thread until the async function completes.
        transcript, source_context = asyncio.run(generate_transcript(app_data))
        return jsonify({
            "transcript": transcript,
            "source_context": source_context
        })
    except Exception as e:
        app.logger.error(f"Error generating transcript for app {app_data.get('name')}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error during transcript generation", "details": str(e)}), 500

if __name__ == '__main__':
    # When running directly with `python api/main.py`
    # Ensure FLASK_APP is set for `flask run` if preferred.
    # E.g., export FLASK_APP=api/main.py
    # flask run --port 5000
    app.run(debug=True, port=5000)
