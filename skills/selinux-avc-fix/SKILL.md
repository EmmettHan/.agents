---
name: selinux-avc-fix
description: Diagnose and fix SELinux avc/denied logs by proposing minimal policy changes in the sepolicy_ext repository (.te, file_contexts, type declarations). Use when a user provides SELinux audit/avc errors or asks to adjust SELinux permissions for services/files in this repo.
---

# Selinux Avc Fix

## Overview

Identify the minimal SELinux policy changes needed to resolve avc denials in this repository while following local conventions and least-privilege rules.

## Workflow

### 1) Collect complete evidence

- Ask for full avc/audit log lines, not summaries.
- Require these fields when possible: `scontext`, `tcontext`, `tclass`, denied perms, `comm`, `path`, `name`.
- If path or label is missing, ask for `ls -Z <path>` or `ps -Z` output.
- If anything is unclear, do not guess; say "I don't know" and request the missing detail.

Example log line to request:
```
avc: denied { read write } for pid=... comm="..." name="..." dev="..." ino=... \
scontext=u:r:... tcontext=u:object_r:... tclass=file permissive=0
```

### 2) Locate the policy home

- Find existing types and rules with `rg` in the repo (types in `public/`, rules in `system/`).
- Prefer the module that already defines the `scontext` domain or the target type.
- Follow existing naming patterns; do not invent new patterns without checking nearby modules.

### 3) Decide the smallest safe change

- Add only the specific permissions shown in the denial.
- Avoid wildcards and broad rules.
- If the target path lacks a type, add or fix `file_contexts` mapping first.
- Use `audit2allow` only as a hint; verify every permission.

### 4) Implement edits

- Update `public/` for type/attribute definitions when needed.
- Update `system/` for allow rules (one rule per line, explicit perms).
- Update `file_contexts` with `u:object_r:<type>:s0` for any new paths.
- Keep changes inside this extension repo; do not touch main repo or `neverallow`.

### 5) Report and validate

- Provide a concise rationale per rule tied to the log evidence.
- Suggest relevant repo scripts or build checks if the user asks for verification.

## Output expectations

- Show the exact files and rules to add/modify.
- Explain how each rule maps to the denied permission.
- Call out any assumptions or missing data.

## References

- Load `references/repo-guidelines.md` for module layout, naming, and style rules.
