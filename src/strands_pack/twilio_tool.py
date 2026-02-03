"""
Twilio Tool

Send SMS, make voice calls, and send WhatsApp messages via Twilio.

Requires:
    pip install strands-pack[twilio]

Authentication:
    Set environment variables:
    - TWILIO_ACCOUNT_SID: Your Twilio Account SID
    - TWILIO_AUTH_TOKEN: Your Twilio Auth Token
    - TWILIO_PHONE_NUMBER: Your Twilio phone number (optional, can pass per-call)

Supported actions
-----------------
- send_sms
    Parameters: to (required), body (required), from_number (optional)
- send_whatsapp
    Parameters: to (required), body (required), from_number (optional)
- make_call
    Parameters: to (required), twiml (optional), url (optional), from_number (optional)
- get_message
    Parameters: message_sid (required)
- list_messages
    Parameters: to (optional), from_number (optional), limit (default 20)
- get_call
    Parameters: call_sid (required)
- list_calls
    Parameters: to (optional), from_number (optional), limit (default 20)
- lookup
    Parameters: phone_number (required), type (optional: "carrier", "caller-name")
- get_account
    Parameters: none

Notes:
  - Phone numbers should be in E.164 format (e.g., +15551234567)
  - WhatsApp numbers need "whatsapp:" prefix, but this tool adds it automatically
  - For voice calls, provide either twiml (XML) or url (TwiML Bin URL)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from strands import tool

# Lazy import for requests
_requests = None


def _get_requests():
    global _requests
    if _requests is None:
        try:
            import requests
            _requests = requests
        except ImportError:
            raise ImportError("requests not installed. Run: pip install strands-pack[twilio]") from None
    return _requests


def _get_credentials():
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

    if not account_sid:
        raise ValueError("TWILIO_ACCOUNT_SID environment variable is not set")
    if not auth_token:
        raise ValueError("TWILIO_AUTH_TOKEN environment variable is not set")

    return account_sid, auth_token


def _get_default_from():
    return os.environ.get("TWILIO_PHONE_NUMBER")


BASE_URL = "https://api.twilio.com/2010-04-01"


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, *, error_type: Optional[str] = None, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    if error_type:
        out["error_type"] = error_type
    out.update(data)
    return out


def _handle_response(response) -> tuple:
    """Handle Twilio API response."""
    if response.status_code >= 400:
        try:
            error_data = response.json()
            message = error_data.get("message", response.text)
            code = error_data.get("code")
            return None, f"Twilio error {code}: {message}" if code else message
        except Exception:
            return None, f"HTTP {response.status_code}: {response.text[:200]}"

    try:
        return response.json(), None
    except Exception:
        return None, f"Failed to parse response: {response.text[:200]}"


def _format_phone(phone: str, whatsapp: bool = False) -> str:
    """Format phone number, adding whatsapp: prefix if needed."""
    phone = phone.strip()
    if whatsapp and not phone.startswith("whatsapp:"):
        phone = f"whatsapp:{phone}"
    return phone


def _extract_message(msg: Dict) -> Dict[str, Any]:
    """Extract relevant message fields."""
    return {
        "sid": msg.get("sid"),
        "from": msg.get("from"),
        "to": msg.get("to"),
        "body": msg.get("body"),
        "status": msg.get("status"),
        "direction": msg.get("direction"),
        "date_created": msg.get("date_created"),
        "date_sent": msg.get("date_sent"),
        "price": msg.get("price"),
        "price_unit": msg.get("price_unit"),
        "error_code": msg.get("error_code"),
        "error_message": msg.get("error_message"),
    }


def _extract_call(call: Dict) -> Dict[str, Any]:
    """Extract relevant call fields."""
    return {
        "sid": call.get("sid"),
        "from": call.get("from"),
        "to": call.get("to"),
        "status": call.get("status"),
        "direction": call.get("direction"),
        "duration": call.get("duration"),
        "start_time": call.get("start_time"),
        "end_time": call.get("end_time"),
        "price": call.get("price"),
        "price_unit": call.get("price_unit"),
    }


def _send_sms(to: str, body: str, from_number: Optional[str] = None,
              **kwargs) -> Dict[str, Any]:
    """Send an SMS message."""
    if not to:
        return _err("to is required")
    if not body:
        return _err("body is required")

    from_number = from_number or _get_default_from()
    if not from_number:
        return _err("from_number is required (set TWILIO_PHONE_NUMBER or pass from_number)")

    requests = _get_requests()
    account_sid, auth_token = _get_credentials()

    response = requests.post(
        f"{BASE_URL}/Accounts/{account_sid}/Messages.json",
        auth=(account_sid, auth_token),
        data={
            "To": to,
            "From": from_number,
            "Body": body,
        },
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="TwilioError")

    return _ok(
        action="send_sms",
        message=_extract_message(data),
    )


def _send_whatsapp(to: str, body: str, from_number: Optional[str] = None,
                   **kwargs) -> Dict[str, Any]:
    """Send a WhatsApp message."""
    if not to:
        return _err("to is required")
    if not body:
        return _err("body is required")

    from_number = from_number or _get_default_from()
    if not from_number:
        return _err("from_number is required (set TWILIO_PHONE_NUMBER or pass from_number)")

    requests = _get_requests()
    account_sid, auth_token = _get_credentials()

    # Add whatsapp: prefix if not present
    to = _format_phone(to, whatsapp=True)
    from_number = _format_phone(from_number, whatsapp=True)

    response = requests.post(
        f"{BASE_URL}/Accounts/{account_sid}/Messages.json",
        auth=(account_sid, auth_token),
        data={
            "To": to,
            "From": from_number,
            "Body": body,
        },
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="TwilioError")

    return _ok(
        action="send_whatsapp",
        message=_extract_message(data),
    )


def _make_call(to: str, twiml: Optional[str] = None, url: Optional[str] = None,
               from_number: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Make a voice call."""
    if not to:
        return _err("to is required")
    if not twiml and not url:
        return _err("Either twiml or url is required")

    from_number = from_number or _get_default_from()
    if not from_number:
        return _err("from_number is required (set TWILIO_PHONE_NUMBER or pass from_number)")

    requests = _get_requests()
    account_sid, auth_token = _get_credentials()

    call_data = {
        "To": to,
        "From": from_number,
    }

    if twiml:
        call_data["Twiml"] = twiml
    elif url:
        call_data["Url"] = url

    response = requests.post(
        f"{BASE_URL}/Accounts/{account_sid}/Calls.json",
        auth=(account_sid, auth_token),
        data=call_data,
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="TwilioError")

    return _ok(
        action="make_call",
        call=_extract_call(data),
    )


def _get_message(message_sid: str, **kwargs) -> Dict[str, Any]:
    """Get details of a specific message."""
    if not message_sid:
        return _err("message_sid is required")

    requests = _get_requests()
    account_sid, auth_token = _get_credentials()

    response = requests.get(
        f"{BASE_URL}/Accounts/{account_sid}/Messages/{message_sid}.json",
        auth=(account_sid, auth_token),
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="TwilioError")

    return _ok(
        action="get_message",
        message=_extract_message(data),
    )


def _list_messages(to: Optional[str] = None, from_number: Optional[str] = None,
                   limit: int = 20, **kwargs) -> Dict[str, Any]:
    """List messages."""
    requests = _get_requests()
    account_sid, auth_token = _get_credentials()

    params = {"PageSize": min(limit, 100)}
    if to:
        params["To"] = to
    if from_number:
        params["From"] = from_number

    response = requests.get(
        f"{BASE_URL}/Accounts/{account_sid}/Messages.json",
        auth=(account_sid, auth_token),
        params=params,
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="TwilioError")

    messages = [_extract_message(m) for m in data.get("messages", [])]

    return _ok(
        action="list_messages",
        messages=messages,
        count=len(messages),
    )


def _get_call(call_sid: str, **kwargs) -> Dict[str, Any]:
    """Get details of a specific call."""
    if not call_sid:
        return _err("call_sid is required")

    requests = _get_requests()
    account_sid, auth_token = _get_credentials()

    response = requests.get(
        f"{BASE_URL}/Accounts/{account_sid}/Calls/{call_sid}.json",
        auth=(account_sid, auth_token),
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="TwilioError")

    return _ok(
        action="get_call",
        call=_extract_call(data),
    )


def _list_calls(to: Optional[str] = None, from_number: Optional[str] = None,
                limit: int = 20, **kwargs) -> Dict[str, Any]:
    """List calls."""
    requests = _get_requests()
    account_sid, auth_token = _get_credentials()

    params = {"PageSize": min(limit, 100)}
    if to:
        params["To"] = to
    if from_number:
        params["From"] = from_number

    response = requests.get(
        f"{BASE_URL}/Accounts/{account_sid}/Calls.json",
        auth=(account_sid, auth_token),
        params=params,
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="TwilioError")

    calls = [_extract_call(c) for c in data.get("calls", [])]

    return _ok(
        action="list_calls",
        calls=calls,
        count=len(calls),
    )


def _lookup(phone_number: str, type: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Look up information about a phone number."""
    if not phone_number:
        return _err("phone_number is required")

    requests = _get_requests()
    account_sid, auth_token = _get_credentials()

    # Lookup API uses a different base URL
    lookup_url = f"https://lookups.twilio.com/v1/PhoneNumbers/{phone_number}"

    params = {}
    if type:
        params["Type"] = type

    response = requests.get(
        lookup_url,
        auth=(account_sid, auth_token),
        params=params,
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="TwilioError")

    result = {
        "phone_number": data.get("phone_number"),
        "national_format": data.get("national_format"),
        "country_code": data.get("country_code"),
        "carrier": data.get("carrier"),
        "caller_name": data.get("caller_name"),
    }

    return _ok(
        action="lookup",
        lookup=result,
    )


def _get_account(**kwargs) -> Dict[str, Any]:
    """Get account information."""
    requests = _get_requests()
    account_sid, auth_token = _get_credentials()

    response = requests.get(
        f"{BASE_URL}/Accounts/{account_sid}.json",
        auth=(account_sid, auth_token),
        timeout=30,
    )

    data, error = _handle_response(response)
    if error:
        return _err(error, error_type="TwilioError")

    return _ok(
        action="get_account",
        account={
            "sid": data.get("sid"),
            "friendly_name": data.get("friendly_name"),
            "status": data.get("status"),
            "type": data.get("type"),
            "date_created": data.get("date_created"),
        },
    )


_ACTIONS = {
    "send_sms": _send_sms,
    "send_whatsapp": _send_whatsapp,
    "make_call": _make_call,
    "get_message": _get_message,
    "list_messages": _list_messages,
    "get_call": _get_call,
    "list_calls": _list_calls,
    "lookup": _lookup,
    "get_account": _get_account,
}


@tool
def twilio_tool(
    action: str,
    to: Optional[str] = None,
    body: Optional[str] = None,
    from_number: Optional[str] = None,
    twiml: Optional[str] = None,
    url: Optional[str] = None,
    message_sid: Optional[str] = None,
    call_sid: Optional[str] = None,
    phone_number: Optional[str] = None,
    lookup_type: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Send SMS, make voice calls, and send WhatsApp messages via Twilio.

    Actions:
    - send_sms: Send an SMS message
    - send_whatsapp: Send a WhatsApp message
    - make_call: Make a voice call (provide twiml or url)
    - get_message: Get details of a specific message
    - list_messages: List messages
    - get_call: Get details of a specific call
    - list_calls: List calls
    - lookup: Look up information about a phone number
    - get_account: Get account information

    Args:
        action: The action to perform (send_sms, send_whatsapp, make_call, get_message,
                list_messages, get_call, list_calls, lookup, get_account)
        to: Phone number to send to (E.164 format, e.g., +15551234567).
            Required for: send_sms, send_whatsapp, make_call.
            Optional for: list_messages, list_calls (filter).
        body: Message body text. Required for: send_sms, send_whatsapp.
        from_number: Phone number to send from. Optional - defaults to TWILIO_PHONE_NUMBER env var.
            Used by: send_sms, send_whatsapp, make_call, list_messages, list_calls.
        twiml: TwiML XML for voice calls. Either twiml or url required for make_call.
        url: TwiML Bin URL for voice calls. Either twiml or url required for make_call.
        message_sid: Message SID. Required for: get_message.
        call_sid: Call SID. Required for: get_call.
        phone_number: Phone number to look up. Required for: lookup.
        lookup_type: Lookup type ("carrier" or "caller-name"). Optional for: lookup.
        limit: Maximum number of results to return (default 20, max 100).
               Used by: list_messages, list_calls.

    Returns:
        dict with success status and action-specific data

    Authentication:
        Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and optionally TWILIO_PHONE_NUMBER.
    """
    action_name = (action or "").strip().lower()

    if action_name not in _ACTIONS:
        return _err(
            f"Unknown action: {action_name}",
            error_type="InvalidAction",
            available_actions=list(_ACTIONS.keys()),
        )

    # Build kwargs dict from explicit parameters
    kwargs: Dict[str, Any] = {}
    if to is not None:
        kwargs["to"] = to
    if body is not None:
        kwargs["body"] = body
    if from_number is not None:
        kwargs["from_number"] = from_number
    if twiml is not None:
        kwargs["twiml"] = twiml
    if url is not None:
        kwargs["url"] = url
    if message_sid is not None:
        kwargs["message_sid"] = message_sid
    if call_sid is not None:
        kwargs["call_sid"] = call_sid
    if phone_number is not None:
        kwargs["phone_number"] = phone_number
    if lookup_type is not None:
        kwargs["type"] = lookup_type
    kwargs["limit"] = limit

    try:
        return _ACTIONS[action_name](**kwargs)
    except ImportError as e:
        return _err(str(e), error_type="ImportError")
    except ValueError as e:
        return _err(str(e), error_type="ValueError")
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action_name)
