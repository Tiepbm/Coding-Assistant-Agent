---
name: observability-pack
description: 'Use when instrumenting code for logs, traces, and metrics: structured logging, OpenTelemetry tracing, Prometheus/OTel metrics. Code-level patterns only — defer SLO/SLI design, dashboard strategy, and alert thresholds to CE7.'
---
# Observability Pack (Implementation Patterns)

> **Scope boundary:** This pack covers *how to instrument* code, NOT how to set SLOs, design dashboards, decide alert thresholds, or pick observability vendors — those are architecture decisions → defer to CE7 Software Engineering Agent.

## When to Use
- Adding structured logging to a service (JSON, correlation IDs).
- Instrumenting code with OpenTelemetry traces (spans, attributes, propagation).
- Emitting custom metrics (counters, histograms, gauges) per stack.
- Adding correlation between logs, traces, and metrics (trace_id injection).
- Wiring exporters (OTLP, Prometheus, Jaeger).

## When NOT to Use
- Choosing SLI/SLO targets, error budgets → CE7.
- Dashboard layout, alert routing policy → CE7.
- Vendor selection (Datadog vs New Relic vs Grafana Cloud) → CE7.
- Debugging a specific live incident → `debugging-pack/production-debugging`.

## Pack Reference Map
| Reference | Use when |
|---|---|
| `structured-logging` | JSON logs, log levels, correlation IDs, sensitive-data redaction per stack. |
| `otel-tracing` | Distributed tracing setup, manual spans, context propagation, attribute conventions. |
| `metrics-instrumentation` | Counters/histograms/gauges, RED/USE method, label cardinality, Prometheus + OTel. |
| `runbook-snippets` | Authoring a one-screen operator runbook entry that ships next to a new endpoint/job/consumer. |

## Cross-Pack Handoffs
- → `debugging-pack/production-debugging` for using these signals during incidents.
- → `api-design-pack/openapi-first` for span attribute naming aligned with operationId.
- → `backend-pack/<stack>` for the production code being instrumented.
- → `devops-pack/ci-cd-pipelines` for shipping collector configs and dashboards-as-code.
- → `quality-pack/release-safety` for the rollout/SLO-gate that the runbook describes.
- → `software-engineering-agent/skills/observability-release-pack/incident-response-and-postmortem` for severity matrix + postmortem template.

