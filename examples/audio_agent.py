"""Audio Agent Example

A simple chat loop for testing audio tool.

Usage:
    pip install strands-pack[audio]
    python examples/audio_agent.py

Type 'exit' or 'quit' to end the session.
"""

import os
import sys

from pathlib import Path

# Get repo root (parent of examples/)
_repo_root = Path(__file__).resolve().parent.parent

# Change to repo root so secrets/ is found
os.chdir(_repo_root)

# Add src to path for local development
sys.path.insert(0, str(_repo_root / "src"))

from dotenv import load_dotenv
load_dotenv()

FFMPEG_PATH = os.getenv("FFMPEG_PATH")

if not FFMPEG_PATH:
    raise ValueError("FFMPEG_PATH is not set")

from strands import Agent
from strands_pack import audio

def main():
    agent = Agent(tools=[audio])

    print("\nAudio Agent Ready!")
    print("Tools: audio")
    print("Try:")
    print("  - 'Get information about an audio file'")
    print("  - 'Convert an audio file to a different format'")
    print("  - 'Trim an audio file to a specific time range'")
    print("  - 'Concatenate multiple audio files'")
    print("  - 'Adjust the volume of an audio file'")
    print("  - 'Normalize the volume of an audio file'")
    print("  - 'Fade an audio file in/out'")
    print("  - 'Split an audio file into segments'")
    print("  - 'Overlay one audio file on top of another'")
    print("  - 'Extract a segment of an audio file'")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            prompt = input("You: ").strip()
            if prompt.lower() in ("exit", "quit", "q"):
                break
            if prompt:
                agent(prompt)
                print() 
        except (KeyboardInterrupt, EOFError):
            break

    print("Goodbye!")

if __name__ == "__main__":
    main()