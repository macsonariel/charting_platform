# AWS App Runner deployment

Trading Buddy deploys as one App Runner web service. FastAPI serves the browser
assets, JSON endpoints, and Core Engine from the same release and origin.

This guide prepares a deployment; it does not create AWS resources.

## Prerequisites

- An AWS account with billing alerts and MFA enabled
- This repository pushed to a private GitHub or Bitbucket repository
- An AWS Region appropriate for the intended users and Binance availability
- No secrets, `.env` files, virtual environments, or local datasets committed

## Create the service

1. Open AWS App Runner and choose **Create service**.
2. Select **Source code repository**, connect the repository provider, and select
   the production branch.
3. Set the source directory to the repository root.
4. Choose **Use a configuration file**. App Runner will read `apprunner.yaml`.
5. Use an HTTP health check with path `/api/health`.
6. Leave outbound networking on the App Runner-managed public network. The Core
   Engine requires outbound HTTPS access to the configured market-data provider.
7. Deploy and wait for the service status to become **Running**.

The configuration runs Python 3.11 on port 8080, installs `requirements.txt`,
and starts `backend.main:app`. `APP_ENV=production` disables development CORS
origins. The checked-in frontend is same-origin and does not require CORS.

If a separate frontend is introduced later, set `ALLOWED_ORIGINS` to a
comma-separated list of exact HTTPS origins, for example:

```text
https://app.example.com,https://admin.example.com
```

Do not use `*` for a credentialed production application.

## Verify the deployment

Run the verifier from the repository root, replacing the URL with the App Runner
default domain or custom domain:

```bash
python scripts/verify_deployment.py https://example.region.awsapprunner.com
```

This checks `/api/health` and then requests `/api/core/summary`. Both must pass.
The Core request verifies that the runtime can reach Binance and execute the
analysis pipeline; a healthy process alone does not prove that.

Also open the root URL and verify the chart, right analysis panel, bottom panel,
timeframe changes, and browser console.

## Domain, HTTPS, and operations

The App Runner default domain includes HTTPS. A custom domain can be associated
from the App Runner service page; Route 53 can automate the required validation
records. Set log retention and alarms in CloudWatch rather than keeping the
defaults indefinitely.

Recommended alarms include elevated 5xx responses, latency, CPU or memory
pressure, and failed deployments. Review CloudWatch application logs for market
provider failures.

## Production limitations

- Profiles and preferences are browser-local and are not shared between devices.
- Drawings currently have no AWS persistence model.
- There is no authentication or authorization layer.
- Core snapshot and market-data caches are process-local. Multiple scaled
  instances can calculate the same analysis independently.
- Binance availability, regional rules, terms, and rate limits must be validated
  for the intended production use.

Do not add a VPC connector merely for isolation: App Runner VPC-connected egress
needs a correctly routed NAT gateway to reach public market-data APIs. Add private
networking only when the application gains private AWS dependencies and its cost
and routing model have been designed.

## Rollback

Keep automatic deployment off for the first release. After verification, enable
it only for a protected production branch. If a release fails, redeploy a known
good source revision from App Runner and rerun `scripts/verify_deployment.py`.
