"""Tests for Hue Bridge tool."""

from unittest.mock import MagicMock, patch

import pytest


def test_hue_unknown_action():
    """Test error for unknown action."""
    from strands_pack import hue

    result = hue(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result


def test_hue_list_lights_missing_bridge():
    """Test error when bridge IP is missing."""
    from strands_pack import hue
    from strands_pack.hue import _bridge_cache

    # Clear cache and env
    _bridge_cache.clear()

    with patch.dict("os.environ", {}, clear=True):
        result = hue(action="list_lights")

    assert result["success"] is False
    assert "bridge_ip" in result["error"].lower() or "not installed" in result["error"].lower()


def test_hue_get_light_missing_params():
    """Test error when light identifier is missing."""
    from strands_pack import hue

    # Mock to avoid bridge connection
    with patch("strands_pack.hue._get_bridge"):
        result = hue(action="get_light")

    assert result["success"] is False
    assert "light_id" in result["error"] or "light_name" in result["error"]


def test_hue_set_light_missing_params():
    """Test error when light identifier is missing for set_light."""
    from strands_pack import hue

    result = hue(action="set_light", on=True)

    assert result["success"] is False
    assert "light_id" in result["error"] or "light_name" in result["error"]


def test_hue_get_group_missing_params():
    """Test error when group identifier is missing."""
    from strands_pack import hue

    with patch("strands_pack.hue._get_bridge"):
        result = hue(action="get_group")

    assert result["success"] is False
    assert "group_id" in result["error"] or "group_name" in result["error"]


def test_hue_set_group_missing_params():
    """Test error when group identifier is missing for set_group."""
    from strands_pack import hue

    result = hue(action="set_group", on=True)

    assert result["success"] is False
    assert "group_id" in result["error"] or "group_name" in result["error"]


def test_hue_activate_scene_missing_group():
    """Test error when group_name is missing for activate_scene."""
    from strands_pack import hue

    result = hue(action="activate_scene", scene_name="Energize")

    assert result["success"] is False
    assert "group_name" in result["error"]


def test_hue_activate_scene_missing_scene():
    """Test error when scene_name is missing for activate_scene."""
    from strands_pack import hue

    result = hue(action="activate_scene", group_name="Office")

    assert result["success"] is False
    assert "scene_name" in result["error"]


def test_hue_set_color_missing_color():
    """Test error when color is missing for set_color."""
    from strands_pack import hue

    result = hue(action="set_color", light_name="Desk lamp")

    assert result["success"] is False
    assert "color" in result["error"]


def test_hue_set_color_missing_target():
    """Test error when target is missing for set_color."""
    from strands_pack import hue

    with patch("strands_pack.hue._get_bridge"):
        with patch("strands_pack.hue._parse_color", return_value=(0.5, 0.5)):
            result = hue(action="set_color", color="red")

    assert result["success"] is False
    assert "light_id" in result["error"] or "group_id" in result["error"]


def test_hue_set_brightness_missing_value():
    """Test error when brightness value is missing."""
    from strands_pack import hue

    result = hue(action="set_brightness", light_name="Desk lamp")

    assert result["success"] is False
    assert "brightness" in result["error"] or "percent" in result["error"]


def test_hue_set_brightness_missing_target():
    """Test error when target is missing for set_brightness."""
    from strands_pack import hue

    with patch("strands_pack.hue._get_bridge"):
        result = hue(action="set_brightness", brightness=200)

    assert result["success"] is False
    assert "light_id" in result["error"] or "group_id" in result["error"]


def test_hue_turn_on_missing_target():
    """Test error when target is missing for turn_on."""
    from strands_pack import hue

    with patch("strands_pack.hue._get_bridge"):
        result = hue(action="turn_on")

    assert result["success"] is False
    assert "light_id" in result["error"] or "group_id" in result["error"]


def test_hue_turn_off_missing_target():
    """Test error when target is missing for turn_off."""
    from strands_pack import hue

    with patch("strands_pack.hue._get_bridge"):
        result = hue(action="turn_off")

    assert result["success"] is False
    assert "light_id" in result["error"] or "group_id" in result["error"]


def test_hue_blink_light_calls_bridge_alert():
    from strands_pack import hue

    mock_light = MagicMock()
    mock_light.light_id = 1
    mock_light.name = "Lamp"
    mock_light.on = True

    mock_bridge = MagicMock()
    mock_bridge.get_light_objects.return_value = {1: mock_light}

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        res = hue(action="blink", light_id=1)
    assert res["success"] is True
    mock_bridge.set_light.assert_called_once_with(1, "alert", "select")


def test_hue_toggle_light_flips_on_state():
    from strands_pack import hue

    mock_light = MagicMock()
    mock_light.light_id = 1
    mock_light.name = "Lamp"
    mock_light.on = True

    mock_bridge = MagicMock()
    mock_bridge.get_light_objects.return_value = {1: mock_light}

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        res = hue(action="toggle", light_id=1)
    assert res["success"] is True
    assert res["on"] is False
    assert mock_light.on is False


def test_hue_set_color_temp_warm_sets_ct():
    from strands_pack import hue

    mock_light = MagicMock()
    mock_light.light_id = 1
    mock_light.name = "Lamp"
    mock_light.on = False

    mock_bridge = MagicMock()
    mock_bridge.get_light_objects.return_value = {1: mock_light}

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        res = hue(action="set_color_temp", light_id=1, temp="warm")
    assert res["success"] is True
    assert res["ct"] == 500


def test_hue_create_group_calls_bridge_create_group():
    from strands_pack import hue

    mock_bridge = MagicMock()
    mock_bridge.create_group.return_value = 10

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        res = hue(action="create_group", name="Office", lights=[1, 2])
    assert res["success"] is True
    mock_bridge.create_group.assert_called_once_with("Office", [1, 2])


def test_hue_delete_group_requires_confirm_text():
    from strands_pack import hue

    mock_group = MagicMock()
    mock_group.group_id = 10
    mock_group.name = "Office"

    mock_bridge = MagicMock()
    mock_bridge.groups = [mock_group]

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        res = hue(action="delete_group", group_id=10)
        assert res["success"] is False
        assert "confirm_text" in res["error"]

        res2 = hue(action="delete_group", group_id=10, confirm_text="DELETE_GROUP 10")
        assert res2["success"] is True
        mock_bridge.delete_group.assert_called_once_with(10)


def test_hue_rename_light_sets_name():
    from strands_pack import hue

    mock_light = MagicMock()
    mock_light.light_id = 1
    mock_light.name = "Old"

    mock_bridge = MagicMock()
    mock_bridge.get_light_objects.return_value = {1: mock_light}

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        res = hue(action="rename_light", light_id=1, name="New")
    assert res["success"] is True
    assert mock_light.name == "New"


def test_hue_effect_light_calls_bridge_set_light():
    from strands_pack import hue

    mock_light = MagicMock()
    mock_light.light_id = 1
    mock_light.name = "Lamp"

    mock_bridge = MagicMock()
    mock_bridge.get_light_objects.return_value = {1: mock_light}

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        res = hue(action="effect", light_id=1, effect="colorloop")
    assert res["success"] is True
    mock_bridge.set_light.assert_called_once_with(1, "effect", "colorloop")

# Test helper functions
def test_rgb_to_xy():
    """Test RGB to XY color conversion."""
    from strands_pack.hue import _rgb_to_xy

    # Red
    xy = _rgb_to_xy(255, 0, 0)
    assert 0.6 < xy[0] < 0.8  # Red is high x
    assert 0.2 < xy[1] < 0.4  # Red is low-mid y

    # Green
    xy = _rgb_to_xy(0, 255, 0)
    assert 0.1 < xy[0] < 0.4  # Green is low x
    assert 0.5 < xy[1] < 0.9  # Green is high y

    # Blue
    xy = _rgb_to_xy(0, 0, 255)
    assert 0.1 < xy[0] < 0.2  # Blue is low x
    assert 0.0 < xy[1] < 0.2  # Blue is low y


def test_hex_to_rgb():
    """Test hex color to RGB conversion."""
    from strands_pack.hue import _hex_to_rgb

    # Full hex
    assert _hex_to_rgb("#FF0000") == (255, 0, 0)
    assert _hex_to_rgb("#00FF00") == (0, 255, 0)
    assert _hex_to_rgb("#0000FF") == (0, 0, 255)
    assert _hex_to_rgb("#FFFFFF") == (255, 255, 255)

    # Without hash
    assert _hex_to_rgb("FF0000") == (255, 0, 0)

    # Short hex
    assert _hex_to_rgb("#F00") == (255, 0, 0)


def test_parse_color_names():
    """Test parsing color names."""
    from strands_pack.hue import _parse_color

    # Named colors should return xy tuples
    xy = _parse_color("red")
    assert isinstance(xy, tuple)
    assert len(xy) == 2

    xy = _parse_color("blue")
    assert isinstance(xy, tuple)

    xy = _parse_color("GREEN")  # case insensitive
    assert isinstance(xy, tuple)


def test_parse_color_hex():
    """Test parsing hex colors."""
    from strands_pack.hue import _parse_color

    xy = _parse_color("#FF0000")
    assert isinstance(xy, tuple)
    assert len(xy) == 2


def test_parse_color_invalid():
    """Test error on invalid color."""
    from strands_pack.hue import _parse_color

    with pytest.raises(ValueError) as exc_info:
        _parse_color("notacolor")

    assert "Unknown color" in str(exc_info.value)


# Mock tests for actual functionality
def test_hue_list_lights_mocked():
    """Test list_lights with mocked bridge."""
    from strands_pack import hue

    mock_light = MagicMock()
    mock_light.light_id = 1
    mock_light.name = "Test Light"
    mock_light.on = True
    mock_light.brightness = 254
    mock_light.hue = 0
    mock_light.saturation = 254
    mock_light.xy = [0.5, 0.5]
    mock_light.colormode = "xy"
    mock_light.type = "Extended color light"
    mock_light.reachable = True

    mock_bridge = MagicMock()
    mock_bridge.lights = [mock_light]

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="list_lights")

    assert result["success"] is True
    assert result["action"] == "list_lights"
    assert result["count"] == 1
    assert result["lights"][0]["name"] == "Test Light"


def test_hue_list_groups_mocked():
    """Test list_groups with mocked bridge."""
    from strands_pack import hue

    mock_group = MagicMock()
    mock_group.group_id = 1
    mock_group.name = "Office"
    mock_group.lights = ["1", "2", "3"]
    mock_group.on = True
    mock_group.brightness = 200

    mock_bridge = MagicMock()
    mock_bridge.groups = [mock_group]

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="list_groups")

    assert result["success"] is True
    assert result["action"] == "list_groups"
    assert result["count"] == 1
    assert result["groups"][0]["name"] == "Office"


def test_hue_list_scenes_mocked():
    """Test list_scenes with mocked bridge."""
    from strands_pack import hue

    mock_scene = MagicMock()
    mock_scene.scene_id = "abc123"
    mock_scene.name = "Energize"
    mock_scene.lights = ["1", "2"]

    mock_bridge = MagicMock()
    mock_bridge.scenes = [mock_scene]

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="list_scenes")

    assert result["success"] is True
    assert result["action"] == "list_scenes"
    assert result["count"] == 1
    assert result["scenes"][0]["name"] == "Energize"


def test_hue_activate_scene_mocked():
    """Test activate_scene with mocked bridge."""
    from strands_pack import hue

    mock_bridge = MagicMock()

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="activate_scene", group_name="Office", scene_name="Energize")

    assert result["success"] is True
    assert result["action"] == "activate_scene"
    assert result["group_name"] == "Office"
    assert result["scene_name"] == "Energize"
    mock_bridge.run_scene.assert_called_once_with("Office", "Energize")


def test_hue_turn_on_light_mocked():
    """Test turn_on for a light with mocked bridge."""
    from strands_pack import hue

    mock_light = MagicMock()
    mock_light.light_id = 1
    mock_light.name = "Desk Lamp"

    mock_bridge = MagicMock()
    mock_bridge.get_light_objects.return_value = {1: mock_light}

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="turn_on", light_id=1)

    assert result["success"] is True
    assert result["action"] == "turn_on"
    assert result["target_type"] == "light"
    assert mock_light.on is True


def test_hue_turn_off_group_mocked():
    """Test turn_off for a group with mocked bridge."""
    from strands_pack import hue

    mock_group = MagicMock()
    mock_group.group_id = 1
    mock_group.name = "Office"

    mock_bridge = MagicMock()
    mock_bridge.groups = [mock_group]

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="turn_off", group_name="Office")

    assert result["success"] is True
    assert result["action"] == "turn_off"
    assert result["target_type"] == "group"
    mock_bridge.set_group.assert_called_with(1, "on", False)


def test_hue_set_color_mocked():
    """Test set_color with mocked bridge."""
    from strands_pack import hue

    mock_light = MagicMock()
    mock_light.light_id = 1
    mock_light.name = "Desk Lamp"

    mock_bridge = MagicMock()
    mock_bridge.get_light_objects.return_value = {"Desk Lamp": mock_light}

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="set_color", light_name="Desk Lamp", color="red")

    assert result["success"] is True
    assert result["action"] == "set_color"
    assert result["color"] == "red"
    assert mock_light.on is True
    assert mock_light.xy is not None


def test_hue_set_brightness_percent_mocked():
    """Test set_brightness with percentage."""
    from strands_pack import hue

    mock_light = MagicMock()
    mock_light.light_id = 1
    mock_light.name = "Desk Lamp"

    mock_bridge = MagicMock()
    mock_bridge.get_light_objects.return_value = {1: mock_light}

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="set_brightness", light_id=1, percent=50)

    assert result["success"] is True
    assert result["brightness"] == 127  # 50% of 254


# Scene management tests
def test_hue_create_scene_missing_name():
    """Test error when scene name is missing."""
    from strands_pack import hue

    result = hue(action="create_scene", group_name="Office")

    assert result["success"] is False
    assert "name" in result["error"]


def test_hue_create_scene_missing_lights():
    """Test error when lights/group is missing."""
    from strands_pack import hue

    with patch("strands_pack.hue._get_bridge"):
        result = hue(action="create_scene", name="My Scene")

    assert result["success"] is False
    assert "lights" in result["error"] or "group" in result["error"]


def test_hue_delete_scene_missing_id():
    """Test error when scene identifier is missing."""
    from strands_pack import hue

    with patch("strands_pack.hue._get_bridge"):
        result = hue(action="delete_scene")

    assert result["success"] is False
    assert "scene_id" in result["error"] or "scene_name" in result["error"]


def test_hue_update_scene_missing_id():
    """Test error when scene identifier is missing for update."""
    from strands_pack import hue

    with patch("strands_pack.hue._get_bridge"):
        result = hue(action="update_scene", name="New Name")

    assert result["success"] is False
    assert "scene_id" in result["error"] or "scene_name" in result["error"]


def test_hue_get_scene_not_found():
    """Test error when scene is not found."""
    from strands_pack import hue

    mock_bridge = MagicMock()
    mock_bridge.scenes = []

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="get_scene", scene_name="NonExistent")

    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_hue_create_scene_mocked():
    """Test create_scene with mocked bridge."""
    from strands_pack import hue

    mock_group = MagicMock()
    mock_group.group_id = 1
    mock_group.name = "Office"
    mock_group.lights = ["1", "2", "3"]

    mock_bridge = MagicMock()
    mock_bridge.groups = [mock_group]
    mock_bridge.username = "testuser"
    mock_bridge.request.return_value = [{"success": {"id": "abc123"}}]

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="create_scene", name="My Scene", group_name="Office")

    assert result["success"] is True
    assert result["action"] == "create_scene"
    assert result["scene_id"] == "abc123"
    assert result["name"] == "My Scene"
    mock_bridge.request.assert_called()


def test_hue_delete_scene_mocked():
    """Test delete_scene with mocked bridge."""
    from strands_pack import hue

    mock_scene = MagicMock()
    mock_scene.scene_id = "abc123"
    mock_scene.name = "Old Scene"

    mock_bridge = MagicMock()
    mock_bridge.scenes = [mock_scene]
    mock_bridge.username = "testuser"
    mock_bridge.request.return_value = [{"success": "/scenes/abc123 deleted"}]

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="delete_scene", scene_name="Old Scene")

    assert result["success"] is True
    assert result["action"] == "delete_scene"
    assert result["deleted"] is True


def test_hue_get_scene_mocked():
    """Test get_scene with mocked bridge."""
    from strands_pack import hue

    mock_scene = MagicMock()
    mock_scene.scene_id = "abc123"
    mock_scene.name = "Energize"
    mock_scene.lights = ["1", "2"]

    mock_bridge = MagicMock()
    mock_bridge.scenes = [mock_scene]
    mock_bridge.username = "testuser"
    mock_bridge.request.return_value = {
        "lightstates": {
            "1": {"on": True, "bri": 254},
            "2": {"on": True, "bri": 254},
        },
        "type": "GroupScene",
        "group": "1",
    }

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="get_scene", scene_name="Energize")

    assert result["success"] is True
    assert result["action"] == "get_scene"
    assert result["scene"]["name"] == "Energize"
    assert "lightstates" in result["scene"]


def test_hue_update_scene_mocked():
    """Test update_scene with mocked bridge."""
    from strands_pack import hue

    mock_scene = MagicMock()
    mock_scene.scene_id = "abc123"
    mock_scene.name = "Old Name"
    mock_scene.lights = ["1", "2"]

    mock_bridge = MagicMock()
    mock_bridge.scenes = [mock_scene]
    mock_bridge.username = "testuser"
    mock_bridge.request.return_value = [{"success": {}}]

    with patch("strands_pack.hue._get_bridge", return_value=mock_bridge):
        result = hue(action="update_scene", scene_name="Old Name", name="New Name")

    assert result["success"] is True
    assert result["action"] == "update_scene"
    assert result["changes"]["name"] == "New Name"
