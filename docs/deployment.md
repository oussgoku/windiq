# Deploy on Google Cloud

This setup uses one Compute Engine VM for PostgreSQL, the API, the hourly
worker, and Caddy. GitHub Actions builds a commit-tagged image and can deploy
it after the VM is ready. The example project ID is `windiq`.

## 1. Create the VM with Terraform

The [`infra/`](../infra) configuration creates an Ubuntu 24.04 LTS
`e2-medium` VM in Berlin, a 20 GB boot disk, a static IPv4 address, a private
VPC, and firewall rules for HTTP, HTTPS, and SSH. No database or application
port is exposed. It also enables the Compute Engine API.

Install [Terraform](https://developer.hashicorp.com/terraform/install) and
the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install), then
authenticate locally using [Application Default Credentials](https://docs.cloud.google.com/docs/terraform/authentication):

```sh
gcloud init
gcloud auth application-default login
gcloud config set project windiq
ssh-keygen -t ed25519 -f ~/.ssh/windiq_deploy -C windiq-deploy
cd infra
cp terraform.tfvars.example terraform.tfvars
```

Replace the placeholder public key in `terraform.tfvars` with the contents of
`~/.ssh/windiq_deploy.pub`. Keep the private key out of the repository. The
example allows SSH from any IPv4 address because GitHub-hosted runners do not
have a small fixed IP range. SSH still requires your private key. If you later
use a runner with a fixed address, narrow `ssh_source_ranges` to that CIDR.

```sh
terraform init
terraform fmt -check
terraform validate
terraform plan -out=windiq.tfplan
terraform apply windiq.tfplan
terraform output external_ip
terraform output site_domain
```

Review the plan before applying it. Keep the `infra/terraform.tfstate` file:
Terraform needs it to update or destroy these resources. It is ignored by Git.
Do not manually create resources with the same names before applying this plan.

The VM, disk, and public IPv4 address consume trial credit while allocated.
Review the estimate in the console and create a billing budget alert. Delete
the VM and release the address when you finish the exercise.

Connect using the `ssh_command` Terraform output and install
[Docker Engine and the Compose plugin](https://docs.docker.com/engine/install/ubuntu/)
using Docker's Ubuntu instructions. The instance SSH user is `windiq`.
It needs permission to run `docker compose` without `sudo`; membership in the
`docker` group grants root-equivalent access, so protect its SSH key. Create
`/opt/windiq` owned by `windiq`. Log out and reconnect after adding the user
to the Docker group so the group membership takes effect.

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

Use the Ed25519 deployment key whose public half Terraform installed on the
VM. Add these repository Actions secrets
under **Settings → Secrets and variables → Actions**:

| Secret | Value |
| --- | --- |
| `DEPLOY_HOST` | VM static IPv4 address |
| `DEPLOY_USER` | `windiq` |
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
When finished, run `terraform destroy` from `infra/` with the same state file
and variable values, then confirm the VM and static IP are gone in Google Cloud.
