# Flashcards — 30 rapid Q&A

1. **Q:** BM25 vs dense retrieval? **A:** BM25 = sparse lexical + IDF; dense = semantic embeddings; hybrid wins on mixed queries.
2. **Q:** When does BM25 beat dense? **A:** Exact tokens, rare IDs, error codes, partner-specific jargon.
3. **Q:** When does dense beat BM25? **A:** Paraphrases, semantic similarity without shared tokens.
4. **Q:** RRF vs alpha fusion? **A:** RRF rank-based, no score calibration; alpha needs comparable score scales.
5. **Q:** Typical RRF k? **A:** 60 (smooths tail ranks).
6. **Q:** What is MCP? **A:** Model Context Protocol — stdio/HTTP bridge exposing typed tools to LLM clients.
7. **Q:** Function-calling vs ReAct? **A:** FC = structured tool schema invocation; ReAct = text thought/action loops — FC easier to eval.
8. **Q:** recall@k? **A:** Fraction of relevant docs found in top k.
9. **Q:** MRR? **A:** Mean of 1/rank of first relevant hit.
10. **Q:** nDCG@k? **A:** Discounted cumulative gain vs ideal ranking.
11. **Q:** Idempotency key purpose? **A:** Safe retries without duplicate side effects.
12. **Q:** Exponential backoff? **A:** delay = base × 2^attempt; spreads retry load.
13. **Q:** Why jitter? **A:** Prevents synchronized retry storms.
14. **Q:** Retry-After header? **A:** Server hint for 429; client should wait at least that long.
15. **Q:** Circuit breaker states? **A:** Closed (normal), open (fail fast), half-open (probe).
16. **Q:** HITL when? **A:** Side effects, low reversibility, policy-sensitive actions.
17. **Q:** Spec-driven development? **A:** Write spec (goal, I/O, constraints) before code; reference in commits.
18. **Q:** AI Skill vs MCP tool? **A:** Skill = app capability with schemas; MCP tool exposes capabilities to external LLM clients.
19. **Q:** FakeLLM in tests? **A:** Deterministic keyword/regex planner for offline agent evals.
20. **Q:** HashEmbedder? **A:** Deterministic hashing embedder for offline dense retrieval tests.
21. **Q:** Cursor vs offset pagination? **A:** Cursor stable under inserts; offset simple but can skip/duplicate on churn.
22. **Q:** S3 for creatives? **A:** Immutable blobs, cheap storage, audit archive (see ADR 002).
23. **Q:** SQS for approvals? **A:** Durable async approval queue, DLQ for stuck items (ADR 001).
24. **Q:** DynamoDB for run ledger? **A:** Key-value by run_id, scales with serverless workers.
25. **Q:** LocalStack? **A:** Local AWS API emulation for S3/SQS/DynamoDB without cloud cost.
26. **Q:** SSE use case? **A:** Push run trace updates to dashboard without polling.
27. **Q:** ASGI transport in tests? **A:** In-process httpx against FastAPI app — no network.
28. **Q:** Tool-selection eval? **A:** Compare planner pick vs expected skill on golden goals.
29. **Q:** LLM-as-judge risks? **A:** Biased, non-deterministic — calibrate with human labels.
30. **Q:** Challenge-back skill? **A:** Question assumptions, cite trade-offs, propose safer alternative.
31. **Q:** Working vs semantic memory? **A:** Working = ephemeral context assembly; semantic = durable facts with keys.
32. **Q:** Episodic vs procedural? **A:** Episodic = what happened; procedural = how to do it (skills + heuristics).
33. **Q:** Parametric memory? **A:** Model weights — boundary, not built; externalize auditable facts.
34. **Q:** A2A Agent Card? **A:** Discovery doc: identity, endpoint, skills, auth at well-known path.
35. **Q:** A2A task states? **A:** submitted → working → input-required → completed | failed | canceled.
36. **Q:** AG-UI event categories? **A:** Lifecycle, Text, ToolCall, State, Special (RAW/CUSTOM/INPUT_REQUEST).
37. **Q:** AG-UI vs A2UI? **A:** AG-UI = transport/events; A2UI = declarative component payloads on stream.
38. **Q:** Push vs SSE? **A:** SSE = live stream to connected client; webhook push for offline/long tasks.
39. **Q:** HITL as input-required? **A:** Same gate: A2A pauses task; AG-UI emits INPUT_REQUEST.
40. **Q:** Opaque-agent principle? **A:** Peer agents untrusted; sanitize artifacts; no prompt injection.
41. **Q:** RRF carryover to memory? **A:** Same fusion mindset — merge ranked memory sources under budget.
42. **Q:** FastAPI role in this repo? **A:** Composition root: async routes, SSE, AppState wiring agent+RAG+protocols.
