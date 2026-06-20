"""Provision LocalStack resources (S3, SQS, DynamoDB) for local deploy."""

from __future__ import annotations

import sys

from aih.config import get_settings


def provision(endpoint_url: str | None = None, region: str | None = None) -> dict[str, str]:
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        raise RuntimeError("boto3 required for deploy: pip install boto3")

    settings = get_settings()
    endpoint = endpoint_url or settings.aws_endpoint_url
    reg = region or settings.aws_region

    session = boto3.Session(region_name=reg)
    s3 = session.client("s3", endpoint_url=endpoint)
    sqs = session.client("sqs", endpoint_url=endpoint)
    ddb = session.client("dynamodb", endpoint_url=endpoint)

    bucket = settings.s3_creatives_bucket
    queue_name = settings.sqs_approvals_queue
    table_name = "aih-run-ledger"

    try:
        s3.create_bucket(Bucket=bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise

    queue_url = sqs.create_queue(QueueName=queue_name)["QueueUrl"]

    try:
        ddb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "run_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "run_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code != "ResourceInUseException":
            raise

    return {"bucket": bucket, "queue_url": queue_url, "table": table_name}


def main() -> int:
    try:
        result = provision()
        print("Provisioned:", result)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"provision failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
