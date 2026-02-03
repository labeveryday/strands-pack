"""
Philips Hue Bridge Tool

Control Philips Hue lights, groups, and scenes.

Requires:
    pip install strands-pack[hue]

Environment variables:
    HUE_BRIDGE_IP: IP address of your Hue Bridge (optional if bridge_ip provided)

Supported actions
-----------------
- list_lights
    Parameters: none
- get_light
    Parameters: light_id or light_name (required)
- set_light
    Parameters: light_id or light_name (required), on (optional), brightness (optional),
                hue (optional), saturation (optional), xy (optional), ct (optional),
                transition_time (optional)
- turn_on
    Parameters: light_id or light_name or group_id or group_name (one required)
- turn_off
    Parameters: light_id or light_name or group_id or group_name (one required)
- list_groups
    Parameters: none
- get_group
    Parameters: group_id or group_name (required)
- set_group
    Parameters: group_id or group_name (required), on (optional), brightness (optional),
                hue (optional), saturation (optional), xy (optional), ct (optional),
                transition_time (optional)
- list_scenes
    Parameters: none
- get_scene
    Parameters: scene_id or scene_name (required)
- activate_scene
    Parameters: group_name (required), scene_name (required)
- create_scene
    Parameters: name (required), lights or group_id/group_name (required),
                capture_current (default True), light_states (optional)
- update_scene
    Parameters: scene_id or scene_name (required), name (optional),
                light_states (optional), capture_current (optional)
- delete_scene
    Parameters: scene_id or scene_name (required)
- set_color
    Parameters: light_id or light_name or group_id or group_name (one required),
                color (required - hex string like "#FF0000" or color name)
- set_brightness
    Parameters: light_id or light_name or group_id or group_name (one required),
                brightness (required - 0-254 or percentage 0-100)

- blink
    Parameters: light_id or light_name or group_id or group_name (one required),
                long (optional, default False)
- toggle
    Parameters: light_id or light_name or group_id or group_name (one required)
- set_color_temp
    Parameters: light_id or light_name or group_id or group_name (one required),
                kelvin (optional) or temp (optional: "warm"/"cool") or ct (optional)
- create_group
    Parameters: name (required), lights (required - list of light ids or names)
- delete_group
    Parameters: group_id or group_name (required), confirm_text (required)
- rename_light
    Parameters: light_id or light_name (required), name (required - new light name)
- effect
    Parameters: light_id or light_name or group_id or group_name (one required),
                effect (required: "none" or "colorloop")

Notes:
  - First connection requires pressing the bridge button within 30 seconds
  - Bridge IP can be found via the Hue app or by scanning: nmap -sP 192.168.1.0/24
  - Hue values: 0-65535 (red=0, green=25500, blue=46920)
  - Saturation: 0-254 (0=white, 254=full color)
  - Brightness: 0-254 (0=off, 254=max)
  - Color temperature (ct): 153-500 mireds (153=cold, 500=warm)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple, Union

from strands import tool

# Lazy import for phue
_phue = None
_bridge_cache: Dict[str, Any] = {}

# Common color name to RGB mapping
COLOR_MAP = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "pink": (255, 192, 203),
    "cyan": (0, 255, 255),
    "white": (255, 255, 255),
    "warm_white": (255, 244, 229),
    "cool_white": (255, 255, 255),
    "lavender": (230, 230, 250),
    "coral": (255, 127, 80),
    "teal": (0, 128, 128),
    "magenta": (255, 0, 255),
    "lime": (0, 255, 0),
    "gold": (255, 215, 0),
    "salmon": (250, 128, 114),
}


def _get_phue():
    global _phue
    if _phue is None:
        try:
            import phue
            _phue = phue
        except ImportError:
            raise ImportError("phue not installed. Run: pip install strands-pack[hue]") from None
    return _phue


def _get_bridge(bridge_ip: Optional[str] = None):
    """Get or create a Hue Bridge connection."""
    phue = _get_phue()

    if bridge_ip is None:
        bridge_ip = os.environ.get("HUE_BRIDGE_IP")

    if not bridge_ip:
        raise ValueError("bridge_ip required. Set HUE_BRIDGE_IP env var or provide bridge_ip parameter")

    if bridge_ip in _bridge_cache:
        return _bridge_cache[bridge_ip]

    bridge = phue.Bridge(bridge_ip)
    bridge.connect()
    _bridge_cache[bridge_ip] = bridge
    return bridge


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


def _rgb_to_xy(r: int, g: int, b: int) -> Tuple[float, float]:
    """Convert RGB to CIE xy color space for Hue lights."""
    # Normalize RGB values
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0

    # Apply gamma correction
    r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
    g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
    b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92

    # Convert to XYZ
    X = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    Y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    Z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    # Convert to xy
    total = X + Y + Z
    if total == 0:
        return (0.0, 0.0)
    x = X / total
    y = Y / total

    return (round(x, 4), round(y, 4))


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _parse_color(color: str) -> Tuple[float, float]:
    """Parse color string to xy values."""
    color_lower = color.lower().strip()

    # Check color map first
    if color_lower in COLOR_MAP:
        rgb = COLOR_MAP[color_lower]
        return _rgb_to_xy(*rgb)

    # Try hex color
    if color.startswith("#") or (len(color) == 6 and all(c in "0123456789abcdefABCDEF" for c in color)):
        rgb = _hex_to_rgb(color)
        return _rgb_to_xy(*rgb)

    raise ValueError(f"Unknown color: {color}. Use hex (#FF0000) or name (red, blue, green, etc.)")


def _kelvin_to_mired(k: int) -> int:
    # mired = 1,000,000 / kelvin
    if k <= 0:
        raise ValueError("kelvin must be a positive integer")
    return int(round(1_000_000 / float(k)))


def _clamp_ct(ct: int) -> int:
    # Hue ct: 153-500 mireds (153=cold, 500=warm)
    return max(153, min(500, int(ct)))


def _light_to_dict(light) -> Dict[str, Any]:
    """Convert a phue Light object to a dictionary."""
    return {
        "light_id": light.light_id,
        "name": light.name,
        "on": light.on,
        "brightness": light.brightness,
        "hue": light.hue,
        "saturation": light.saturation,
        "xy": light.xy,
        "colormode": light.colormode,
        "type": light.type,
        "reachable": getattr(light, "reachable", None),
    }


def _group_to_dict(group) -> Dict[str, Any]:
    """Convert a phue Group object to a dictionary."""
    # Extract light IDs from Light objects if needed
    lights = group.lights
    if lights and hasattr(lights[0], 'light_id'):
        lights = [l.light_id for l in lights]
    return {
        "group_id": group.group_id,
        "name": group.name,
        "lights": lights,
        "on": getattr(group, "on", None),
        "brightness": getattr(group, "brightness", None),
    }


def _scene_to_dict(scene) -> Dict[str, Any]:
    """Convert a phue Scene object to a dictionary."""
    return {
        "scene_id": scene.scene_id,
        "name": scene.name,
        "lights": scene.lights,
    }


def _find_light(bridge, light_id: Optional[int] = None, light_name: Optional[str] = None):
    """Find a light by ID or name."""
    if light_id is not None:
        lights_by_id = bridge.get_light_objects("id")
        if light_id in lights_by_id:
            return lights_by_id[light_id]
        raise ValueError(f"Light with ID {light_id} not found")

    if light_name is not None:
        lights_by_name = bridge.get_light_objects("name")
        if light_name in lights_by_name:
            return lights_by_name[light_name]
        # Try case-insensitive match
        for name, light in lights_by_name.items():
            if name.lower() == light_name.lower():
                return light
        raise ValueError(f"Light with name '{light_name}' not found")

    raise ValueError("Either light_id or light_name is required")


def _find_group(bridge, group_id: Optional[int] = None, group_name: Optional[str] = None):
    """Find a group by ID or name."""
    groups = bridge.groups

    if group_id is not None:
        for group in groups:
            if group.group_id == group_id:
                return group
        raise ValueError(f"Group with ID {group_id} not found")

    if group_name is not None:
        for group in groups:
            if group.name == group_name or group.name.lower() == group_name.lower():
                return group
        raise ValueError(f"Group with name '{group_name}' not found")

    raise ValueError("Either group_id or group_name is required")


# Action implementations
def _list_lights(bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """List all lights."""
    bridge = _get_bridge(bridge_ip)
    lights = bridge.lights

    return _ok(
        action="list_lights",
        lights=[_light_to_dict(light) for light in lights],
        count=len(lights),
    )


def _get_light(light_id: Optional[int] = None, light_name: Optional[str] = None,
               bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Get a specific light's state."""
    if not light_id and not light_name:
        return _err("Either light_id or light_name is required")

    bridge = _get_bridge(bridge_ip)
    light = _find_light(bridge, light_id, light_name)

    return _ok(
        action="get_light",
        light=_light_to_dict(light),
    )


def _set_light(light_id: Optional[int] = None, light_name: Optional[str] = None,
               on: Optional[bool] = None, brightness: Optional[int] = None,
               hue: Optional[int] = None, saturation: Optional[int] = None,
               xy: Optional[List[float]] = None, ct: Optional[int] = None,
               transition_time: Optional[int] = None,
               bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Set a light's state."""
    if not light_id and not light_name:
        return _err("Either light_id or light_name is required")

    bridge = _get_bridge(bridge_ip)
    light = _find_light(bridge, light_id, light_name)

    changes = {}
    if on is not None:
        light.on = on
        changes["on"] = on
    if brightness is not None:
        light.brightness = brightness
        changes["brightness"] = brightness
    if hue is not None:
        light.hue = hue
        changes["hue"] = hue
    if saturation is not None:
        light.saturation = saturation
        changes["saturation"] = saturation
    if xy is not None:
        light.xy = xy
        changes["xy"] = xy
    if ct is not None:
        light.colortemp = ct
        changes["ct"] = ct
    if transition_time is not None:
        light.transitiontime = transition_time
        changes["transition_time"] = transition_time

    return _ok(
        action="set_light",
        light_id=light.light_id,
        light_name=light.name,
        changes=changes,
    )


def _turn_on(light_id: Optional[int] = None, light_name: Optional[str] = None,
             group_id: Optional[int] = None, group_name: Optional[str] = None,
             brightness: Optional[int] = None,
             bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Turn on a light or group."""
    bridge = _get_bridge(bridge_ip)

    if light_id is not None or light_name is not None:
        light = _find_light(bridge, light_id, light_name)
        light.on = True
        if brightness is not None:
            light.brightness = brightness
        return _ok(action="turn_on", target_type="light", name=light.name, light_id=light.light_id)

    if group_id is not None or group_name is not None:
        group = _find_group(bridge, group_id, group_name)
        bridge.set_group(group.group_id, "on", True)
        if brightness is not None:
            bridge.set_group(group.group_id, "bri", brightness)
        return _ok(action="turn_on", target_type="group", name=group.name, group_id=group.group_id)

    return _err("Either light_id/light_name or group_id/group_name is required")


def _turn_off(light_id: Optional[int] = None, light_name: Optional[str] = None,
              group_id: Optional[int] = None, group_name: Optional[str] = None,
              bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Turn off a light or group."""
    bridge = _get_bridge(bridge_ip)

    if light_id is not None or light_name is not None:
        light = _find_light(bridge, light_id, light_name)
        light.on = False
        return _ok(action="turn_off", target_type="light", name=light.name, light_id=light.light_id)

    if group_id is not None or group_name is not None:
        group = _find_group(bridge, group_id, group_name)
        bridge.set_group(group.group_id, "on", False)
        return _ok(action="turn_off", target_type="group", name=group.name, group_id=group.group_id)

    return _err("Either light_id/light_name or group_id/group_name is required")


def _list_groups(bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """List all groups."""
    bridge = _get_bridge(bridge_ip)
    groups = bridge.groups

    return _ok(
        action="list_groups",
        groups=[_group_to_dict(group) for group in groups],
        count=len(groups),
    )


def _get_group(group_id: Optional[int] = None, group_name: Optional[str] = None,
               bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Get a specific group."""
    if not group_id and not group_name:
        return _err("Either group_id or group_name is required")

    bridge = _get_bridge(bridge_ip)
    group = _find_group(bridge, group_id, group_name)

    return _ok(
        action="get_group",
        group=_group_to_dict(group),
    )


def _set_group(group_id: Optional[int] = None, group_name: Optional[str] = None,
               on: Optional[bool] = None, brightness: Optional[int] = None,
               hue: Optional[int] = None, saturation: Optional[int] = None,
               xy: Optional[List[float]] = None, ct: Optional[int] = None,
               transition_time: Optional[int] = None,
               bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Set a group's state."""
    if not group_id and not group_name:
        return _err("Either group_id or group_name is required")

    bridge = _get_bridge(bridge_ip)
    group = _find_group(bridge, group_id, group_name)
    gid = group.group_id

    changes = {}
    if on is not None:
        bridge.set_group(gid, "on", on)
        changes["on"] = on
    if brightness is not None:
        bridge.set_group(gid, "bri", brightness)
        changes["brightness"] = brightness
    if hue is not None:
        bridge.set_group(gid, "hue", hue)
        changes["hue"] = hue
    if saturation is not None:
        bridge.set_group(gid, "sat", saturation)
        changes["saturation"] = saturation
    if xy is not None:
        bridge.set_group(gid, "xy", xy)
        changes["xy"] = xy
    if ct is not None:
        bridge.set_group(gid, "ct", ct)
        changes["ct"] = ct
    if transition_time is not None:
        bridge.set_group(gid, "transitiontime", transition_time)
        changes["transition_time"] = transition_time

    return _ok(
        action="set_group",
        group_id=gid,
        group_name=group.name,
        changes=changes,
    )


def _list_scenes(bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """List all scenes."""
    bridge = _get_bridge(bridge_ip)
    scenes = bridge.scenes

    return _ok(
        action="list_scenes",
        scenes=[_scene_to_dict(scene) for scene in scenes],
        count=len(scenes),
    )


def _activate_scene(group_name: str, scene_name: str,
                    bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Activate a scene on a group."""
    if not group_name:
        return _err("group_name is required")
    if not scene_name:
        return _err("scene_name is required")

    bridge = _get_bridge(bridge_ip)
    bridge.run_scene(group_name, scene_name)

    return _ok(
        action="activate_scene",
        group_name=group_name,
        scene_name=scene_name,
    )


def _create_scene(name: str, lights: Optional[List[Union[int, str]]] = None,
                  group_id: Optional[int] = None, group_name: Optional[str] = None,
                  capture_current: bool = True,
                  light_states: Optional[Dict[str, Dict]] = None,
                  bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Create a new scene.

    Args:
        name: Name for the new scene
        lights: List of light IDs to include (if not using group)
        group_id/group_name: Group to create scene for (uses group's lights)
        capture_current: If True, captures current light states (default)
        light_states: Optional dict of light_id -> state to set specific states
                     e.g. {"1": {"on": true, "bri": 254, "hue": 10000}}
    """
    if not name:
        return _err("name is required for the scene")

    bridge = _get_bridge(bridge_ip)

    # Determine which lights to include
    light_ids = []
    group_ref = None

    if group_id is not None or group_name is not None:
        group = _find_group(bridge, group_id, group_name)
        light_ids = [str(lid) for lid in group.lights]
        group_ref = group.group_id
    elif lights:
        # Convert light names to IDs if needed
        for light in lights:
            if isinstance(light, int):
                light_ids.append(str(light))
            else:
                found = _find_light(bridge, light_name=str(light))
                light_ids.append(str(found.light_id))
    else:
        return _err("Either lights list or group_id/group_name is required")

    # Build the scene data
    scene_data = {
        "name": name,
        "lights": light_ids,
        "recycle": False,  # Don't auto-delete
    }

    if group_ref:
        scene_data["group"] = str(group_ref)
        scene_data["type"] = "GroupScene"
    else:
        scene_data["type"] = "LightScene"

    # Create the scene via API
    # phue's request method: bridge.request('POST', '/api/<username>/scenes', data)
    result = bridge.request("POST", "/api/" + bridge.username + "/scenes", scene_data)

    if isinstance(result, list) and len(result) > 0:
        if "success" in result[0]:
            scene_id = result[0]["success"]["id"]

            # If capture_current is True, we need to store current light states
            # The Hue API captures current states by default when creating a scene
            # If light_states provided, set those instead
            if light_states:
                for lid, state in light_states.items():
                    bridge.request(
                        "PUT",
                        f"/api/{bridge.username}/scenes/{scene_id}/lightstates/{lid}",
                        state
                    )

            return _ok(
                action="create_scene",
                scene_id=scene_id,
                name=name,
                lights=light_ids,
                group_id=group_ref,
            )
        elif "error" in result[0]:
            return _err(result[0]["error"].get("description", "Unknown error"),
                       error_type="HueAPIError")

    return _err("Failed to create scene", error_type="HueAPIError")


def _delete_scene(scene_id: Optional[str] = None, scene_name: Optional[str] = None,
                  bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Delete a scene."""
    bridge = _get_bridge(bridge_ip)

    # Find scene ID if name provided
    if scene_id is None and scene_name:
        for scene in bridge.scenes:
            if scene.name == scene_name or scene.name.lower() == scene_name.lower():
                scene_id = scene.scene_id
                break
        if not scene_id:
            return _err(f"Scene with name '{scene_name}' not found")
    elif not scene_id:
        return _err("Either scene_id or scene_name is required")

    # Delete via API
    result = bridge.request("DELETE", f"/api/{bridge.username}/scenes/{scene_id}")

    if isinstance(result, list) and len(result) > 0:
        if "success" in result[0]:
            return _ok(
                action="delete_scene",
                scene_id=scene_id,
                deleted=True,
            )
        elif "error" in result[0]:
            return _err(result[0]["error"].get("description", "Unknown error"),
                       error_type="HueAPIError")

    return _ok(action="delete_scene", scene_id=scene_id, deleted=True)


def _update_scene(scene_id: Optional[str] = None, scene_name: Optional[str] = None,
                  name: Optional[str] = None,
                  light_states: Optional[Dict[str, Dict]] = None,
                  capture_current: bool = False,
                  bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Update a scene's name or light states.

    Args:
        scene_id/scene_name: Scene to update
        name: New name for the scene (optional)
        light_states: Dict of light_id -> state to update
                     e.g. {"1": {"on": true, "bri": 254, "hue": 10000}}
        capture_current: If True, update scene with current light states
    """
    bridge = _get_bridge(bridge_ip)

    # Find scene ID if name provided
    target_scene_id = scene_id
    if target_scene_id is None and scene_name:
        for scene in bridge.scenes:
            if scene.name == scene_name or scene.name.lower() == scene_name.lower():
                target_scene_id = scene.scene_id
                break
        if not target_scene_id:
            return _err(f"Scene with name '{scene_name}' not found")
    elif not target_scene_id:
        return _err("Either scene_id or scene_name is required")

    changes = {}

    # Update scene name if provided
    if name:
        bridge.request(
            "PUT",
            f"/api/{bridge.username}/scenes/{target_scene_id}",
            {"name": name}
        )
        changes["name"] = name

    # Update light states
    if light_states:
        for lid, state in light_states.items():
            bridge.request(
                "PUT",
                f"/api/{bridge.username}/scenes/{target_scene_id}/lightstates/{lid}",
                state
            )
        changes["light_states"] = list(light_states.keys())

    # Capture current states if requested
    if capture_current:
        # Get scene's lights
        scene_info = None
        for scene in bridge.scenes:
            if scene.scene_id == target_scene_id:
                scene_info = scene
                break

        if scene_info:
            lights_by_id = bridge.get_light_objects("id")
            for lid in scene_info.lights:
                lid_int = int(lid)
                if lid_int in lights_by_id:
                    light = lights_by_id[lid_int]
                    state = {
                        "on": light.on,
                        "bri": light.brightness,
                    }
                    if light.hue is not None:
                        state["hue"] = light.hue
                    if light.saturation is not None:
                        state["sat"] = light.saturation
                    if light.xy is not None:
                        state["xy"] = light.xy

                    bridge.request(
                        "PUT",
                        f"/api/{bridge.username}/scenes/{target_scene_id}/lightstates/{lid}",
                        state
                    )
            changes["captured_current"] = True

    return _ok(
        action="update_scene",
        scene_id=target_scene_id,
        changes=changes,
    )


def _get_scene(scene_id: Optional[str] = None, scene_name: Optional[str] = None,
               bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Get detailed scene information including light states."""
    bridge = _get_bridge(bridge_ip)

    # Find scene
    target_scene = None
    for scene in bridge.scenes:
        if scene_id and scene.scene_id == scene_id:
            target_scene = scene
            break
        elif scene_name and (scene.name == scene_name or scene.name.lower() == scene_name.lower()):
            target_scene = scene
            break

    if not target_scene:
        return _err(f"Scene not found: {scene_id or scene_name}")

    # Get detailed scene info from API
    scene_data = bridge.request("GET", f"/api/{bridge.username}/scenes/{target_scene.scene_id}")

    return _ok(
        action="get_scene",
        scene={
            "scene_id": target_scene.scene_id,
            "name": target_scene.name,
            "lights": target_scene.lights,
            "lightstates": scene_data.get("lightstates", {}),
            "type": scene_data.get("type"),
            "group": scene_data.get("group"),
        },
    )


def _set_color(light_id: Optional[int] = None, light_name: Optional[str] = None,
               group_id: Optional[int] = None, group_name: Optional[str] = None,
               color: Optional[str] = None,
               bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Set a light or group to a specific color."""
    if not color:
        return _err("color is required (hex like #FF0000 or name like 'red')")

    try:
        xy = _parse_color(color)
    except ValueError as e:
        return _err(str(e))

    bridge = _get_bridge(bridge_ip)

    if light_id is not None or light_name is not None:
        light = _find_light(bridge, light_id, light_name)
        light.on = True
        light.xy = list(xy)
        return _ok(
            action="set_color",
            target_type="light",
            name=light.name,
            light_id=light.light_id,
            color=color,
            xy=list(xy),
        )

    if group_id is not None or group_name is not None:
        group = _find_group(bridge, group_id, group_name)
        bridge.set_group(group.group_id, "on", True)
        bridge.set_group(group.group_id, "xy", list(xy))
        return _ok(
            action="set_color",
            target_type="group",
            name=group.name,
            group_id=group.group_id,
            color=color,
            xy=list(xy),
        )

    return _err("Either light_id/light_name or group_id/group_name is required")


def _set_brightness(light_id: Optional[int] = None, light_name: Optional[str] = None,
                    group_id: Optional[int] = None, group_name: Optional[str] = None,
                    brightness: Optional[int] = None, percent: Optional[int] = None,
                    bridge_ip: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Set brightness for a light or group."""
    if brightness is None and percent is None:
        return _err("Either brightness (0-254) or percent (0-100) is required")

    # Convert percent to brightness if needed
    if percent is not None:
        brightness = int((percent / 100) * 254)
    brightness = max(0, min(254, brightness))

    bridge = _get_bridge(bridge_ip)

    if light_id is not None or light_name is not None:
        light = _find_light(bridge, light_id, light_name)
        light.on = True
        light.brightness = brightness
        return _ok(
            action="set_brightness",
            target_type="light",
            name=light.name,
            light_id=light.light_id,
            brightness=brightness,
        )

    if group_id is not None or group_name is not None:
        group = _find_group(bridge, group_id, group_name)
        bridge.set_group(group.group_id, "on", True)
        bridge.set_group(group.group_id, "bri", brightness)
        return _ok(
            action="set_brightness",
            target_type="group",
            name=group.name,
            group_id=group.group_id,
            brightness=brightness,
        )

    return _err("Either light_id/light_name or group_id/group_name is required")


def _blink(
    light_id: Optional[int] = None,
    light_name: Optional[str] = None,
    group_id: Optional[int] = None,
    group_name: Optional[str] = None,
    long: bool = False,
    bridge_ip: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Blink/flash a light or group to identify it.

    Hue API uses "alert":
      - "select"  : one short flash
      - "lselect" : long/continuous flash until cancelled by setting "alert":"none"
    """
    bridge = _get_bridge(bridge_ip)
    alert = "lselect" if bool(long) else "select"

    if light_id is not None or light_name is not None:
        light = _find_light(bridge, light_id, light_name)
        bridge.set_light(light.light_id, "alert", alert)
        return _ok(action="blink", target_type="light", name=light.name, light_id=light.light_id, alert=alert)

    if group_id is not None or group_name is not None:
        group = _find_group(bridge, group_id, group_name)
        bridge.set_group(group.group_id, "alert", alert)
        return _ok(action="blink", target_type="group", name=group.name, group_id=group.group_id, alert=alert)

    return _err("Either light_id/light_name or group_id/group_name is required")


def _toggle(
    light_id: Optional[int] = None,
    light_name: Optional[str] = None,
    group_id: Optional[int] = None,
    group_name: Optional[str] = None,
    bridge_ip: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Toggle a light or group on/off."""
    bridge = _get_bridge(bridge_ip)

    if light_id is not None or light_name is not None:
        light = _find_light(bridge, light_id, light_name)
        new_state = not bool(light.on)
        light.on = new_state
        return _ok(action="toggle", target_type="light", name=light.name, light_id=light.light_id, on=new_state)

    if group_id is not None or group_name is not None:
        group = _find_group(bridge, group_id, group_name)
        # phue Group may not have a reliable .on property; use bridge.get_group state as source of truth
        try:
            g = bridge.get_group(group.group_id)
            current = bool((g.get("state") or {}).get("any_on") or (g.get("state") or {}).get("all_on"))
        except Exception:
            current = False
        new_state = not current
        bridge.set_group(group.group_id, "on", new_state)
        return _ok(action="toggle", target_type="group", name=group.name, group_id=group.group_id, on=new_state)

    return _err("Either light_id/light_name or group_id/group_name is required")


def _set_color_temp(
    light_id: Optional[int] = None,
    light_name: Optional[str] = None,
    group_id: Optional[int] = None,
    group_name: Optional[str] = None,
    ct: Optional[int] = None,
    kelvin: Optional[int] = None,
    temp: Optional[str] = None,
    bridge_ip: Optional[str] = None,
    transition_time: Optional[int] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Convenience for warm/cool white.

    Provide one of:
      - ct (mireds)
      - kelvin (converted to mireds)
      - temp = "warm" or "cool"
    """
    if ct is None and kelvin is None and not temp:
        return _err("Provide one of: ct, kelvin, temp")

    if ct is None and kelvin is not None:
        ct = _kelvin_to_mired(int(kelvin))
    if ct is None and temp:
        t = str(temp).strip().lower()
        if t in ("warm", "warm_white", "soft"):
            ct = 500
        elif t in ("cool", "cool_white", "daylight"):
            ct = 153
        else:
            return _err("temp must be 'warm' or 'cool'")

    assert ct is not None
    ct = _clamp_ct(int(ct))

    bridge = _get_bridge(bridge_ip)

    if light_id is not None or light_name is not None:
        light = _find_light(bridge, light_id, light_name)
        light.on = True
        light.ct = ct
        if transition_time is not None:
            # phue Light supports transitiontime via bridge.set_light
            bridge.set_light(light.light_id, {"ct": ct, "on": True, "transitiontime": int(transition_time)})
        return _ok(action="set_color_temp", target_type="light", name=light.name, light_id=light.light_id, ct=ct)

    if group_id is not None or group_name is not None:
        group = _find_group(bridge, group_id, group_name)
        payload: Dict[str, Any] = {"ct": ct, "on": True}
        if transition_time is not None:
            payload["transitiontime"] = int(transition_time)
        bridge.set_group(group.group_id, payload)
        return _ok(action="set_color_temp", target_type="group", name=group.name, group_id=group.group_id, ct=ct)

    return _err("Either light_id/light_name or group_id/group_name is required")


def _create_group(
    name: Optional[str] = None,
    lights: Optional[List[Union[int, str]]] = None,
    bridge_ip: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create a new group/room with the given lights."""
    if not name:
        return _err("name is required")
    if not isinstance(lights, list) or not lights:
        return _err("lights is required (list of light ids or names)")

    bridge = _get_bridge(bridge_ip)
    ids: List[int] = []
    for item in lights:
        if isinstance(item, int):
            ids.append(int(item))
        else:
            light = _find_light(bridge, light_name=str(item))
            ids.append(int(light.light_id))

    group_id = bridge.create_group(str(name), ids)
    return _ok(action="create_group", name=str(name), group_id=group_id, lights=ids)


def _delete_group(
    group_id: Optional[int] = None,
    group_name: Optional[str] = None,
    confirm_text: Optional[str] = None,
    bridge_ip: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Delete a group. Requires confirm_text."""
    bridge = _get_bridge(bridge_ip)
    group = _find_group(bridge, group_id, group_name)
    expected = f"DELETE_GROUP {group.group_id}"
    if confirm_text != expected:
        return _err(
            f"Destructive action requires confirm_text='{expected}'",
            error_type="ConfirmationRequired",
            expected_confirm_text=expected,
        )
    bridge.delete_group(group.group_id)
    return _ok(action="delete_group", group_id=group.group_id, name=group.name, deleted=True)


def _rename_light(
    light_id: Optional[int] = None,
    light_name: Optional[str] = None,
    name: Optional[str] = None,
    bridge_ip: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Rename a light."""
    if not name:
        return _err("name (new light name) is required")
    bridge = _get_bridge(bridge_ip)
    light = _find_light(bridge, light_id, light_name)
    old = light.name
    # phue supports setting name via property
    light.name = str(name)
    return _ok(action="rename_light", light_id=light.light_id, old_name=old, new_name=str(name))


def _effect(
    light_id: Optional[int] = None,
    light_name: Optional[str] = None,
    group_id: Optional[int] = None,
    group_name: Optional[str] = None,
    effect: Optional[str] = None,
    bridge_ip: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Set an effect (e.g., colorloop) for a light or group."""
    if not effect:
        return _err("effect is required (e.g., 'none' or 'colorloop')")
    e = str(effect).strip().lower()
    if e not in ("none", "colorloop"):
        return _err("effect must be 'none' or 'colorloop'")

    bridge = _get_bridge(bridge_ip)
    if light_id is not None or light_name is not None:
        light = _find_light(bridge, light_id, light_name)
        bridge.set_light(light.light_id, "effect", e)
        return _ok(action="effect", target_type="light", name=light.name, light_id=light.light_id, effect=e)

    if group_id is not None or group_name is not None:
        group = _find_group(bridge, group_id, group_name)
        bridge.set_group(group.group_id, "effect", e)
        return _ok(action="effect", target_type="group", name=group.name, group_id=group.group_id, effect=e)

    return _err("Either light_id/light_name or group_id/group_name is required")

_ACTIONS = {
    "list_lights": _list_lights,
    "get_light": _get_light,
    "set_light": _set_light,
    "turn_on": _turn_on,
    "turn_off": _turn_off,
    "list_groups": _list_groups,
    "get_group": _get_group,
    "set_group": _set_group,
    "list_scenes": _list_scenes,
    "get_scene": _get_scene,
    "activate_scene": _activate_scene,
    "create_scene": _create_scene,
    "update_scene": _update_scene,
    "delete_scene": _delete_scene,
    "set_color": _set_color,
    "set_brightness": _set_brightness,
    "blink": _blink,
    "toggle": _toggle,
    "set_color_temp": _set_color_temp,
    "create_group": _create_group,
    "delete_group": _delete_group,
    "rename_light": _rename_light,
    "effect": _effect,
}


@tool
def hue(
    action: str,
    bridge_ip: Optional[str] = None,
    light_id: Optional[int] = None,
    light_name: Optional[str] = None,
    group_id: Optional[int] = None,
    group_name: Optional[str] = None,
    scene_id: Optional[str] = None,
    scene_name: Optional[str] = None,
    on: Optional[bool] = None,
    brightness: Optional[int] = None,
    hue_value: Optional[int] = None,
    saturation: Optional[int] = None,
    xy: Optional[List[float]] = None,
    ct: Optional[int] = None,
    transition_time: Optional[int] = None,
    color: Optional[str] = None,
    percent: Optional[int] = None,
    name: Optional[str] = None,
    lights: Optional[List[Union[int, str]]] = None,
    capture_current: Optional[bool] = None,
    light_states: Optional[Dict[str, Dict]] = None,
    # New convenience / safety params
    kelvin: Optional[int] = None,
    temp: Optional[str] = None,
    effect: Optional[str] = None,
    confirm_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Control Philips Hue lights, groups, and scenes.

    Actions:
    - list_lights: List all lights
    - get_light: Get a specific light's state
    - set_light: Set a light's state (on, brightness, hue, saturation, xy, ct)
    - turn_on: Turn on a light or group
    - turn_off: Turn off a light or group
    - list_groups: List all groups
    - get_group: Get a specific group
    - set_group: Set a group's state
    - list_scenes: List all scenes
    - get_scene: Get detailed scene info including light states
    - activate_scene: Activate a scene on a group
    - create_scene: Create a new scene from current or specified light states
    - update_scene: Update a scene's name or light states
    - delete_scene: Delete a scene
    - set_color: Set a light/group to a color (hex or name)
    - set_brightness: Set brightness for a light or group
    - blink: Flash a light/group to identify it
    - toggle: Toggle a light/group on/off
    - set_color_temp: Convenience warm/cool white (ct/kelvin/temp)
    - create_group: Create a new group/room
    - delete_group: Delete a group (requires confirm_text)
    - rename_light: Rename a light
    - effect: Set light/group effect (none/colorloop)

    Args:
        action: The action to perform (required)
        bridge_ip: IP address of the Hue Bridge (optional, uses HUE_BRIDGE_IP env var if not provided)
        light_id: Light ID for light-specific actions
        light_name: Light name for light-specific actions
        group_id: Group ID for group-specific actions
        group_name: Group name for group-specific actions
        scene_id: Scene ID for scene-specific actions
        scene_name: Scene name for scene-specific actions
        on: Turn light/group on (True) or off (False)
        brightness: Brightness level 0-254
        hue_value: Hue value 0-65535 (red=0, green=25500, blue=46920)
        saturation: Saturation level 0-254 (0=white, 254=full color)
        xy: CIE xy color coordinates as [x, y]
        ct: Color temperature in mireds 153-500 (153=cold, 500=warm)
        transition_time: Transition time in tenths of a second
        color: Color as hex string (#FF0000) or name (red, blue, green, etc.)
        percent: Brightness as percentage 0-100 (alternative to brightness)
        name: Name for new scene (create_scene) or new name (update_scene)
        lights: List of light IDs or names for create_scene
        capture_current: Capture current light states for scene (default True for create_scene)
        light_states: Dict of light_id -> state for create_scene/update_scene
        kelvin: Color temperature in Kelvin (for set_color_temp)
        temp: Convenience temperature preset "warm" or "cool" (for set_color_temp)
        effect: Effect name for action="effect" ("none" or "colorloop")
        confirm_text: Confirmation string for destructive actions (e.g., delete_group)

    Returns:
        dict with success status and action-specific data

    Notes:
        - Set HUE_BRIDGE_IP env var or provide bridge_ip parameter
        - First connection requires pressing bridge button within 30 seconds
        - Hue: 0-65535 (red=0, green=25500, blue=46920)
        - Brightness: 0-254 (0=off, 254=max)
    """
    action = (action or "").strip().lower()

    if action not in _ACTIONS:
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=list(_ACTIONS.keys()),
        )

    # Build kwargs dict from explicit parameters
    kwargs: Dict[str, Any] = {}
    if bridge_ip is not None:
        kwargs["bridge_ip"] = bridge_ip
    if light_id is not None:
        kwargs["light_id"] = light_id
    if light_name is not None:
        kwargs["light_name"] = light_name
    if group_id is not None:
        kwargs["group_id"] = group_id
    if group_name is not None:
        kwargs["group_name"] = group_name
    if scene_id is not None:
        kwargs["scene_id"] = scene_id
    if scene_name is not None:
        kwargs["scene_name"] = scene_name
    if on is not None:
        kwargs["on"] = on
    if brightness is not None:
        kwargs["brightness"] = brightness
    if hue_value is not None:
        kwargs["hue"] = hue_value
    if saturation is not None:
        kwargs["saturation"] = saturation
    if xy is not None:
        kwargs["xy"] = xy
    if ct is not None:
        kwargs["ct"] = ct
    if transition_time is not None:
        kwargs["transition_time"] = transition_time
    if color is not None:
        kwargs["color"] = color
    if percent is not None:
        kwargs["percent"] = percent
    if name is not None:
        kwargs["name"] = name
    if lights is not None:
        kwargs["lights"] = lights
    if capture_current is not None:
        kwargs["capture_current"] = capture_current
    if light_states is not None:
        kwargs["light_states"] = light_states
    if kelvin is not None:
        kwargs["kelvin"] = kelvin
    if temp is not None:
        kwargs["temp"] = temp
    if effect is not None:
        kwargs["effect"] = effect
    if confirm_text is not None:
        kwargs["confirm_text"] = confirm_text

    try:
        return _ACTIONS[action](**kwargs)
    except ImportError as e:
        return _err(str(e), error_type="ImportError")
    except ValueError as e:
        return _err(str(e), error_type="ValueError", action=action)
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
