# Odoo Automation Testing: Team Guide

## What This Does

When a developer pushes code to the configured branch, GitHub sends a message
to our webhook server. The server checks out that exact commit, finds the Odoo
modules changed in that commit, and runs those modules' automated tests in an
isolated Docker database.

The result is visible in three places:

- The live server terminal logs.
- The GitHub commit status.
- An email to the GitHub user who pushed the code.

This flow is for functional automation testing only. It does not perform a
general coding-standards review.

## Normal Developer Flow

1. Work in the normal development checkout.
2. Add or update Odoo tests in the module's `tests/` directory.
3. Run the tests locally when possible.
4. Commit and push to the configured branch, for example `main`.
5. The webhook starts the test automatically.
6. Open the commit in GitHub and check the CI status.
7. If the test fails, read the failure email and the server log.

The CI checkout is separate from the developer checkout. Developers should
not edit files inside the CI checkout while a test is running.

## What Gets Tested

Only modules changed by the pushed commit are selected. For example:

- A change inside `sh_sales/` selects `sh_sales`.
- A change inside `sh_sales/models/` also selects `sh_sales`.
- A change to documentation only selects no module and runs no Odoo module test.
- If three modules changed, all three modules are tested independently.

Each selected module is installed or upgraded in a separate test database and
its tagged Odoo tests run with `--test-enable`.

## Understanding Results

**Passed:** The selected module tests completed successfully. The GitHub
commit receives a successful status and the configured SMTP sender sends a
success email.

**Failed:** At least one selected module test failed, or the test environment
could not complete. The GitHub commit receives a failure status and the email
contains the commit details and the CI log.

**Skipped/no module:** The commit did not change an Odoo module. The webhook
still records the commit, but there is no module test to run.

## Live Logs

Connect to the server over SSH and use two terminals:

```bash
sudo journalctl -u test-ci-cd-webhook -f
```

```bash
tail -F /opt/ci/test-ci-cd-ci/logs/*.log
```

The log normally shows the commit SHA, changed files, selected modules, test
names, failures, and the final result.

## Email Behavior

The email is sent after the test finishes. It includes:

- Repository and branch.
- Commit SHA.
- GitHub actor and pusher email.
- Passed or failed result.
- The CI log, truncated only if it is extremely large.

Leave `CI_EMAIL_TO` empty when the email should go to the pusher. Use a fixed
recipient list only when the project requires a shared mailbox. Gmail requires
an App Password, not the normal account password.

## Intentional Failure Test

To verify the failure path, a temporary test can intentionally assert the
wrong result. Push it, watch the logs, confirm the failure email, and then
remove the temporary test immediately. Do not leave an intentional failure in
the production branch.

## Important Rule

The test database is disposable. The CI process must never run against a live
customer database or restart the production Odoo service.
