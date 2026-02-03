"""
AWS tagging helpers (production-minded defaults).

All AWS resources created by strands-pack tools should be tagged for:
- cost allocation
- cleanup / ownership
- governance

Defaults:
- managed-by=strands-pack
- component=<tool name>

Optional:
- STRANDS_PACK_AWS_TAGS: extra tags to apply (JSON object or "k=v,k2=v2")
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional


def _parse_env_tags(raw: str) -> Dict[str, str]:
    raw = (raw or "").strip()
    if not raw:
        return {}

    # JSON object
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                out: Dict[str, str] = {}
                for k, v in data.items():
                    if k is None or v is None:
                        continue
                    out[str(k)] = str(v)
                return out
        except Exception:
            return {}

    # k=v,k2=v2
    out: Dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k:
            out[k] = v
    return out


def aws_tags_dict(*, component: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Return tags as a simple dict[str,str], suitable for many AWS APIs (e.g., Lambda, SQS TagQueue).
    """
    merged: Dict[str, str] = {
        "managed-by": "strands-pack",
        "component": str(component),
    }

    merged.update(_parse_env_tags(os.getenv("STRANDS_PACK_AWS_TAGS", "")))
    if tags:
        merged.update({str(k): str(v) for k, v in tags.items() if k is not None and v is not None})

    # Enforce non-overridable tag.
    merged["managed-by"] = "strands-pack"
    return merged


def aws_tags_list(*, component: str, tags: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """
    Return tags as a list of {Key, Value}, suitable for APIs that want that shape.
    """
    d = aws_tags_dict(component=component, tags=tags)
    return [{"Key": k, "Value": v} for k, v in d.items()]


