"""Tests for YouTube transcript tool (offline/mocked)."""



def test_youtube_transcript_unknown_action():
    from strands_pack import youtube_transcript

    result = youtube_transcript(action="nope")
    assert result["success"] is False
    assert "available_actions" in result


def test_youtube_transcript_requires_video_id():
    from strands_pack import youtube_transcript

    result = youtube_transcript(action="get_transcript", video_id="")
    assert result["success"] is False
    # May fail due to missing deps or missing video_id
    assert "video_id" in result["error"].lower() or "youtube" in result["error"].lower()


def test_youtube_transcript_missing_video_id():
    from strands_pack import youtube_transcript

    result = youtube_transcript(action="get_transcript")
    assert result["success"] is False


def test_youtube_transcript_invalid_format():
    from strands_pack import youtube_transcript

    # Should either fail due to missing dep or invalid format
    result = youtube_transcript(action="get_transcript", video_id="VID", output_format="invalid_format")
    assert result["success"] is False


