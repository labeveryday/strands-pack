#!/usr/bin/env python3
"""
Philips Hue Agent Example

Demonstrates the hue tool for controlling Philips Hue lights.

Usage:
    python examples/hue_agent.py

Environment:
    HUE_BRIDGE_IP: IP address of your Hue Bridge (required)

Note:
    First connection requires pressing the bridge button within 30 seconds.
    Find your bridge IP in the Hue app or via: nmap -sP 192.168.1.0/24
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import hue


def main():
    """Run the hue agent."""
    agent = Agent(tools=[hue])

    print("=" * 60)
    print("Philips Hue Agent")
    print("=" * 60)
    print("\nThis agent controls Philips Hue lights, groups, and scenes.")
    print("\nAvailable actions:")
    print("  list_lights    - List all lights")
    print("  turn_on/off    - Turn lights or groups on/off")
    print("  toggle         - Toggle a light or group on/off")
    print("  blink          - Flash a light or group (identify)")
    print("  set_color      - Set color (hex #FF0000 or name 'red')")
    print("  set_brightness - Set brightness (0-254 or percent 0-100)")
    print("  set_color_temp - Set warm/cool white (temp='warm'/'cool' or kelvin=...)")
    print("  list_groups    - List all groups/rooms")
    print("  create_group   - Create a new group/room")
    print("  delete_group   - Delete a group (requires confirm_text)")
    print("  rename_light   - Rename a light")
    print("  effect         - Set effect (none/colorloop)")
    print("  list_scenes    - List all scenes")
    print("  activate_scene - Activate a scene")
    print("  create_scene   - Create a new scene from current states")
    print("\nColors: red, green, blue, yellow, orange, purple, pink,")
    print("        cyan, white, warm_white, cool_white, lavender, etc.")
    print("\nExample queries:")
    print("  - List all my lights")
    print("  - Turn on the living room")
    print("  - Toggle the desk lamp")
    print("  - Blink the bedroom light")
    print("  - Set office to warm white")
    print("  - Set kitchen to 4000 kelvin")
    print("  - Set bedroom to blue")
    print("  - Set kitchen brightness to 50%")
    print("  - Activate the 'Movie' scene in living room")
    print("  - Turn off all lights")
    print("\nType 'quit' or 'exit' to end.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            response = agent(user_input)
            print(f"\nAgent: {response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
