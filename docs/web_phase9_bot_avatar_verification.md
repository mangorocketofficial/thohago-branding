# Web Phase 9 Bot Avatar Patch Verification

> Status: Verified  
> Date: 2026-04-02  
> Contract: [web_phase9_bot_avatar_contract.md](./web_phase9_bot_avatar_contract.md)

## Verification Environment

- OS: Windows (PowerShell)
- Python: 3.12.x local interpreter
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- Live server: `https://34.180.80.140.sslip.io`

## Automated Test Evidence

### Targeted UI tests

- Commands:
  - `python -m unittest discover -s tests -p 'test_web_phase9.py' -v`
  - `python -m unittest discover -s tests -p 'test_web_phase4.py' -v`
- Result: Pass
- Coverage:
  - conversation UI still renders
  - bot avatar icon markup is present
  - preview/approval flow still renders without layout regression

## Live Deployment Evidence

- Deploy artifact: `runs/_deploy_tmp/thohago-bot-avatar-patch.tgz`
- Service restart result: `thohago-web active`

## Live Fetch Evidence

### Command

```powershell
python - <<'PY'
import urllib.request
html = urllib.request.urlopen('https://34.180.80.140.sslip.io/s/6gJ5n_kJcsbOCJz-rvDi97YK-swMTSgI/complete').read().decode('utf-8', errors='ignore')
print(f"has_icon={'chat-avatar-icon' in html}")
print(f"has_bot_text_avatar={'>또<' in html}")
PY
```

### Result

- `has_icon=True`
- `has_bot_text_avatar=False`

## Acceptance Checklist

### A. Assistant Avatar

- [x] assistant bubbles no longer render the `또` text badge
- [x] assistant bubbles render a visible AI bot icon

### B. User Avatar Stability

- [x] user bubbles still render the existing `나` text avatar

### C. Regression Safety

- [x] customer conversation pages still render without layout breakage
- [x] live server shows the icon after deployment

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-02
