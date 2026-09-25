# AWS Cost Guidance

KubePilot uses a deliberately small AWS EKS lab, but small does not mean free. Cost and credit eligibility vary by account, region, service, date, and support tier. Exact decisions must always use current data from the AWS Billing and Cost Management console, Cost Explorer, or an equivalent account-authorized source.

## AWS Free Plan And Credits

AWS currently offers eligible new customers a Free Plan with credits and time limits. Eligibility, service access, credit expiration, and conversion to a paid plan are account-specific. Credits reduce eligible charges; they do not make every service free, remove usage limits, or replace cost monitoring.

Before relying on credits:

- Confirm the account plan and remaining credit balance in AWS Billing.
- Confirm the expiration date and which services are eligible.
- Create budget alerts before sustained lab use.
- Treat credits as temporary funding, not as a production cost model.

See the current [AWS Free Tier](https://aws.amazon.com/free/) and [Free Tier terms](https://aws.amazon.com/free/terms/) before making a spending decision.

## EKS Cost Awareness

An EKS environment can accrue several independent categories of cost:

- EKS control plane hours, including higher rates if a Kubernetes version enters extended support
- EC2 worker instance runtime
- EBS root and workload volumes
- Public IPv4 addresses
- Load balancers and processed traffic
- Cross-AZ and internet data transfer
- Container registry storage and transfer
- CloudWatch logs, metrics, and retention
- Optional managed or self-hosted observability services

AWS publishes the current components on the [Amazon EKS pricing page](https://aws.amazon.com/eks/pricing/). Do not copy a historical rate into an operational decision without checking the live regional price and account billing data.

## Current Lab Footprint

The Terraform configuration under `infrastructure/terraform/eks` defines one development cluster in `eu-west-3` with three managed `t3.small` nodes. The node group has minimum, desired, and maximum size fixed at three.

The lab uses `t3.small` because burstable general-purpose instances keep the demonstration footprint modest while supporting a small application set. The tradeoff is limited memory, scheduling headroom, and pod capacity. This shape is unsuitable as a general production recommendation and is already close to its practical pod limit.

Leaving the cluster running continuously keeps the EKS control plane, three EC2 instances, their storage, public IPv4 addresses, and any attached network resources billable. Stopping local clients or closing a terminal does not stop those charges.

## Optional Component Impact

- **Prometheus** consumes CPU, memory, and persistent storage; retention and scrape cardinality increase the footprint.
- **Grafana** adds another service and pod, even when it uses an existing Prometheus datasource.
- **OpenCost** needs compute and a metrics backend; it can improve allocation visibility but is not cost-neutral.
- **Karpenter** can improve node provisioning efficiency, but it requires controllers, IAM integration, and carefully bounded node policies. Misconfiguration can add capacity and cost quickly.

The current cluster has about two free pod slots. Prometheus, Grafana, OpenCost, and Karpenter must not be added merely to complete the demo. Evaluate them in a separate capacity and cost review.

## Safe Cost Check

The repository provides a read-only inventory helper:

```bash
bash scripts/check-costs.sh
```

Override the project defaults only when intentionally inspecting another approved KubePilot environment:

```bash
KUBEPILOT_AWS_REGION=eu-west-3 \
KUBEPILOT_CLUSTER_NAME=kubepilot-eks-dev \
bash scripts/check-costs.sh
```

Cost Explorer is optional and disabled by default. To request a project-tag-filtered query:

```bash
KUBEPILOT_QUERY_COST_EXPLORER=true bash scripts/check-costs.sh
```

The cost allocation tag must be active and Cost Explorer permissions/configuration must be available for that query to be meaningful. A missing or empty result is not proof of zero spend.

Review this sequence before decisions:

1. Verify the AWS account identity and region printed by the script.
2. Verify the exact EKS cluster and Terraform project tags.
3. Review EC2, EBS, public IP, load balancer, logging, and registry usage.
4. Check Cost Explorer and the Bills page using the same account and billing period.
5. Check remaining credits and their expiration separately.
6. Compare against current regional pricing and configured budgets.

The script performs no deletion or modification. Cleanup is a separate, explicitly confirmed Terraform workflow documented in `scripts/cleanup.sh` and must happen only after demo evidence has been captured.
