# GCP MVP Deploy Contract

> Status: Active  
> Date: 2026-04-01

## Goal

Deploy the current MVP web application to a new Google Compute Engine VM in Tokyo and make it reachable from the public internet.

## Target Topology

- Project: `notebooklm-485105`
- Region: `asia-northeast1`
- Zone: `asia-northeast1-b`
- VM: `e2-small`
- Boot disk: `pd-standard`, 20GB
- OS: Ubuntu LTS
- Public entry: static external IPv4
- Reverse proxy: Caddy on port `80`
- App server: `uvicorn` on `127.0.0.1:8000`
- Process manager: `systemd`

## In Scope

1. Create a new VM for the MVP app
2. Reserve and attach a static external IP
3. Create firewall access for HTTP
4. Copy the current app code to the VM
5. Install Python runtime dependencies
6. Install and configure `uvicorn` and `caddy`
7. Install and enable a `systemd` service for the app
8. Configure runtime env vars for the deployed app
9. Verify the app responds publicly

## Out of Scope

- HTTPS certificate issuance
- domain connection
- managed instance groups
- Cloud SQL migration
- Redis
- CI/CD automation

## Runtime Assumptions

- SQLite and `runs/` remain local to the VM
- The deployed app continues to use the current file-based artifact layout
- Live STT should use Groq in production mode

## Acceptance Criteria

### A. Infrastructure

- A new `e2-small` VM exists in `asia-northeast1-b`
- A static external IP is attached to the VM
- Port `80` is reachable from the internet

### B. Application Process

- `uvicorn` is running under `systemd`
- `caddy` is running and reverse proxying to the app
- The app responds on `/healthz`

### C. Runtime Configuration

- Deployed app has non-default admin credentials
- Deployed app has a non-default sync token
- Deployed app is configured with `THOHAGO_WEB_STT_MODE=groq`
- Deployed app has `GROQ_API_KEY` configured

### D. Public Verification

- Public `GET /healthz` succeeds
- Public `GET /admin/sessions` returns an auth challenge or protected response

## Required Evidence

- exact `gcloud` commands used
- created instance name and external IP
- service status checks for `thohago-web` and `caddy`
- public HTTP verification results
- deployment verification document with pass/fail by criterion
