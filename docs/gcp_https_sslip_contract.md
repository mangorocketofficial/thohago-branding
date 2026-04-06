# GCP HTTPS sslip.io Contract

> Status: Active  
> Date: 2026-04-01

## Goal

Enable public HTTPS for the deployed MVP server using a temporary DNS-resolving hostname based on the current static IP.

## Target Hostname

- Hostname: `34.180.80.140.sslip.io`
- Public IP: `34.180.80.140`

## In Scope

1. Open firewall access for TCP `443`
2. Reconfigure Caddy from plain HTTP to host-based HTTPS
3. Update deployed app base URL to the HTTPS hostname
4. Reload services
5. Verify public HTTP and HTTPS behavior

## Out of Scope

- Cloud DNS setup
- custom branded domain
- TLS certificate customization

## Acceptance Criteria

### A. Networking

- Port `443` is reachable from the internet

### B. HTTPS

- `https://34.180.80.140.sslip.io/healthz` returns `200`
- Caddy serves a valid HTTPS certificate for the hostname

### C. App Configuration

- Deployed app uses `THOHAGO_WEB_BASE_URL=https://34.180.80.140.sslip.io`

### D. Redirect Behavior

- `http://34.180.80.140.sslip.io/healthz` redirects or upgrades to HTTPS

## Required Evidence

- exact `gcloud` and remote update commands
- service restart results
- public HTTPS verification results
