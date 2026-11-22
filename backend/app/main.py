import logging
import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.finder import SearchError, find_leads
from app.jobs import JobStore
from app.knowledge.generic_rules import build_generic_rules
from app.knowledge.products import PRODUCTS, get_kb
from app.pipeline.runner import STAGES, PipelineRequest, run_pipeline

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Smart Buyer AI API",
    description=(
        "Smart Buyer AI: A Knowledge Base Intelligent Potential Customer Detection System. "
        "/api/v2 is the knowledge-based pipeline; /api/search is the legacy keyword finder."
    ),
    version="0.2.0",
)
jobs = JobStore()

# Local frontend origins work by default; deployments can override these with
# a comma-separated CORS_ORIGINS environment variable.
_default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_configured_origins = os.getenv("CORS_ORIGINS", "")
_cors_origins = [
    origin.strip()
    for origin in _configured_origins.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or _default_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class SearchRequest(BaseModel):
    products: list[str] = Field(default_factory=list, max_length=10)
    custom_products: list[str] = Field(default_factory=list, max_length=10)
    country: str | None = Field(default=None, max_length=100)
    max_results_per_query: int = Field(default=5, ge=1, le=10)

    @field_validator("products", "custom_products")
    @classmethod
    def clean_product_names(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("Product names cannot be empty.")
        return cleaned

    @field_validator("country")
    @classmethod
    def clean_country(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Country cannot be empty when provided.")
        return cleaned

    @model_validator(mode="after")
    def require_products(self) -> "SearchRequest":
        if not self.products and not self.custom_products:
            raise ValueError("Provide at least one product or custom product.")
        if len(self.products) + len(self.custom_products) > 10:
            raise ValueError("Provide no more than 10 products per search.")
        return self


class ContactInfo(BaseModel):
    emails: list[str]
    phones: list[str]


class Lead(BaseModel):
    company_name: str
    website: str
    relevance_score: int
    matched_keywords: list[str]
    contact_info: ContactInfo
    source_url: str


class SearchWarning(BaseModel):
    query: str
    message: str


class SearchResponse(BaseModel):
    leads: list[Lead]
    warnings: list[SearchWarning]


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse, tags=["search"])
def search_leads(request: SearchRequest) -> SearchResponse:
    try:
        leads, warnings = find_leads(
            products=request.products,
            custom_products=request.custom_products,
            country=request.country,
            max_results_per_query=request.max_results_per_query,
        )
    except SearchError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return SearchResponse(
        leads=[Lead(**lead) for lead in leads],
        warnings=[SearchWarning(**warning) for warning in warnings],
    )


# =========================================================================
# v2 - knowledge-based pipeline (background job + polling)
# =========================================================================

ProductId = Literal["raw_sheep_wool", "duck_down", "cashmere"]


class SearchRequestV2(BaseModel):
    product: ProductId
    country: str | None = Field(default=None, max_length=100)
    max_candidates: int = Field(default=12, ge=1, le=20)
    seed_urls: list[HttpUrl] = Field(default_factory=list, max_length=20)
    mode: Literal["live", "seed", "replay"] = "live"

    @field_validator("country")
    @classmethod
    def clean_country(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def seed_mode_needs_urls(self) -> "SearchRequestV2":
        if self.mode == "seed" and not self.seed_urls:
            raise ValueError("Seed mode needs at least one seed URL.")
        return self


class JobCreated(BaseModel):
    job_id: str
    status_url: str


@app.get("/api/v2/products", tags=["v2"])
def list_products() -> list[dict]:
    return [{"id": kb.id, "name": kb.name, "definition": kb.definition} for kb in PRODUCTS.values()]


@app.post("/api/v2/search", status_code=202, response_model=JobCreated, tags=["v2"])
def start_search(request: SearchRequestV2) -> JobCreated:
    pipeline_request = PipelineRequest(
        product=request.product,
        country=request.country,
        max_candidates=request.max_candidates,
        seed_urls=[str(u) for u in request.seed_urls],
        mode=request.mode,
    )
    job_id = jobs.submit(lambda progress: run_pipeline(pipeline_request, progress),
                         describe=request.model_dump(mode="json"))
    return JobCreated(job_id=job_id, status_url=f"/api/v2/search/{job_id}")


@app.get("/api/v2/search/{job_id}", tags=["v2"])
def search_status(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown or expired search job.")
    job["stages"] = STAGES
    return job


def _describe_condition(cond) -> str:
    return cond.describe()


@app.get("/api/v2/knowledge/{product}", tags=["v2"])
def knowledge(product: ProductId) -> dict:
    kb = get_kb(product)
    rules = [*build_generic_rules(kb), *kb.rules]
    return {
        "id": kb.id, "name": kb.name, "definition": kb.definition, "aliases": kb.aliases,
        "industries": kb.industries,
        "materials": [{"id": m.id, "name": m.name, "role": m.role, "terms": m.terms} for m in kb.materials.values()],
        "activities": [{"id": a.id, "name": a.name, "tier": a.tier, "kind": a.kind} for a in kb.activities.values()],
        "applications": [{"id": a.id, "name": a.name} for a in kb.applications.values()],
        "buyer_categories": [{"id": c.id, "name": c.name, "tier": c.tier, "activities": c.activities}
                             for c in kb.buyer_categories.values()],
        "required_evidence": kb.required_evidence,
        "relations": [{"subject": s, "predicate": p, "object": o} for s, p, o in kb.relations()],
        "rules": [{
            "id": r.id, "kind": r.kind, "explain": r.explain,
            "if": [_describe_condition(c) for c in r.when],
            "then": {k: v for k, v in vars(r.effect).items() if v},
        } for r in rules],
    }


@app.get("/api/v2/snapshots", tags=["v2"])
def list_snapshots() -> list[dict]:
    """Saved live runs that can be replayed without internet (newest first)."""
    import json

    from app.pipeline.runner import SNAPSHOT_DIR

    items = []
    for path in SNAPSHOT_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("product") not in PRODUCTS:
            continue
        items.append({
            "product": data["product"],
            "product_name": PRODUCTS[data["product"]].name,
            "country": data.get("country"),
            "recorded_at": data.get("recorded_at"),
            "companies": len(data.get("companies", [])),
        })
    return sorted(items, key=lambda i: i["recorded_at"] or "", reverse=True)
