# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.

"""Send an optional SMTP notification for a completed CI run."""

import argparse
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def parse_args():
    """Parse CI run details supplied by the shell runner."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', required=True)
    parser.add_argument('--branch', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--actor', default='')
    parser.add_argument('--author', default='')
    parser.add_argument('--result', choices=('passed', 'failed'), required=True)
    parser.add_argument('--log-file', type=Path, required=True)
    return parser.parse_args()


def main():
    """Send the CI result when SMTP configuration and recipients are present."""
    args = parse_args()
    smtp_host = os.environ.get('SMTP_HOST', '')
    recipients = [
        address.strip()
        for address in os.environ.get('CI_EMAIL_TO', args.author).split(',')
        if address.strip()
    ]
    if not smtp_host or not recipients:
        return

    sender = os.environ.get('SMTP_FROM') or os.environ.get('SMTP_USERNAME')
    if not sender:
        raise RuntimeError('SMTP_FROM or SMTP_USERNAME is required')

    log_text = args.log_file.read_text(encoding='utf-8', errors='replace')
    max_log_size = 100_000
    if len(log_text) > max_log_size:
        log_text = '[Log truncated to the last 100 KB]\n\n' + log_text[-max_log_size:]

    message = EmailMessage()
    message['From'] = sender
    message['To'] = ', '.join(recipients)
    message['Subject'] = (
        f"[Odoo CI] {args.result.upper()}: {args.repository}@{args.commit[:8]}"
    )
    message.set_content(
        f"Repository: {args.repository}\n"
        f"Branch: {args.branch}\n"
        f"Commit: {args.commit}\n"
        f"Actor: {args.actor or 'unknown'}\n"
        f"Author email: {args.author or 'unknown'}\n"
        f"Result: {args.result}\n\n"
        f"CI log:\n{log_text}"
    )

    port = int(os.environ.get('SMTP_PORT', '587'))
    username = os.environ.get('SMTP_USERNAME', '')
    password = os.environ.get('SMTP_PASSWORD', '')
    use_starttls = os.environ.get('SMTP_STARTTLS', 'true').lower() == 'true'
    with smtplib.SMTP(smtp_host, port, timeout=30) as smtp:
        smtp.ehlo()
        if use_starttls:
            smtp.starttls()
            smtp.ehlo()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)


if __name__ == '__main__':
    main()
