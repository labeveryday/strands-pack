# strands-pack Tool Checklist

**Total Tools:** 51
**Test Status:** 831 passed, 0 failing, 11 skipped

## Communication & Social

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| discord | `discord` | 40 pass | Yes | **Refactored** - 13 actions: send/read/edit/delete message, create channel/thread, list channels/threads/members, get/search members, add reaction, get guild info |
| gmail | `gmail` | 23 pass | Yes | Send/read, reply, drafts, labels, mark read/unread, trash - **Refactored** |
| twilio | `twilio_tool` | 13 pass | - | **Refactored** - SMS and voice calls |
| x | `x` | 13 pass | - | **Refactored** - Twitter read-only (posting requires paid API) |
| linkedin | `linkedin` | 10 pass | - | **Refactored** - Posts and profile |

## Google Workspace

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| google_auth | `google_auth` | - | Yes | OAuth authentication helper |
| google_calendar | `google_calendar` | 18 pass | Yes | **Refactored** - explicit params, reminders, hyperlinks |
| google_docs | `google_docs` | 13 pass | Yes | **Refactored** - explicit params, hyperlinks, images |
| google_drive | `google_drive` | 16 pass | Yes | **Refactored** - copy, move, rename, trash, restore, quota |
| google_forms | `google_forms` | 25 pass | Yes | **Refactored** - explicit params |
| google_sheets | `google_sheets` | 11 pass | Yes | **Refactored** - explicit params |
| google_tasks | `google_tasks` | 10 pass | Yes | **Refactored** - explicit params |

## YouTube

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| youtube_read | `youtube` | 18 pass | Yes | **Refactored** - Read-only (API key or OAuth). `youtube` is an alias. Includes `get_comments` + search filters. |
| youtube_write | `youtube_write` | 8 pass | Yes | **Refactored** - 10 actions: update_video_metadata, playlist CRUD, delete_video, set_thumbnail, set_video_privacy |
| youtube_analytics | `youtube_analytics` | 9 pass | Yes | **Refactored** - explicit params |
| youtube_transcript | `youtube_transcript` | 4 pass | Yes | **Refactored** - explicit params, v1.x API compatibility |

## AWS Services

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| s3 | `s3` | 7 pass | Yes | 13 actions: list_buckets, list_objects, head_object, download/upload_file, put/get_text, copy_object, add_lambda_trigger, delete_object, create/delete_bucket, presign_url - **Refactored** |
| dynamodb | `dynamodb` | 7 pass | Yes | 12 actions: create_jobs_table, put/get/update/delete_item, query_jobs_by_status, describe/delete_table, batch_write/get_item, scan, query - **Refactored** |
| lambda | `lambda_tool` | 8 pass | Yes | 12 actions: list/get/delete_function, list/create/update/delete_event_source_mapping, build_zip, create/update_function_zip, update_function_config, invoke - **Refactored** |
| sns | `sns` | 15 pass | Yes | 10 actions: create/delete/list_topics, get_topic_attributes, publish, subscribe, subscribe_lambda, unsubscribe, list_subscriptions, confirm_subscription - **Refactored** |
| sqs | `sqs` | 14 pass | Yes | 12 actions: create/delete/list_queues, get_queue_url, get_queue_attributes, send, send_batch, receive, delete_message, delete_message_batch, purge, change_visibility - **Refactored** |
| secrets_manager | `secrets_manager` | 6 pass | Yes | 6 actions: list_secrets, describe_secret, tag_secret, get_secret_ref, delete_secret, delete_secret_ref - **Refactored** (safe-by-default: never returns secret values) |
| eventbridge | `eventbridge_scheduler` | 6 pass | Yes | 13 actions: list/get/create/update/delete_schedule, list/create/delete_schedule_groups, pause/resume_schedule, schedule_job, create/update_lambda_schedule - **Refactored** |
| apigateway_http | `apigateway_http_api` | 5 pass | Yes | 8 actions: list_apis, create_http_api, get/delete_api, create_stage, create_jwt_authorizer, add_lambda_route/permission - **Refactored** (no API keys) |
| apigateway_rest | `apigateway_rest_api` | 2 pass | Yes | **Refactored** - 7 actions: create_rest_api, add_lambda_route, deploy_api, create_usage_plan, create_api_key, attach_api_key_to_usage_plan, create_rest_lambda_api - API keys + usage plans |
| list_managed_resources | `managed_resources` | 2 pass | Yes | Scans 8 services (lambda, dynamodb, s3, sqs, sns, apigateway_http/rest, scheduler) for resources tagged `managed-by=strands-pack` - supports additional tag filters + safety caps |

## Databases

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| sqlite | `sqlite` | 27 pass | Yes | 17 actions: execute, query, create/drop table, insert, update, delete, upsert, list/describe tables, get_info, backup, vacuum, create/drop index, truncate, export/import CSV - **Refactored** |
| local_queue | `local_queue` | 21 pass | Yes | 10 actions: init_db, send, send_batch, receive, delete, delete_batch, purge, get_queue_attributes, list_queues, change_visibility - **Refactored** (SQS-like, no AWS) |
| local_scheduler | `local_scheduler` | 22 pass | Yes | 9 actions: init_db, schedule_at, schedule_in, schedule_rate, get_schedule, list_schedules, update_schedule, cancel_schedule, run_due - **Refactored** (EventBridge-like, recurring with rate expressions) |
| local_embeddings | `local_embeddings` | 11 pass | Yes | 3 actions: embed_query, embed_texts, similarity - model caching, batch_size - **Refactored** |
| openai_embeddings | `openai_embeddings` | 10 pass | Yes | 3 actions: embed_query, embed_texts, similarity - dimensions, normalize - **Refactored** |
| chromadb | `chromadb_tool` | 17 pass | Yes | 14 actions: create/get/get_or_create/list/delete/modify collection, add, query, get, update, upsert, delete, count, peek - **Refactored** |

## Productivity

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| notion | `notion` | 11 pass | - | **Refactored** - Pages and databases |
| calendly | `calendly` | 14 pass | Yes | **Refactored** - 16 actions: user, event types, events, invitees, cancel, webhooks, scheduling links, availability (read-only) |
| excel | `excel` | 16 pass | Yes | **Refactored** - 10 actions: create, read, write, sheets, formulas, save_as |

## Media & Files

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| image | `image` | 20 pass | Yes | 14 actions: resize, crop, rotate, convert, compress, get_info, add_text, thumbnail, flip, blur, grayscale, brightness, contrast, sharpen - **Refactored** |
| pdf | `pdf` | 22 pass | Yes | 11 actions: extract_text, extract_pages, delete_pages, merge, split, get_info, to_images, rotate_pages, add_watermark, search_text, add_page_numbers - **Refactored** |
| audio | `audio` | 16 pass | Yes | Convert, trim, normalize, fade, split, overlay - **Refactored** |
| ffmpeg | `ffmpeg` | 39 pass | Yes | 14 actions: cut, concat, info, extract_audio, resize, convert, compress, add_audio, extract_frames, create_gif, thumbnail, rotate, speed, watermark - **Refactored** |
| qrcode | `qrcode_tool` | 11 pass | Yes | 8 actions: generate, generate_styled, decode, decode_all, generate_svg, generate_barcode, decode_barcode, get_info - **Refactored** |
| carbon | `carbon` | 7 pass | Yes | 3 actions: generate, generate_from_file, list_themes - **Refactored** |

## AI & Generation

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| gemini_image | `gemini_image` | 23 pass | Yes | **Refactored** - 2 actions: generate, edit - output_format, output_filename, num_images support |
| gemini_video | `gemini_video` | 35 pass | Yes | **Refactored** - Veo 3.1 - text/image to video, 1080p, talking/dialogue, commercials, action, horror |
| gemini_music | `gemini_music` | 15 pass | Yes | **Refactored** - Lyria - BPM/density/brightness controls, orchestral, lo-fi, ⚠️ no artist names |
| openai_image | `openai_image` | 27 pass | Yes | **Refactored** - 5 actions: generate, edit, analyze, optimize, variations - GPT-4o vision analysis |
| openai_video | `openai_video` | 10 pass | Yes | **Refactored** - Videos API wrapper: create/wait/download/remix/list/retrieve/delete |

## Notifications

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| notify | `notify` | 7 pass | Yes | 3 actions: notify, beep, play_file - local sound (best-effort, no cloud) |

## Developer Tools

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| github | `github` | 22 pass | Yes | **Refactored** - 21 actions: user/repo (get_user, get_repo, list_repos, search_code), issues (list_issues, get_issue, create_issue, close_issue, create_comment, set/add/remove_labels), PRs (list_prs, get_pr, create_pr, update_pr, merge_pr, list_pr_files, get_pr_diff), files (get_file_contents, create_or_update_file) |
| playwright | `playwright_browser` | 17 pass | Yes | **Refactored** - 9 actions: navigate, screenshot (.playwright-strands/), extract_text, click, fill, type, wait, evaluate, close_session + session persistence |
| grab_code | `code_reader` | 5 pass | Yes | **Refactored** - Read code with line numbers, range selection, size limits |

## Smart Home

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| hue | `hue` | 43 pass | Yes | **Refactored** - 23 actions: lights, groups, scenes, toggle, blink, color_temp, effects |

## Agent Utilities

| Tool | Module | Tests | Live Tested | Notes |
|------|--------|-------|-------------|-------|
| skills | `skills` | 21 pass | Yes | **Refactored** - 5 actions: list, load, list_scripts, read_script, read_resource. Anthropic/agentskills.io format: directory-based with Skill.md, scripts/, resources/. Dependencies reference strands-pack tools. |

## Utility Functions

| Function | Description |
|----------|-------------|
| `validate_email` | Email validation |
| `count_lines_in_file` | Line counter |
| `divide_numbers` | Safe division |
| `save_json` / `load_json` | JSON file operations |
| `get_env_variable` | Environment variable access |
| `format_timestamp` | Timestamp formatting |
| `extract_urls` | URL extraction from text |
| `word_count` | Word counting |

---

## Usage

```bash
# Run unified agent with specific tools
python examples/agent.py discord github google_forms

# List all available tools
python examples/agent.py --list

# Run with default tools
python examples/agent.py
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific tool
pytest tests/test_discord.py -v

# With coverage
pytest tests/ --cov=strands_pack
```
