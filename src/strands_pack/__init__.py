"""
strands-pack: Custom tool library for Strands Agents by LabEveryday.

A collection of consolidated tools for AI agents built on the Strands Agents framework.
Each tool uses an action parameter to select the operation to perform.
"""

# Consolidated Gemini media tool (require google-genai)
# API Gateway HTTP API tool (require boto3)
from strands_pack.apigateway_http_api import apigateway_http_api
from strands_pack.apigateway_rest_api import apigateway_rest_api

# Audio tool (require pydub + ffmpeg system binary)
from strands_pack.audio import audio

# Calendly tool (require requests)
from strands_pack.calendly import calendly

# Consolidated Carbon tool (require playwright)
from strands_pack.carbon import carbon

# ChromaDB vector database tool (require chromadb)
from strands_pack.chromadb_tool import chromadb_tool

# Code tools (no extra dependencies)
from strands_pack.code_reader import grab_code

# Consolidated Discord tool (require requests)
from strands_pack.discord import discord

# DynamoDB tool (require boto3)
from strands_pack.dynamodb import dynamodb

# EventBridge Scheduler tool (require boto3)
from strands_pack.eventbridge_scheduler import eventbridge_scheduler

# Excel tool (require openpyxl)
from strands_pack.excel import excel

# Consolidated FFmpeg tool (require ffmpeg system binary)
from strands_pack.ffmpeg import ffmpeg

# Gemini tools (require google-genai)
from strands_pack.gemini_image import gemini_image
from strands_pack.gemini_music import gemini_music
from strands_pack.gemini_video import gemini_video

# OpenAI Image tool (require openai)
from strands_pack.openai_image import openai_image

# OpenAI video tool (require openai)
from strands_pack.openai_video import openai_video

# Consolidated GitHub tool (require requests)
from strands_pack.github import github

# Google OAuth authentication tool (require google-auth-oauthlib)
from strands_pack.google_auth import google_auth

# Consolidated Gmail tool (require google-api-python-client + google-auth)
from strands_pack.gmail import gmail

# Consolidated Google Calendar tool (require google-api-python-client + google-auth)
from strands_pack.google_calendar import google_calendar

# Consolidated Google Docs tool (require google-api-python-client + google-auth)
from strands_pack.google_docs import google_docs

# Consolidated Google Drive tool (require google-api-python-client + google-auth)
from strands_pack.google_drive import google_drive

# Consolidated Google Forms tool (require google-api-python-client + google-auth)
from strands_pack.google_forms import google_forms

# Consolidated Google Sheets tool (require google-api-python-client + google-auth)
from strands_pack.google_sheets import google_sheets

# Consolidated Google Tasks tool (require google-api-python-client + google-auth)
from strands_pack.google_tasks import google_tasks

# Philips Hue Bridge tool (require phue)
from strands_pack.hue import hue

# Consolidated Image tool (require Pillow)
from strands_pack.image import image

# Lambda tool (require boto3)
from strands_pack.lambda_tool import lambda_tool

# LinkedIn tool (require requests)
from strands_pack.linkedin import linkedin

# Local dev tools (SQLite-backed)
from strands_pack.local_queue import local_queue
from strands_pack.local_scheduler import local_scheduler

# Embeddings tools
from strands_pack.local_embeddings import local_embeddings
from strands_pack.openai_embeddings import openai_embeddings

# Notifications tool (local sound + cloud backends)
from strands_pack.notify import notify

# Notion tool (require notion-client)
from strands_pack.notion import notion

# Consolidated PDF tool (require pymupdf)
from strands_pack.pdf import pdf

# Playwright browser tool (require playwright)
from strands_pack.playwright_browser import playwright_browser

# QR Code tool (require qrcode, pyzbar, Pillow)
from strands_pack.qrcode_tool import qrcode_tool

# AWS S3 tool (require boto3)
from strands_pack.s3 import s3

# AWS Secrets Manager tool (require boto3)
from strands_pack.secrets_manager import secrets_manager

# Skills loader tool (no extra dependencies, optional pyyaml)
from strands_pack.skills import skills

# Consolidated AWS SNS tool (require boto3)
from strands_pack.sns import sns

# SQLite tool (no extra dependencies - uses stdlib)
from strands_pack.sqlite import sqlite

# Consolidated AWS SQS tool (require boto3)
from strands_pack.sqs import sqs

# Managed resources inventory tool (require boto3)
from strands_pack.managed_resources import list_managed_resources

# Twilio tool (require requests)
from strands_pack.twilio_tool import twilio_tool

# Utility tools (no extra dependencies) - these remain as separate tools
from strands_pack.utilities import (
    count_lines_in_file,
    divide_numbers,
    extract_urls,
    format_timestamp,
    get_env_variable,
    load_json,
    save_json,
    validate_email,
    word_count,
)

# X (Twitter) tool (require requests)
from strands_pack.x import x

# YouTube Data API tool (require google-api-python-client + google-auth)
from strands_pack.youtube_read import youtube, youtube_read
from strands_pack.youtube_write import youtube_write

# YouTube Analytics API tool (require google-api-python-client + google-auth)
from strands_pack.youtube_analytics import youtube_analytics

# YouTube public transcript tool (requires youtube-transcript-api)
from strands_pack.youtube_transcript import youtube_transcript

__version__ = "0.1.0"

__all__ = [
    # Consolidated tools (use action parameter)
    "gemini_image",
    "gemini_video",
    "gemini_music",
    "openai_image",
    "openai_video",
    "google_auth",
    "carbon",
    "ffmpeg",
    "sns",
    "sqs",
    "notify",
    "gmail",
    "google_calendar",
    "google_forms",
    "google_drive",
    "google_sheets",
    "google_docs",
    "google_tasks",
    "discord",
    "github",
    "image",
    "pdf",
    "dynamodb",
    "eventbridge_scheduler",
    "lambda_tool",
    "apigateway_http_api",
    "apigateway_rest_api",
    "s3",
    "playwright_browser",
    "secrets_manager",
    "skills",
    "list_managed_resources",
    "youtube_read",
    "youtube_write",
    "youtube_analytics",
    "youtube_transcript",
    "notion",
    "excel",
    "audio",
    "calendly",
    "linkedin",
    "x",
    "qrcode_tool",
    "twilio_tool",
    "sqlite",
    "local_queue",
    "local_scheduler",
    "local_embeddings",
    "openai_embeddings",
    "chromadb_tool",
    "hue",
    # Code reader tool
    "grab_code",
    # Utility tools (separate functions)
    "validate_email",
    "count_lines_in_file",
    "divide_numbers",
    "save_json",
    "load_json",
    "get_env_variable",
    "format_timestamp",
    "extract_urls",
    "word_count",
]
