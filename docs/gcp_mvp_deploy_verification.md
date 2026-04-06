# GCP MVP Deploy Verification

> Status: Verified  
> Date: 2026-04-01  
> Contract: [gcp_mvp_deploy_contract.md](./gcp_mvp_deploy_contract.md)

## Verification Environment

- GCP project: `notebooklm-485105`
- Region: `asia-northeast1`
- Zone: `asia-northeast1-b`
- Instance: `thohago-mvp-tokyo`
- Public base URL: `http://34.180.80.140`

## Infrastructure Creation

### Commands executed

- Firewall:
  - `gcloud compute firewall-rules create allow-thohago-mvp-http --project=notebooklm-485105 --network=default --direction=INGRESS --priority=1000 --action=ALLOW --rules=tcp:80 --source-ranges=0.0.0.0/0 --target-tags=thohago-mvp`
- Static IP:
  - `gcloud compute addresses create thohago-mvp-tokyo-ip --project=notebooklm-485105 --region=asia-northeast1`
- VM:
  - `gcloud compute instances create thohago-mvp-tokyo --project=notebooklm-485105 --zone=asia-northeast1-b --machine-type=e2-small --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud --boot-disk-type=pd-standard --boot-disk-size=20GB --address=<reserved-ip> --tags=thohago-mvp`

### Result

- VM status: `RUNNING`
- Machine type: `e2-small`
- Boot disk: `20GB pd-standard`
- Internal IP: `10.146.0.3`
- External IP: `34.180.80.140`

## Application Deployment

### Remote install actions completed

- installed `python3-venv`, `python3-pip`, `caddy`
- created service user `thohago`
- copied app source to `/opt/thohago/app`
- created Python venv at `/opt/thohago/venv`
- installed runtime packages including `uvicorn`
- installed systemd unit: [thohago-web.service](/C:/Users/User/Desktop/Thohago_branding/deployment/gcp_mvp/thohago-web.service)
- installed Caddy config: [Caddyfile](/C:/Users/User/Desktop/Thohago_branding/deployment/gcp_mvp/Caddyfile)
- wrote runtime env file to `/opt/thohago/app/.env`

## Runtime Verification

### Service status

- `thohago-web`: `active`
- `caddy`: `active`

### Public checks

- `GET http://34.180.80.140/healthz`
  - result: `200`
  - body: `{"status":"ok"}`
- `GET http://34.180.80.140/admin/sessions`
  - result: `401 Unauthorized`
  - interpretation: admin auth protection is active
- `GET http://34.180.80.140/admin/sessions` with generated Basic auth credentials
  - result: `200`
  - interpretation: admin login is working with the deployed credential set

## Acceptance Checklist

### A. Infrastructure

- [x] new `e2-small` VM exists in `asia-northeast1-b`
- [x] static external IP is attached
- [x] port `80` is reachable from the internet

### B. Application Process

- [x] `uvicorn` is running under `systemd`
- [x] `caddy` is running and reverse proxying to the app
- [x] app responds on `/healthz`

### C. Runtime Configuration

- [x] deployed app has non-default admin credentials
- [x] deployed app has non-default sync token
- [x] deployed app is configured with `THOHAGO_WEB_STT_MODE=groq`
- [x] deployed app has `GROQ_API_KEY` configured

### D. Public Verification

- [x] public `GET /healthz` succeeds
- [x] public `GET /admin/sessions` is protected

## Secrets / Operator Access

- Generated operator credentials were written locally to:
  - [credentials.txt](/C:/Users/User/Desktop/Thohago_branding/runs/_deploy_tmp/credentials.txt)

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-01
