# KubePilot Grafana Dashboard

`kubepilot-operations.json` is a read-only Grafana dashboard for the operational activity of KubePilot's AI SRE and FinOps workflows. It provides visibility into incoming incidents, human decisions, LLM usage, Slack callbacks, and controlled GitHub pull request execution.

## Metrics

The dashboard uses only the counters exposed by the existing KubePilot `GET /metrics` endpoint:

- `kubepilot_incidents_total`
- `kubepilot_approvals_total`
- `kubepilot_rejections_total`
- `kubepilot_prs_created_total`
- `kubepilot_github_execution_failures_total`
- `kubepilot_slack_callbacks_total`
- `kubepilot_llm_requests_total`

Prometheus must be configured to scrape the KubePilot `/metrics` endpoint. When importing the dashboard, select the Prometheus datasource that contains those scraped series.

The total panels aggregate all scraped KubePilot instances with `sum(...)`. Rate panels use `rate(...[$__rate_interval])`, allowing Grafana to select a range appropriate for the dashboard resolution and Prometheus scrape interval.

## Panels

The dashboard contains:

- Total incidents
- Total approvals
- Total rejections
- Total pull requests created
- Workflow activity rates for incidents, approvals, rejections, LLM requests, and Slack callbacks
- GitHub pull request creation and execution failure rates
- Total LLM requests
- Total Slack callbacks
- Total GitHub execution failures

The default view covers the last six hours and refreshes every 30 seconds.

## Safety And Deployment Scope

This dashboard is observability-only. Importing or viewing it does not perform Kubernetes writes, execute GitHub operations, modify AWS resources, approve remediation, or bypass KubePilot's human approval and GitOps controls.

The current EKS cluster has only about two free pod slots. Grafana, Prometheus, and other observability workloads must not be deployed to that cluster as part of this task. Use an existing external or already-provisioned observability stack when reviewing the dashboard.

## Limitations

KubePilot currently stores counters in application memory. Values reset when an application process restarts, and each replica exposes its own counter series. The dashboard sums replicas for current totals, while Prometheus handles counter resets in the rate panels. Durable lifetime totals require persistent or externally managed metrics in a future iteration.
