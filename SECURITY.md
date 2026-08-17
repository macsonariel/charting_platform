# Security policy

## Supported versions

Only the current `main` branch is supported while the project remains in active
development.

## Reporting a vulnerability

Do not open a public issue containing vulnerability details, credentials, or
personal information. Use GitHub's private vulnerability reporting feature for
this repository when available. If it is unavailable, contact the repository
owner privately through a verified channel listed on their GitHub profile.

Include the affected component, reproduction steps, potential impact, and any
suggested mitigation. Do not test against systems or accounts you do not own or
have permission to assess.

## Scope notes

The application currently has no authentication or server-side user account
model. Browser-stored settings are local to the user's device. Market data comes
from external providers and must be treated as untrusted input.
