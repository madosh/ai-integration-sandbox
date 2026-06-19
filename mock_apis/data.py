"""Deterministic seed fixtures for the mock partner APIs.

Each partner exposes campaign records in its OWN shape (different field names and
status vocabularies) so the connector normalization layer has to earn its keep.
"""

from __future__ import annotations

from typing import Any

# PulseAds: cursor-paginated, "label"/"state"/"spend_cents"/"clicks".
PULSEADS_CAMPAIGNS: list[dict[str, Any]] = [
    {
        "campaign_id": "pa-1",
        "label": "Summer Sale",
        "state": "running",
        "spend_cents": 125_00,
        "clicks": 220,
    },
    {
        "campaign_id": "pa-2",
        "label": "Back to School",
        "state": "paused",
        "spend_cents": 64_50,
        "clicks": 88,
    },
    {
        "campaign_id": "pa-3",
        "label": "Holiday Push",
        "state": "running",
        "spend_cents": 980_00,
        "clicks": 1500,
    },
    {
        "campaign_id": "pa-4",
        "label": "Clearance",
        "state": "stopped",
        "spend_cents": 12_00,
        "clicks": 14,
    },
    {
        "campaign_id": "pa-5",
        "label": "Flash Deal",
        "state": "running",
        "spend_cents": 305_75,
        "clicks": 640,
    },
]

# NovaReach: offset/limit-paginated, "title"/"status"/"budget"/"impressions".
NOVAREACH_CAMPAIGNS: list[dict[str, Any]] = [
    {
        "id": "nr-1",
        "title": "Brand Awareness",
        "status": "active",
        "budget": 500.0,
        "impressions": 10_000,
    },
    {
        "id": "nr-2",
        "title": "Retargeting Q3",
        "status": "active",
        "budget": 750.0,
        "impressions": 22_400,
    },
    {
        "id": "nr-3",
        "title": "App Installs",
        "status": "paused",
        "budget": 300.0,
        "impressions": 5_300,
    },
    {
        "id": "nr-4",
        "title": "Lookalike Test",
        "status": "archived",
        "budget": 120.0,
        "impressions": 1_200,
    },
]
