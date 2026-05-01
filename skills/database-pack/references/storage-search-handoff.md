---
name: storage-search-handoff
description: 'Use when implementing object/file storage (S3/GCS/Azure Blob), signed URLs, retention, or search/index integration (OpenSearch/Elasticsearch/Algolia). Routes the design (retention policy, projection model, reindex strategy, source-of-truth boundary) to CE7 and keeps only the SDK wiring here.'
---
# Storage / Search Handoff (Shim Reference)

This is a **routing shim**. The Coding Assistant wires the SDKs; **CE7** owns the storage and search architecture.

## Two scopes — pick the right one

| Scope | Owner |
|---|---|
| Writing S3 upload code, generating signed URLs, calling OpenSearch SDK, writing index mappings | **Coding Assistant** → `database-pack` + `devops-pack/aws-services` (for S3) |
| Choosing object lifecycle (retention, legal hold, scan-on-upload), designing the search projection (which fields, authz model, reindex strategy) | **CE7** → `storage-search-pack/file-and-object-storage` + `storage-search-pack/search-and-indexing` |

## The 4 always-on Coding Assistant rules

Apply whenever code touches object storage or search:

1. **Object metadata lives outside the object** — never in the binary. Index/database row carries `tenant_id`, `owner_id`, `created_at`, `content_hash`, `scan_status`, `retention_class`.
2. **Signed URL with scoped authz** — short TTL (≤ 15 min), method-restricted (`GET`-only for read), object-key prefixed by `tenant_id`, NOT just object UUID.
3. **Search index is NEVER source of truth** — every list/search endpoint reads index for filter/sort + fetches authoritative fields from primary store; rejects rows where authz fails (post-filter).
4. **Reindex is a deployable artifact** — code paths that build index documents must be runnable as a one-shot CLI/job (for backfill / index version bump).

## When to escalate to CE7

| Signal | Escalate to |
|---|---|
| "How long do we keep these documents?" / "Legal hold?" | `storage-search-pack/file-and-object-storage` |
| "Should we use Elasticsearch / OpenSearch / Algolia / Postgres FTS?" | `storage-search-pack/search-and-indexing` + `data-database-analytics-pack/database-architecture` |
| "Reindex strategy for schema change" (zero-downtime, alias swap) | `storage-search-pack/search-and-indexing` |
| "Document-level vs field-level authz in the index" | `storage-search-pack/search-and-indexing` + `security-access-pack/security-review` |
| "Should we scan on upload? virus / PII detection?" | `storage-search-pack/file-and-object-storage` + `security-access-pack/security-review` |

## Cross-Pack Handoffs
- File / object storage design → CE7 `storage-search-pack/file-and-object-storage`.
- Search / indexing design → CE7 `storage-search-pack/search-and-indexing`.
- S3/GCS/Azure SDK implementation → `devops-pack/aws-services` (or equivalent) + `backend-pack/<stack>`.
- Signed-URL endpoint authz → `quality-pack/security-handoff` + `quality-pack/security-coding`.

