# Security Policy

## Supported scope

This project is a local CLI/toolkit. It should not receive or store shared service credentials.

## Secrets

Never commit:

- access tokens;
- refresh tokens;
- cookies;
- auth files;
- `.env` files;
- real reference images with private people unless you intentionally publish them.

The tool redacts common token/header patterns in errors, but redaction is not a reason to log secrets.

## Data handling

Dry-run mode is local only. Live mode sends the prompt and any reference images to the configured backend. Do not use live mode with private, client, biometric, or sensitive reference images unless you have the right to do so.

## Reporting

Open a GitHub issue with a minimal reproduction. Do not paste tokens, cookies, private images, or raw auth files.
