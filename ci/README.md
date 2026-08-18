# Local Webhook CI

This repository is a small Odoo 18 demonstration for testing a self-hosted
webhook flow on macOS.

The receiver accepts signed GitHub push events for `main`, detects changed
Odoo modules, runs the standards review, and runs tests for only those modules
inside Docker. The receiver binds to localhost; Cloudflare Tunnel can expose
it temporarily for GitHub delivery testing.

When SMTP variables are configured, every completed run sends a plain-text
notification containing the commit result and CI log. `CI_EMAIL_TO` supports a
comma-separated list; when it is unset or empty, the notification uses the
pusher email from the GitHub push payload. Email failures are logged as
warnings and do not change the CI result.

For Gmail, use an App Password rather than the account password. Keep all SMTP
values in the server's environment file, never in Git.

Required local tools are Git, Python 3.11, Docker Desktop, `jq`, and
`cloudflared`. Keep `.env.local` outside Git and never put credentials in
source code.
