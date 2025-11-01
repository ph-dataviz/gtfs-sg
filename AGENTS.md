# Repository Guidelines

## Project Structure & Module Organization
Source scripts live at the repository root for now: `build_gtfs.py` orchestrates generation, `lta_api_client.py` handles DataMall requests and caching, `gtfs_generator.py` writes GTFS tables, and `gtfs_validator.py` wraps validation steps. Runtime assets are stored under `api_cache/` for cached payloads, `gtfs_output/` for produced feeds, and `validation_output/` for reports. Keep any new helpers alongside related scripts and document major additions in `README.md`.

## Build, Test, and Development Commands
Use `python build_gtfs.py` for a full fetch-and-generate cycle. Prefer `python build_gtfs.py --use-cache` when iterating to avoid API rate limits, and pair it with `--save-cache` on the first run after schema changes. Run targeted validation with `python build_gtfs.py --validate` or call `python gtfs_validator.py gtfs_output` for a standalone check; add `--download-validator` and `--run-canonical` when you need the full MobilityData suite. Inspect cache health with `python inspect_cache.py` before shipping updates.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation, `snake_case` for functions and module-level variables, and `CamelCase` for classes. Keep modules small and focused—favor pure functions in the generator, move API-specific logic into `lta_api_client.py`, and centralize shared constants in `config.py`. Type hints are optional but encouraged for new code paths touching feed schema.

## Testing & Validation Guidelines
There is no unit-test harness yet, so treat GTFS validation as your regression guard. Run `python build_gtfs.py --use-cache --validate` before submitting changes that touch generation logic, and include canonical validator output for structural or scheduling changes. When adding new cache formats, update `inspect_cache.py` to assert expected keys and sizes.

## Commit & Pull Request Guidelines
Write commits in the imperative mood (e.g., "Add service calendar export") and keep them scoped to a single concern. Reference issue IDs in the subject when applicable. Pull requests should outline the problem, summarize the solution, and note validation commands you executed. Include before/after metrics (stop counts, route totals, validation warnings) whenever feed content changes.

## Configuration & Secrets
Store local API keys only in `config.py` or environment variables; never commit secrets. Document any new configuration flags inside `config.py` and mirror them in the README usage examples. For CI parity, avoid hard-coded paths and keep default output inside `gtfs_output/`.
