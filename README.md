# luki-modules-cognitive

> **This repository is archived.** Active development continues in a private repository with multilingual support and expanded activity generation. This public version reflects the ReMeLife integration era and is no longer maintained.

Cognitive stimulation module for LUKi. Generates personalised activity recommendations, records life stories, and supports brain training workflows using ELR data.

## What It Does

- Recommends activities from a curated catalog, scored by user interests, mood, and time of day
- Records and manages life story sessions (guided prompts across life phases)
- Generates images for photo reminiscence activities (via Together AI FLUX models)
- Tracks engagement metrics per user
- Exposes all functions as callable tools for the LUKi agent

## Stack

- **API:** FastAPI
- **Image Generation:** Together AI (FLUX models)
- **Recommendations:** Content-based scoring with heuristic ranking
- **Deployment:** Docker on Railway

## Structure

```
luki_modules_cognitive/
├── main.py                      # FastAPI app, all endpoints
├── config.py                    # Feature flags, model settings, service URLs
├── constants.py                 # Shared constants and enums
├── exceptions.py                # Custom exception hierarchy
├── startup.py                   # Service initialization
├── data/
│   ├── activity_catalog.py      # Curated activities with metadata and tags
│   ├── elr_adapter.py           # ELR data ingestion and cleaning
│   ├── life_story.py            # Life phases, prompts, story recording
│   └── world_days.py            # International observance calendar
├── recommender/
│   └── recommend.py             # Activity recommendation engine
├── analytics/
│   └── privacy_metrics.py       # Differential privacy for aggregate metrics
├── interfaces/
│   └── agent_tools.py           # Functions exposed to LUKi agent
└── utils/
    ├── validators.py            # Input validation
    └── performance_monitor.py   # Operation latency tracking
```

## Setup

```bash
git clone git@github.com:ReMeLife/luki-modules-cognitive.git
cd luki-modules-cognitive
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn luki_modules_cognitive.main:app --reload --port 8101
```

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/recommend` | Get activity recommendations for a user |
| POST | `/life-story/start` | Start a life story recording session |
| POST | `/life-story/record` | Record a life story entry |
| GET | `/life-story/{user_id}` | Get life story entries |
| POST | `/generate-image` | Generate a reminiscence image |
| GET | `/health` | Service health |

## Agent Tools

The `interfaces/agent_tools.py` module exposes functions that the core agent calls via HTTP:
- `recommend_cognitive_activity` — scored activity suggestions
- `record_mystory` — guided life story recording
- `get_mystory_prompts` — phase-appropriate prompts
- `generate_photo_reminiscence_images` — AI image generation for reminiscence

## License

Apache License 2.0. Copyright 2025 Singularities Ltd / ReMeLife. See [LICENSE](LICENSE).
