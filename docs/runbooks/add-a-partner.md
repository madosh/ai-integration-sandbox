# Runbook: Add a New Partner Connector

This sandbox treats each partner as a **connector module** registered in the connector registry.
Follow these steps to add a fourth partner without touching unrelated code.

## Add-partner flow

```mermaid
flowchart LR
  M1["1 mock_apis routes"] --> M2["2 connector module"]
  M2 --> M3["3 mapping.py"]
  M3 --> M4["4 registry + auth"]
  M4 --> M5["5 corpus + RAG"]
  M5 --> M6["6 tests + health probe"]

  style M1 fill:#0c4a6e,stroke:#38bdf8,color:#e0f2fe
  style M6 fill:#166534,stroke:#4ade80,color:#dcfce7
```

## 1. Mock API (offline dev)

1. Add routes under `mock_apis/app.py` with deliberate auth + pagination quirks (interview signal).
2. Add seed data in `mock_apis/data.py`.
3. Expose `GET /healthz` on the mock app root (health probes use it).

## 2. Connector module

1. Create `src/aih/connectors/<partner>.py` extending `Connector`.
2. Implement `get_records()` (and `push_*` if publishing).
3. Normalize raw payloads to `Campaign` / `Creative` via `_normalize()`.
4. Register field mappings in `src/aih/connectors/mapping.py` for schema drift.

```python
MAPPINGS["newpartner:campaigns"] = PartnerMapping(
    partner="newpartner",
    resource="campaigns",
    fields=[FieldMapping(source="budget_cents", target="spend", transform="cents_to_dollars")],
)
```

5. Use `map_raw()` inside `_normalize()` — never scatter transform logic.

## 3. Auth + registry

1. Add auth strategy in `src/aih/connectors/auth.py` if needed (or reuse Bearer / API key / Basic).
2. Register factory in `src/aih/connectors/registry.py`:

```python
reg.register("newpartner", build_newpartner)
```

3. Add default credentials to `config.py` and `.env.example`.

## 4. Corpus + RAG

1. Add `src/aih/rag/corpus/partner-<name>.md` documenting auth, pagination, and quirks.
2. Add a retrieval eval row in `src/aih/evals/datasets/retrieval.jsonl`.

## 5. Skills / agent

- Read-only sync works automatically via `sync_campaign_data` and `sync_all_connectors`.
- Add a publish skill only if the partner supports writes.

## 6. Tests

1. Pagination test in `tests/connectors/`.
2. Health probe: `check_connector_health("newpartner", httpx_transport=ASGITransport(mock_app))`.
3. Optional webhook test if the partner pushes async events to `POST /webhooks/{partner}`.

## 7. Verify

```powershell
python tasks.py test
python tasks.py eval
python tasks.py mock-apis   # :9000
python tasks.py run         # :8000 — GET /connectors/newpartner/health
```

## Interview talking points

- **Transport layer** owns retries, `Retry-After`, circuit breaker — connectors stay thin.
- **Mapping registry** documents schema drift; versioning mappings beats one-off `if partner` blocks.
- **Health endpoint** surfaces circuit state + upstream probe for ops dashboards.
- **Webhooks** complement polling for async partner callbacks.
