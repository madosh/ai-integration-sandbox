"""Mock peer A2A agent — CreativeReviewAgent."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from aih.a2a.models import AgentCard, AgentSkill, Artifact, DataPart, TextPart


class ReviewRequest(BaseModel):
    creative_id: str = Field(min_length=1)
    partner: str = "creativebox"


def create_creative_review_app() -> FastAPI:
    app = FastAPI(title="CreativeReviewAgent")

    @app.get("/.well-known/agent-card.json")
    async def card() -> dict:
        return AgentCard(
            name="creative-review-agent",
            description="Reviews creatives for policy compliance before publish.",
            url="http://127.0.0.1:9100/a2a",
            skills=[
                AgentSkill(
                    id="review_creative",
                    name="review_creative",
                    description="Policy compliance check",
                )
            ],
        ).model_dump()

    @app.post("/review")
    async def review(body: ReviewRequest) -> dict:
        approved = "bad" not in body.creative_id.lower()
        artifact = Artifact(
            name="review_result",
            parts=[
                DataPart(
                    data={
                        "approved": approved,
                        "creative_id": body.creative_id,
                        "partner": body.partner,
                    }
                ),
                TextPart(
                    text="approved" if approved else "rejected: policy violation keyword detected"
                ),
            ],
        )
        return {"artifact": artifact.model_dump(), "approved": approved}

    return app


app = create_creative_review_app()
