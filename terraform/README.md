# Terraform Location

The AWS infrastructure for this gateway lives in the platform infra repo:

```text
../terraform-platform-infra-live/modules/slack-mcp-gateway
```

It is wired into dev as an optional module:

```text
../terraform-platform-infra-live/environments/dev/main.tf
```

Enable it with:

```text
TF_VAR_enable_slack_mcp_gateway=true
```

Managed AWS resources:

- ECR repository for the gateway image.
- ECS Fargate task definition and service.
- CloudWatch log group.
- IAM execution role and task role.
- Secrets Manager secret for Slack tokens.
- Security group egress for Slack Socket Mode and analytics agent API calls.

The ECS service is created with `desired_count = 0` by default. After the
gateway image is pushed and the Slack secrets have values, the session deploy
step can roll out the task and scale the service to 1.

Slack workspace creation and Slack app installation remain manual or manifest
driven. They should not be destroyed during normal EDP session teardown.
