# Changelog

All notable changes to `db-name-to-idx-mapper` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.0.3 - 2026-10-27

- First stable release.
- Ansible support (`ANSIBLE.md`).
- Concurrent writers are serialised on `<config>.lock` and the config file is replaced atomically: processes that
  add mappings at the same time get distinct indices, and readers never see a partly written file. The file keeps
  its permissions when rewritten.
- `exec` maps an exact mapped name to its index (it was passed through unchanged), runs once per mapping for a
  prefix (it failed with a `TypeError`), and exits with the utility's exit code.
- `MappingResult` is exported from the package; the package ships `py.typed`.
- Requires Python 3.8+ (was declared as 3.7+, which was never tested).
- Build backend is `uv_build`; the version lives in `pyproject.toml` and `__version__` reads it from the installed
  package metadata. `requirements.txt` and `MANIFEST.in` are removed.

## v0.1.0
- Initial release
- Cross-platform support
- CLI and Python API
- Utility parameter mapping
- Prefix filtering
