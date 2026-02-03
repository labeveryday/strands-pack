"""Test that all tools can be imported."""



def test_import_package():
    """Test that the main package imports."""
    import strands_pack
    assert strands_pack.__version__ == "0.1.0"


def test_import_consolidated_tools():
    """Test that all consolidated tools can be imported from the package."""
    from strands_pack import (
        apigateway_http_api,
        audio,
        calendly,
        carbon,
        chromadb_tool,
        count_lines_in_file,
        divide_numbers,
        dynamodb,
        eventbridge_scheduler,
        excel,
        extract_urls,
        ffmpeg,
        format_timestamp,
        # Gemini tools (use action parameter)
        gemini_image,
        gemini_music,
        gemini_video,
        get_env_variable,
        gmail,
        google_auth,
        google_calendar,
        google_docs,
        google_drive,
        google_forms,
        google_sheets,
        google_tasks,
        # Code reader tool
        grab_code,
        hue,
        image,
        lambda_tool,
        linkedin,
        load_json,
        local_queue,
        local_scheduler,
        local_embeddings,
        notion,
        openai_embeddings,
        pdf,
        playwright_browser,
        qrcode_tool,
        s3,
        save_json,
        secrets_manager,
        sns,
        sqs,
        sqlite,
        # Utility tools (separate functions)
        validate_email,
        twilio_tool,
        word_count,
        x,
        youtube,
        youtube_analytics,
        youtube_transcript,
    )

    # All consolidated tools should be callable
    assert callable(gemini_image)
    assert callable(gemini_video)
    assert callable(gemini_music)
    assert callable(google_auth)
    assert callable(carbon)
    assert callable(ffmpeg)
    assert callable(sns)
    assert callable(sqs)
    assert callable(s3)
    assert callable(gmail)
    assert callable(google_calendar)
    assert callable(google_forms)
    assert callable(google_drive)
    assert callable(google_sheets)
    assert callable(google_docs)
    assert callable(google_tasks)
    assert callable(youtube)
    assert callable(dynamodb)
    assert callable(eventbridge_scheduler)
    assert callable(lambda_tool)
    assert callable(apigateway_http_api)
    assert callable(playwright_browser)
    assert callable(secrets_manager)
    assert callable(notion)
    assert callable(excel)
    assert callable(audio)
    assert callable(calendly)
    assert callable(linkedin)
    assert callable(x)
    assert callable(qrcode_tool)
    assert callable(twilio_tool)
    assert callable(sqlite)
    assert callable(local_queue)
    assert callable(local_scheduler)
    assert callable(local_embeddings)
    assert callable(chromadb_tool)
    assert callable(hue)
    assert callable(image)
    assert callable(pdf)
    assert callable(openai_embeddings)
    assert callable(youtube)
    assert callable(youtube_analytics)
    assert callable(youtube_transcript)
    assert callable(grab_code)

    # Utility tools should be callable
    assert callable(validate_email)
    assert callable(count_lines_in_file)
    assert callable(divide_numbers)
    assert callable(save_json)
    assert callable(load_json)
    assert callable(get_env_variable)
    assert callable(format_timestamp)
    assert callable(extract_urls)
    assert callable(word_count)


def test_import_individual_modules():
    """Test that individual modules can be imported."""
    from strands_pack import apigateway_http_api as agw
    from strands_pack import audio as aud
    from strands_pack import calendly as cal
    from strands_pack import carbon as c
    from strands_pack import code_reader, utilities
    from strands_pack import chromadb_tool as cdb
    from strands_pack import dynamodb as ddb
    from strands_pack import eventbridge_scheduler as ebs
    from strands_pack import excel as ex
    from strands_pack import ffmpeg as f
    from strands_pack import gemini_image as gi
    from strands_pack import gemini_music as gmus
    from strands_pack import gemini_video as gvid
    from strands_pack import gmail as g
    from strands_pack import google_auth as ga
    from strands_pack import google_calendar as gc
    from strands_pack import google_docs as gdoc
    from strands_pack import google_drive as gd
    from strands_pack import google_forms as gf
    from strands_pack import google_sheets as gs
    from strands_pack import google_tasks as gt
    from strands_pack import hue as hu
    from strands_pack import image as img
    from strands_pack import lambda_tool as lt
    from strands_pack import linkedin as li
    from strands_pack import local_queue as lq
    from strands_pack import local_scheduler as ls
    from strands_pack import local_embeddings as le
    from strands_pack import notion as no
    from strands_pack import openai_embeddings as oe
    from strands_pack import pdf as pd
    from strands_pack import playwright_browser as pb
    from strands_pack import qrcode_tool as qr
    from strands_pack import s3 as s3_tool
    from strands_pack import secrets_manager as sm
    from strands_pack import sns as s
    from strands_pack import sqs as sq
    from strands_pack import sqlite as sq3
    from strands_pack import twilio_tool as tw
    from strands_pack import x as xx
    from strands_pack import youtube as yt
    from strands_pack import youtube_analytics as yta
    from strands_pack import youtube_transcript as ytt

    # Consolidated tools are directly the functions
    assert callable(gi)
    assert callable(gvid)
    assert callable(gmus)
    assert callable(ga)
    assert callable(c)
    assert callable(f)
    assert callable(s)
    assert callable(sq)
    assert callable(s3_tool)
    assert callable(g)
    assert callable(gc)
    assert callable(gf)
    assert callable(gd)
    assert callable(gs)
    assert callable(gdoc)
    assert callable(gt)
    assert callable(yt)
    assert callable(ddb)
    assert callable(ebs)
    assert callable(lt)
    assert callable(agw)
    assert callable(pb)
    assert callable(sm)
    assert callable(aud)
    assert callable(cal)
    assert callable(no)
    assert callable(ex)
    assert callable(li)
    assert callable(xx)
    assert callable(qr)
    assert callable(tw)
    assert callable(sq3)
    assert callable(lq)
    assert callable(ls)
    assert callable(le)
    assert callable(cdb)
    assert callable(hu)
    assert callable(img)
    assert callable(pd)
    assert callable(oe)
    assert callable(yt)
    assert callable(yta)
    assert callable(ytt)

    # Code reader has grab_code function
    assert hasattr(code_reader, 'grab_code')

    # Utilities has individual functions
    assert hasattr(utilities, 'validate_email')
    assert hasattr(utilities, 'word_count')
