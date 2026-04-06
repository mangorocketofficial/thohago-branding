# Web Phase 9 Bot Avatar Patch Contract

> Status: Active  
> Date: 2026-04-02  
> Reference: [web_phase9_contract.md](./web_phase9_contract.md)

## Goal

Replace the assistant text avatar `또` with an AI bot icon in the customer conversation UI.

## In Scope

1. Assistant avatar rendering in shared customer chat thread
2. Assistant avatar rendering in complete page status bubble
3. Minimal CSS needed to size and style the icon consistently
4. Live server deployment for the updated avatar

## Out of Scope

- user avatar redesign
- conversation layout changes
- route or state changes
- admin UI changes

## Acceptance Criteria

### A. Assistant Avatar

- assistant bubbles no longer render the `또` text badge
- assistant bubbles render a visible AI bot icon instead

### B. User Avatar Stability

- user bubbles still render the existing `나` text avatar

### C. Regression Safety

- existing customer conversation pages still render without layout breakage
- live server shows the icon after deployment

## Completion Evidence Required

The verification record must include:

1. local rendering/test evidence
2. live server fetch evidence
3. pass/fail status for the acceptance criteria
