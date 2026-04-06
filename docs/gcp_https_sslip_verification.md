# GCP HTTPS sslip.io Verification

> Status: Verified  
> Date: 2026-04-01  
> Contract: [gcp_https_sslip_contract.md](./gcp_https_sslip_contract.md)

## Target Hostname

- Hostname: `34.180.80.140.sslip.io`
- Public IP: `34.180.80.140`

## Commands Executed

- Firewall:
  - `gcloud compute firewall-rules create allow-thohago-mvp-https --project=notebooklm-485105 --network=default --direction=INGRESS --priority=1000 --action=ALLOW --rules=tcp:443 --source-ranges=0.0.0.0/0 --target-tags=thohago-mvp`
- Config update:
  - updated server env to `THOHAGO_WEB_BASE_URL=https://34.180.80.140.sslip.io`
  - updated deployed [Caddyfile](/C:/Users/User/Desktop/Thohago_branding/deployment/gcp_mvp/Caddyfile) to host `34.180.80.140.sslip.io`
- Service reload:
  - copied updated `server.env` and `Caddyfile`
  - restarted `thohago-web`
  - restarted `caddy`

## Service Verification

- `thohago-web`: `active`
- `caddy`: `active`

## HTTPS Verification

- `http://34.180.80.140.sslip.io/healthz`
  - status: `200`
  - final URL: `https://34.180.80.140.sslip.io/healthz`
  - body: `{"status":"ok"}`
- `https://34.180.80.140.sslip.io/healthz`
  - status: `200`
  - final URL: `https://34.180.80.140.sslip.io/healthz`
  - body: `{"status":"ok"}`

## Certificate Evidence

Caddy journal confirms:

- automatic TLS enabled for `34.180.80.140.sslip.io`
- ACME `http-01` challenge served successfully
- certificate obtained successfully from Let's Encrypt

## Acceptance Checklist

### A. Networking

- [x] port `443` is reachable from the internet

### B. HTTPS

- [x] `https://34.180.80.140.sslip.io/healthz` returns `200`
- [x] Caddy serves a valid HTTPS certificate for the hostname

### C. App Configuration

- [x] deployed app uses `THOHAGO_WEB_BASE_URL=https://34.180.80.140.sslip.io`

### D. Redirect Behavior

- [x] `http://34.180.80.140.sslip.io/healthz` upgrades to HTTPS

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-01
