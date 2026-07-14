# Repository Guidelines (sepolicy_ext)

## Layout

- Top-level directories are subsystem or custom modules (e.g., `base/`, `communication/`, `kh_*`).
- Each module uses `public/` + `system/`:
  - `public/` = type/attribute/service definitions
  - `system/` = allow rules and `file_contexts`
- Central whitelist lives in `whitelist/`.
- Helper scripts live in `scripts/`.

## Style and Naming

- Keep existing copyright headers in `.te` files.
- One rule per line; list permissions explicitly; avoid `*`.
- Type naming patterns:
  - `<service>`
  - `<service>_exec`
  - `<service>_data_file`
  - `sa_<service>_service`
- `file_contexts` labels: `u:object_r:<type>:s0`.

## Workflow and Checks

- Prefer minimal permissions; do not relax `neverallow`.
- Only modify rules inside this extension repository.
- Use `audit2allow -i <log>` only for hints; verify each permission.
- Typical maintenance scripts:
  - `cd scripts`
  - `python3 distribute_selinux_rules.py --dry-run ../update.te`
  - `python3 optimize_rules.py --all`
  - `python3 clean_backups.py --all`
- Build and strict checks are run in the main project:
  - `./build.sh --product-name <product> --build-target selinux_adapter`
- Runtime check:
  - `dmesg | rg "avc: denied"`
