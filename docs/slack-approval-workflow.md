# Slack human approval workflow

KubePilot can attach interactive **Approve** and **Reject** actions to an SRE
incident notification. The callback endpoint is:

```text
POST /slack/actions
```

Configure the Slack app's Interactivity request URL to this HTTPS endpoint.
KubePilot verifies the signature against the exact raw request body before it
parses the form-encoded `payload` field.

## Environment

```text
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_SIGNING_SECRET=...
KUBEPILOT_GITHUB_LIVE_AUTHORIZED=false
GITHUB_TOKEN=...
```

- `SLACK_WEBHOOK_URL` is used only for outbound notifications.
- `SLACK_SIGNING_SECRET` verifies `X-Slack-Signature` and
  `X-Slack-Request-Timestamp`. It must come from the Slack app configuration
  and must never be committed or logged.
- `KUBEPILOT_GITHUB_LIVE_AUTHORIZED` defaults to blocked. Only the exact value
  `true` enables the controlled GitHub execution path after approval.
- `GITHUB_TOKEN` is read only after a valid approval and live authorization.

## Dry-run mode

Dry-run is the default. A valid approval is recorded as `APPROVED`, the trusted
patch and Git execution request are validated, and no GitHub network write is
performed. This lets the human decision survive until an explicitly authorized
execution is requested.

## Live mode

Live mode requires both a verified human approval and
`KUBEPILOT_GITHUB_LIVE_AUTHORIZED=true`. KubePilot then uses the existing SRE
GitHub safety gateway to create one branch, one commit, and one Pull Request.
It never merges the Pull Request. GitHub failure leaves the remediation
approved and records an audit failure; it never falls back to Kubernetes.

## Approval flow

1. `/alerts` resolves the workload using the server-side target allowlist.
2. KubePilot records the trusted patch proposal and candidate under an opaque
   `remediation_id`.
3. The Slack buttons carry only that identifier.
4. `/slack/actions` verifies Slack's HMAC SHA-256 signature and five-minute
   timestamp window against the raw body.
5. The reviewer identity comes from the verified Slack `user` object.
6. Approve records the trusted candidate and runs the dry-run or authorized
   GitHub path. Reject records a final rejection and performs no GitHub action.

## Security and idempotency

Slack-supplied repository names, branches, target paths, candidate YAML, and
Kubernetes operations are ignored. Trusted remediation state is loaded by
`remediation_id` from an `ApprovalRepository`; the local/demo implementation is
thread-safe and in-memory so it can be replaced by durable storage later.

The terminal transitions are:

```text
PENDING -> APPROVED -> EXECUTED
PENDING -> REJECTED
```

Repeated identical callbacks return an idempotent success. Opposite decisions
after a final decision return a conflict. Execution is guarded atomically so a
duplicate callback cannot create a second Pull Request.

Audit entries record remediation creation, notification preparation, approval,
rejection, blocked duplicates, execution authorization, PR creation, and
execution failure. Entries contain identifiers and non-secret metadata only.

At no point does this workflow call `kubectl`, mutate the Kubernetes API, or
auto-merge a Pull Request. Delivery remains:

```text
Human approval -> GitHub PR -> Human merge -> ArgoCD -> Kubernetes
```
