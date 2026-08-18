# Odoo Automation Testing: Technical Setup

## Architecture

```text
Developer push
      |
      v
GitHub repository webhook
      |
      v
HTTPS reverse proxy or tunnel
      |
      v
Python webhook server
      |
      v
ci/run_ci.sh
      |
      +--> fetch exact commit
      +--> detect changed Odoo modules
      +--> run each module in Docker
      +--> post GitHub status
      +--> send SMTP result email
```

The production Odoo services and production databases are not part of this
flow. The test runner uses its own checkout, Docker network, PostgreSQL
container, and test databases.

## Required Components

- Git with SSH access to the private repository.
- Python 3.11 or a compatible Python 3 runtime.
- Docker Engine or Docker Desktop.
- `jq` for JSON processing.
- A reachable HTTPS webhook URL.
- PostgreSQL running in the isolated CI Docker network.
- An Odoo CI image containing the required Odoo source and Python runtime.

## Repository Layout

```text
test-ci-cd/
├── ci/
│   ├── run_ci.sh
│   ├── send_ci_email.py
│   └── webhook_server.py
├── docs/
├── sh_ci_demo/
│   ├── __manifest__.py
│   └── tests/
└── .env.example
```

`ci/run_ci.sh` is the test runner. `ci/webhook_server.py` validates GitHub's
signature and queues the runner. `ci/send_ci_email.py` sends the final result
through SMTP.

## Separate CI Checkout

Do not use the developer checkout as the CI checkout. Create a second checkout:

```bash
git clone --branch main --single-branch \
  git@github.com:OWNER/REPOSITORY.git \
  /opt/ci/test-ci-cd-ci
```

The CI service must own the checkout:

```bash
sudo chown -R ci-runner:ci-runner /opt/ci/test-ci-cd-ci
```

The runner fetches the pushed SHA and checks it out detached. This guarantees
that the tests run against the commit that triggered the webhook.

## Environment Configuration

Create `/etc/test-ci-cd.env` on the server. Keep this file outside Git and
restrict its permissions:

```env
WEBHOOK_SECRET=use-the-same-random-value-configured-in-github
GITHUB_TOKEN=

CI_REPO_SLUG=jaimin-softhealer/test-ci-cd
CI_REPO_DIR=/opt/ci/test-ci-cd-ci
CI_RUNNER=/opt/ci/test-ci-cd-ci/ci/run_ci.sh
CI_BRANCH=main

CI_DOCKER_NETWORK=test-ci-cd-ci
CI_DB_HOST=test-ci-cd-postgres
CI_DB_PORT=5432
POSTGRES_USER=odoo
POSTGRES_PASSWORD=isolated-test-database-password
POSTGRES_DB=odoo_test
ODOO_CI_IMAGE=test-ci-cd/odoo-ci:18.0-py3.11
ODOO_SRC=/opt/odoo
WEBHOOK_PORT=8091

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=ci-sender@example.com
SMTP_PASSWORD=gmail-app-password
SMTP_FROM=ci-sender@example.com
SMTP_STARTTLS=true
CI_EMAIL_TO=
```

`CI_EMAIL_TO=` is intentionally empty when the pusher should receive the
message. If it contains comma-separated addresses, those addresses are used
instead. `GITHUB_TOKEN` is optional and is only needed if the runner should
post commit statuses through the GitHub API.

Apply secure permissions:

```bash
sudo chmod 600 /etc/test-ci-cd.env
```

## PostgreSQL and Docker Isolation

Create a dedicated Docker network and PostgreSQL container. Names can be
changed, but they must match the environment file:

```bash
docker network create test-ci-cd-ci

docker run -d \
  --name test-ci-cd-postgres \
  --network test-ci-cd-ci \
  -e POSTGRES_USER=odoo \
  -e POSTGRES_PASSWORD='isolated-test-database-password' \
  -e POSTGRES_DB=odoo_test \
  postgres:17
```

The test runner connects to `test-ci-cd-postgres` by Docker DNS. Do not point
`CI_DB_HOST` at a production PostgreSQL service.

## Webhook Service

Create `/etc/systemd/system/test-ci-cd-webhook.service`:

```ini
[Unit]
Description=test-ci-cd GitHub webhook receiver
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=ci-runner
Group=ci-runner
EnvironmentFile=/etc/test-ci-cd.env
WorkingDirectory=/opt/ci/test-ci-cd-ci
ExecStart=/usr/bin/python3 /opt/ci/test-ci-cd-ci/ci/webhook_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and check it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now test-ci-cd-webhook
sudo systemctl status test-ci-cd-webhook --no-pager
curl http://127.0.0.1:8091/health
```

Expected health response:

```text
ok
```

## HTTPS Reverse Proxy

Inside the existing HTTPS server block for the project domain, add a route
that forwards to the local webhook port:

```nginx
location = /ci-webhook {
    proxy_pass http://127.0.0.1:8091/github/webhook;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Validate and reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

An unsigned request should be rejected. That is expected and proves the route
reaches the webhook service:

```bash
curl -i -X POST https://ci.example.com/ci-webhook -d '{}'
```

Expected response:

```text
403 invalid signature
```

## GitHub Webhook Configuration

In the repository, open **Settings -> Webhooks -> Add webhook** and use:

- Payload URL: `https://ci.example.com/ci-webhook`
- Content type: `application/json`
- Secret: exactly the value of `WEBHOOK_SECRET`
- Events: **Just the push event**
- Active: enabled

The webhook accepts only signed `push` events for the configured branch. A
delivery response of `202` with `CI queued` means the server accepted it.

## Test Execution Details

For every push, the runner:

1. Creates a per-commit log file.
2. Posts a pending GitHub status when `GITHUB_TOKEN` is configured.
3. Fetches the branch and checks out the exact `after` SHA.
4. Calculates changed files using the `before` and `after` SHAs.
5. Finds the nearest parent directory containing `__manifest__.py`.
6. Deduplicates selected module names and addon paths.
7. Creates a database named `<POSTGRES_DB>_<module_name>`.
8. Installs the module with `--test-enable` and runs `--test-tags=/<module>`.
9. Stops Odoo after the test run.
10. Posts success or failure and sends the SMTP email.

The command executed for a selected module is equivalent to:

```bash
python /opt/odoo/odoo-bin \
  -d odoo_test_sh_ci_demo \
  -i sh_ci_demo \
  --test-enable \
  --test-tags=/sh_ci_demo \
  --stop-after-init \
  --without-demo=True
```

## Logs and Troubleshooting

Live webhook service logs:

```bash
sudo journalctl -u test-ci-cd-webhook -f
```

Live CI logs:

```bash
tail -F /opt/ci/test-ci-cd-ci/logs/*.log
```

Useful checks:

```bash
sudo systemctl status test-ci-cd-webhook --no-pager
curl http://127.0.0.1:8091/health
docker ps
docker network inspect test-ci-cd-ci
ls -lh /opt/ci/test-ci-cd-ci/logs
```

Common failures:

| Symptom | Check |
|---|---|
| GitHub cannot deliver | HTTPS URL, DNS, Nginx route, firewall, and webhook delivery details |
| `invalid signature` | GitHub secret and `WEBHOOK_SECRET` are not identical |
| No module selected | The pushed files are outside a directory containing `__manifest__.py` |
| Git authentication failure | The `ci-runner` SSH key has repository read access |
| Docker database connection failure | Network name, container name, credentials, and container health |
| Email not sent | SMTP variables, App Password, sender address, and server logs |
| Another CI run is active | Check for a stale `logs/ci.lock` only after confirming no run is active |

## Safe Verification

Use a small test-only commit to verify the failure path. Confirm all of the
following:

- The webhook delivery returns `202`.
- The selected module appears in the CI log.
- The failing test appears with its traceback.
- The GitHub commit receives a failure status.
- The pusher receives the failure email.

Remove the intentional failure immediately after verification and push a
cleanup commit. Never use a production database for this test.
