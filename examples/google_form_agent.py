#!/usr/bin/env python3
"""
Google Forms Agent Example

Demonstrates the Google Forms tool capabilities.

Prerequisites:
    1. Create OAuth credentials in Google Cloud Console (Desktop app)
    2. Run: python examples/google_oauth_token.py --client-secrets client_secret.json --preset forms --out secrets/token.json
    3. Set GOOGLE_AUTHORIZED_USER_FILE=secrets/token.json in .env

Usage:
    pip install strands-pack[forms]
    python examples/google_form_agent.py
"""
import os
from pathlib import Path

_dotenv_path = Path.cwd() / ".env"
if not _dotenv_path.exists():
    _dotenv_path = Path(__file__).resolve().parents[1] / ".env"

try:
    from dotenv import load_dotenv

    if _dotenv_path.exists():
        load_dotenv(_dotenv_path)
except ImportError:
    pass

# Make token path absolute
token_file = os.environ.get("GOOGLE_AUTHORIZED_USER_FILE", "")
if token_file and not Path(token_file).is_absolute():
    os.environ["GOOGLE_AUTHORIZED_USER_FILE"] = str(Path.cwd() / token_file)

from strands_pack import google_forms


def main():
    token_path = os.environ.get("GOOGLE_AUTHORIZED_USER_FILE")
    if not token_path or not Path(token_path).exists():
        print("Error: GOOGLE_AUTHORIZED_USER_FILE not set or file not found")
        print("Run examples/google_oauth_token.py to generate a token first")
        return

    print("Google Forms Tool Demo")
    print("=" * 50)

    # 1. Create a form
    print("\n1. Creating a new form...")
    result = google_forms(
        action="create_form",
        form={"info": {"title": "Customer Feedback Survey"}}
    )
    if not result.get("success"):
        print(f"Error: {result.get('error')}")
        return

    form_id = result["form"]["formId"]
    responder_url = result["form"]["responderUri"]
    print(f"   Created form ID: {form_id}")
    print(f"   Responder URL: {responder_url}")

    # 2. Add questions using batch_update
    print("\n2. Adding questions...")
    result = google_forms(
        action="batch_update",
        form_id=form_id,
        requests=[
            {
                "createItem": {
                    "item": {
                        "title": "How satisfied are you with our service?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "scaleQuestion": {
                                    "low": 1,
                                    "high": 5,
                                    "lowLabel": "Not satisfied",
                                    "highLabel": "Very satisfied"
                                }
                            }
                        }
                    },
                    "location": {"index": 0}
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "What could we improve?",
                        "questionItem": {
                            "question": {
                                "required": False,
                                "textQuestion": {"paragraph": True}
                            }
                        }
                    },
                    "location": {"index": 1}
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "Would you recommend us to a friend?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": "Yes"},
                                        {"value": "No"},
                                        {"value": "Maybe"}
                                    ]
                                }
                            }
                        }
                    },
                    "location": {"index": 2}
                }
            }
        ]
    )
    if result.get("success"):
        print("   Added 3 questions successfully")
    else:
        print(f"   Error: {result.get('error')}")

    # 3. Get form details
    print("\n3. Fetching form details...")
    result = google_forms(action="get_form", form_id=form_id)
    if result.get("success"):
        form = result["form"]
        print(f"   Title: {form['info']['title']}")
        print(f"   Questions: {len(form.get('items', []))}")
        for item in form.get("items", []):
            print(f"   - {item.get('title', 'Untitled')}")
    else:
        print(f"   Error: {result.get('error')}")

    # 4. List responses (will be empty for new form)
    print("\n4. Listing responses...")
    result = google_forms(action="list_responses", form_id=form_id)
    if result.get("success"):
        responses = result.get("responses", [])
        print(f"   Total responses: {len(responses)}")
    else:
        print(f"   Error: {result.get('error')}")

    print("\n" + "=" * 50)
    print("Demo complete!")
    print(f"\nShare this form: {responder_url}")
    print(f"Edit form: https://docs.google.com/forms/d/{form_id}/edit")


if __name__ == "__main__":
    main()
