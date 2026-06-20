# ADR 002: S3 for creative asset storage

## Status

Accepted

## Context

CreativeBox and similar partners accept multipart uploads, but we also need an internal archive of
creatives for audit, re-push, and eval fixtures. Files are binary blobs with metadata (partner, run id,
content hash).

## Decision

Store creative binaries in **Amazon S3** (LocalStack bucket `aih-creatives` in dev):

- Connector `push_creative` uploads to partner API; service optionally mirrors to S3 for audit.
- Smoke test validates S3 landing via `deploy/smoke_test.py`.
- Bucket policies restrict write to the service role; read for dashboard preview (future).

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| EFS / NFS | Poor fit for immutable blobs; harder to expose to partners |
| DynamoDB for bytes | 400KB item limit; wrong tool for binaries |
| Partner-only storage | No internal audit trail if partner deletes asset |
| PostgreSQL BYTEA | Operational cost; backup bloat |

## Consequences

- **Positive:** Cheap, durable object storage; natural CDN path later.
- **Negative:** Not a database — metadata index still needs ledger/DynamoDB.
