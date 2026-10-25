# Deploy on Google Cloud

This setup uses one Compute Engine VM for PostgreSQL, the API, the hourly
worker, and Caddy. GitHub Actions builds a commit-tagged image and can deploy
it after the VM is ready. The example project ID is `windiq`.

## 1. Create the VM

In the [Google Cloud console](https://console.cloud.google.com/compute/instances?project=windiq),
select project `windiq` and create an Ubuntu 24.04 LTS VM. An `e2-medium`
instance in `europe-west10` (Berlin) is a reasonable starting size. Use a
standard persistent boot disk with at least 20 GB and reserve an external
static IPv4 address. Enable HTTP and HTTPS traffic, which opens ports 80 and
443. Keep SSH access restricted to your own IP if practical. No database or
application port needs an external firewall rule.

The VM, disk, and public IPv4 address consume trial credit while allocated.
Review the estimate in the console and create a billing budget alert. Delete
the VM and release the address when you finish the exercise.

Install [Docker Engine and the Compose plugin](https://docs.docker.com/engine/install/ubuntu/)
on the VM using Docker's Ubuntu instructions. The deployment SSH user needs
permission to run `docker compose` without `sudo`; membership in the `docker`
group grants root-equivalent access, so use a dedicated deployment account and
protect its SSH key. Create `/opt/windiq` owned by that account.

## 2. Create VM-only configuration

Create `/opt/windiq/.env` on the VM with mode `600` and these values:

```dotenv
POSTGRES_PASSWORD=<random-hex-string>
WINDIQ_API_BASE_URL=<upstream-api-url>
WINDIQ_CLIENT_ID=<upstream-client-id>
WINDIQ_CLIENT_SECRET=<upstream-client-secret>
SITE_DOMAIN=<static-ip>.sslip.io
INGEST_INTERVAL_SECONDS=3600
INGEST_STALE_AFTER_SECONDS=9000
```

Generate the database password with `openssl rand -hex 24`. The hostname
`<static-ip>.sslip.io` resolves to that IP without a DNS account; a domain you
own also works. Caddy obtains and renews HTTPS certificates once DNS, ports
80/443, and the proxy are working. Do not add a URL scheme to `SITE_DOMAIN`.
Keep `.env` on the VM and out of GitHub.

## 3. Connect GitHub Actions

Create an Ed25519 SSH key specifically for deployment. Install its public key
for the deployment account on the VM. Add these repository Actions secrets
under **Settings → Secrets and variables → Actions**:

| Secret | Value |
| --- | --- |
| `DEPLOY_HOST` | VM static IPv4 address |
| `DEPLOY_USER` | VM deployment account name |
| `DEPLOY_SSH_KEY` | Complete private key, including header and footer |
| `DEPLOY_KNOWN_HOSTS` | Verified SSH host-key line for the VM address |

Compare the VM's SSH host-key fingerprint from its console with the key you
record for `DEPLOY_KNOWN_HOSTS`; do not trust an unverified `ssh-keyscan` result.
The workflow uses its short-lived `GITHUB_TOKEN` to pull the image and removes
the temporary Docker credentials after deployment. No registry token is stored
on the VM.

Set the repository Actions **variable** `DEPLOY_ENABLED` to `true` after the
four secrets and VM configuration are ready. It is unset by default, so image
publishing continues without attempting to deploy. Run the **CI and image**
workflow from the Actions tab (or push to `main`) to release a commit.

## 4. Verify and operate

Once the deploy job succeeds, visit `https://<static-ip>.sslip.io/`. Check
`/ready` and `/health/ingestion` on that host. The ingestion endpoint can be
unhealthy until the first successful upstream pass; then check it again after
more than one hourly cycle. Check the annual energy card against
`/energy/annual` and confirm it reports coverage and exclusions.

Configure an external uptime check for `/ready` and `/health/ingestion` with
alerting to your email. The ingestion endpoint returns 503 after a failed run
or if the last success exceeds the configured freshness period. Keep the
single worker replica; two workers may run duplicate syncs. On the VM,
`docker compose --env-file .env -f compose.production.yaml ps` and
`docker compose --env-file .env -f compose.production.yaml logs scheduler`
show service status and ingestion logs.

The database lives in a Docker volume on one VM. For work beyond this short
case study, configure backups before relying on the data. Removing the VM or
its disk without a backup loses the measurements and ingestion history.
