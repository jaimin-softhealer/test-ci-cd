# test-ci-cd

Small Odoo 18 module and local webhook CI demonstration.

## Demo module

`sh_ci_demo` contains a task model and transaction tests. A push that changes
the module causes the local runner to install it in a fresh test database and
execute its tagged tests.

## Local setup

Install `git`, Python 3.11, Docker Desktop, `jq`, and `cloudflared`. Create a
`.env.local` file from the variables described in `ci/README.md`, then run:

```bash
set -a
source .env.local
set +a
python3 ci/webhook_server.py
```

Use a second checkout for `CI_REPO_DIR` (for example,
`/Users/jaimindhamecha/Documents/test-ci-cd-ci`). The runner checks out exact
commits in detached HEAD, so it must not use the working copy used to create
and push commits.

The health endpoint is `http://127.0.0.1:8080/health`. For a real GitHub push,
run `cloudflared tunnel --url http://127.0.0.1:8080` and configure the
generated HTTPS URL with `/github/webhook` as the repository webhook.
