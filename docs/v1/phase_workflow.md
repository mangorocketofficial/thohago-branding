# Phase Delivery Workflow

This repository follows a fixed three-step workflow for every phase:

1. Contract document creation
2. Implementation
3. Contract verification

## Rules

- A new phase does not start with code. It starts with a contract document.
- The contract defines what "done" means before implementation begins.
- Implementation is allowed to evolve internally, but it may not silently change the contract scope.
- A phase is not complete when code exists. It is complete only after the contract is verified.
- Verification must record concrete evidence: commands, artifacts, links, screenshots, or logs.

## Required Documents

For each phase, keep these files in `docs/`:

- `phaseN_contract.md`
- `phaseN_verification.md`

## Contract Document Must Include

- Goal and business outcome
- In-scope deliverables
- Out-of-scope items
- Required inputs and outputs
- Acceptance criteria
- Required commands or operator flows
- Dependencies, credentials, and environment assumptions
- Completion evidence required at verification time

## Verification Document Must Include

- Contract version/date being verified
- Verification environment
- Exact commands or user flows executed
- Produced artifacts and file paths
- Pass/fail result for each acceptance criterion
- Remaining gaps or follow-up actions

## Change Control

- If implementation reveals a better approach, update the contract first.
- Do not let the verification document become the place where scope changes are discovered retroactively.
- Contract changes should be explicit and dated.

