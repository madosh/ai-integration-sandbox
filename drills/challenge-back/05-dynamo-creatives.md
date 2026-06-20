# Challenge-back drill 5

**Stakeholder:** "Store creatives in DynamoDB — we already use it."

<details>
<summary>Counter-argument + alternative</summary>

DynamoDB item size limit and cost for binaries; wrong access pattern. **Alternative:** S3 for blobs,
DynamoDB/SQLite for metadata index and run ledger (see ADR 002).

</details>
