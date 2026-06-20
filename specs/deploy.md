# Spec: deploy — LocalStack-first AWS deployment

## Goal

Make the stack deployable and observable with LocalStack-first IaC so it costs nothing locally.

## Inputs / Outputs

- **Inputs:** Docker, docker-compose, LocalStack endpoint (`http://127.0.0.1:4566`).
- **Outputs:** Dockerfile, compose stack (service + mock_apis + LocalStack), provision script,
  smoke test, architecture doc, ADRs.

## Behaviour

1. Dockerfile builds the FastAPI service image.
2. docker-compose runs service, mock_apis, and LocalStack.
3. `deploy/provision_localstack.py` creates S3 (creatives), SQS (approvals), DynamoDB (run ledger).
4. `deploy/smoke_test.py` (via `python tasks.py deploy-local`) provisions + uploads a creative via
   S3 mock and confirms landing.
5. `docs/architecture.md` with C4-ish mermaid diagram.
6. ADRs for SQS approvals and S3 creatives choices.

## Constraints

- LocalStack endpoints by default; no real AWS credentials required.
- Smoke test degrades gracefully when Docker/LocalStack unavailable (documents skip reason).

## Failure modes

- Docker not installed → smoke test reports skip with instructions.
- LocalStack not reachable → provision fails with clear error.

## Success criteria (measurable)

- `docker-compose up` brings stack online (when Docker installed).
- Smoke test passes against LocalStack when available.
- architecture.md + ≥2 ADRs exist.

## Out of scope

- Production multi-region HA, real AWS account provisioning.
