"""LocalStack smoke test: provision + upload creative to S3 mock."""

from __future__ import annotations

import sys
import urllib.error
import urllib.request

from aih.config import get_settings


def _localstack_reachable(endpoint: str) -> bool:
    try:
        with urllib.request.urlopen(f"{endpoint}/_localstack/health", timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def smoke_test() -> int:
    settings = get_settings()
    endpoint = settings.aws_endpoint_url or "http://127.0.0.1:4566"

    if not _localstack_reachable(endpoint):
        print(
            "SKIP: LocalStack not reachable at",
            endpoint,
            "\nInstall Docker Desktop and run: docker compose up -d localstack",
        )
        return 0  # graceful skip per plan when Docker unavailable

    try:
        import boto3
    except ImportError:
        print("SKIP: boto3 not installed (pip install boto3)")
        return 0

    from deploy.provision_localstack import provision
    print("Provisioning LocalStack resources...")
    resources = provision(endpoint_url=endpoint)
    bucket = resources["bucket"]
    key = "smoke/creative.bin"
    body = b"smoke-test-creative-bytes"

    s3 = boto3.client("s3", endpoint_url=endpoint, region_name=settings.aws_region)
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/octet-stream")

    head = s3.head_object(Bucket=bucket, Key=key)
    size = head["ContentLength"]
    if size != len(body):
        print(f"FAIL: object size {size} != {len(body)}")
        return 1

    print(f"OK: uploaded s3://{bucket}/{key} ({size} bytes)")
    return 0


def main() -> int:
    try:
        return smoke_test()
    except Exception as exc:  # noqa: BLE001
        print(f"smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
