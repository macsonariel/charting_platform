# AWS ECS Express Mode deployment

Trading Buddy deploys as one containerized FastAPI service on Amazon ECS Express
Mode. ECS Express Mode provisions an ECS service on Fargate, an Application Load
Balancer, HTTPS, networking, auto scaling, and monitoring around the container.

AWS App Runner is closed to new customers after April 30, 2026. This repository
does not contain or support an App Runner deployment configuration.

## Deployment state

The deployment workflow is deliberately disabled by default. It runs only by
manual dispatch and only when the repository variable below is set:

```text
AWS_DEPLOYMENT_ENABLED=true
```

Do not enable it until the AWS account, IAM roles, ECR repository, billing
alerts, and GitHub environment protection are configured and reviewed.

## Architecture

```text
GitHub Actions (OIDC)
  -> build Docker image
  -> push immutable commit tag to Amazon ECR
  -> deploy image to ECS Express Mode
  -> Fargate + ALB + HTTPS + CloudWatch
```

No permanent AWS access key belongs in GitHub. GitHub obtains short-lived AWS
credentials by assuming a narrowly scoped IAM role through OpenID Connect.

## 1. AWS account and region

Enable root-account MFA, use a separate administrative identity, and create an
AWS Budget before provisioning resources. The initial target region is:

```text
Africa (Cape Town): af-south-1
```

ECS Express Mode is available in regions where ECS and Fargate are supported.

## 2. Create the ECR repository

Create a private ECR repository named `charting-platform`. Enable image scanning
and add a lifecycle policy that keeps a practical number of recent commit-tagged
images. Do not rely exclusively on a mutable `latest` tag.

## 3. Create the ECS roles

Create these roles using the trust policies and managed policies presented by
the ECS Express Mode setup flow:

- `ecsTaskExecutionRole`, with `AmazonECSTaskExecutionRolePolicy`, lets the ECS
  agent pull ECR images and publish container logs.
- `ecsInfrastructureRoleForExpressServices`, with
  `AmazonECSInfrastructureRoleforExpressGatewayServices`, lets ECS provision and
  manage the Express Mode load balancer, networking, and related resources.

The application does not currently call AWS APIs, so it does not need a task
role. Add one later only for a specific AWS dependency.

## 4. Configure GitHub OIDC

In IAM, add the GitHub Actions OIDC provider if the account does not already
have it:

```text
Provider URL: https://token.actions.githubusercontent.com
Audience:     sts.amazonaws.com
```

Create `github-actions-ecs-role` with a trust policy restricted to this
repository and production environment:

```text
repo:macsonariel/charting_platform:environment:production
```

Its permissions should be limited to pushing images to the one ECR repository,
creating or updating the intended ECS Express service, describing deployments,
and passing only the approved ECS execution and infrastructure roles. Start from
the permissions documented by the official ECS Express deployment action, then
replace wildcard resources wherever the AWS API supports tighter scoping.

## 5. Configure GitHub

Create a GitHub environment named `production`. Add protection or required
reviewers when another trusted collaborator is available.

Add these repository or environment variables:

| Variable | Initial value |
| --- | --- |
| `AWS_DEPLOYMENT_ENABLED` | `false` |
| `AWS_REGION` | `af-south-1` |
| `AWS_ACCOUNT_ID` | AWS account ID |
| `AWS_DEPLOYMENT_ROLE` | `github-actions-ecs-role` |
| `ECR_REPOSITORY` | `charting-platform` |
| `ECS_SERVICE` | `charting-platform` |
| `ECS_CLUSTER` | `default` |
| `ECS_EXECUTION_ROLE` | `ecsTaskExecutionRole` |
| `ECS_INFRASTRUCTURE_ROLE` | `ecsInfrastructureRoleForExpressServices` |

These identifiers are configuration, not credentials. Never add
`AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` to the repository.

## 6. Validate the container locally

From the repository root:

```bash
docker build --tag charting-platform:local .
docker run --rm --publish 8080:8080 charting-platform:local
```

Then verify `http://127.0.0.1:8080/api/health`. The CI workflow also builds and
health-checks the container on every push and pull request.

## 7. First deployment

After every prerequisite is complete:

1. Change `AWS_DEPLOYMENT_ENABLED` to `true`.
2. Open **Actions -> Deploy to ECS Express Mode -> Run workflow**.
3. Watch the job assume the AWS role through OIDC, build the image, push the
   commit-SHA tag to ECR, and create or update the Express Mode service.
4. Copy the endpoint from the deployment job summary or ECS console.
5. Run `python scripts/verify_deployment.py https://the-real-endpoint`.

The deployment uses port `8080`, health path `/api/health`, 1 vCPU, 2 GiB memory,
one minimum task, two maximum tasks, and CPU target tracking at 70 percent.

## 8. Production checks

Verify the dashboard, Core summary endpoint, right and bottom panels, timeframe
changes, Binance access, browser console, ALB health, and CloudWatch logs. The
health route proves process availability; the Core summary request separately
proves that the service can reach its market-data provider.

This public service currently has no authentication or rate limiting. Do not
promote it broadly until abuse controls, account storage, monitoring, and a
cost model have been designed.

## Rollback

Every image is tagged with the full Git commit SHA. To roll back, revert the bad
commit through a pull request or manually dispatch the workflow from a known-good
commit. Never force-push protected `main` and never delete ECR images still needed
for rollback.
