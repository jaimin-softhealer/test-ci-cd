# Local Webhook CI

This repository is a small Odoo 18 demonstration for testing a self-hosted
webhook flow on macOS.

The receiver accepts signed GitHub push events for `main`, detects changed
Odoo modules, runs the standards review, and runs tests for only those modules
inside Docker. The receiver binds to localhost; Cloudflare Tunnel can expose
it temporarily for GitHub delivery testing.

Required local tools are Git, Python 3.11, Docker Desktop, `jq`, and
`cloudflared`. Keep `.env.local` outside Git and never put credentials in
source code.
