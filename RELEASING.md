# Releasing

Releases use semantic versioning and tags in the form `vMAJOR.MINOR.PATCH`.

The repository contains two independently versioned deliverables:

- the Kapso HACS integration, versioned in `pyproject.toml` and its manifest;
- the WAHA HAOS app, versioned in `waha/config.yaml` and published to GHCR with
  the same image tag.

Every push to `main` that changes `waha/` builds and publishes the app image.
Pull requests build it without publishing. Bump the app version whenever its
runtime image changes; documentation-only edits do not require a bump.
After the first image publish, verify that the `ha-waha` GHCR package is public;
HAOS cannot install a private package from a custom app repository.

WAHA app releases use tags in the form `waha-vMAJOR.MINOR.PATCH`. The release
workflow verifies the tag against `waha/config.yaml` before creating the GitHub
release. Never reuse an app tag or its versioned image tag.

1. Update `version` in `pyproject.toml` and
   `custom_components/kapso_whatsapp/manifest.json` to the same value.
2. Add the release notes and date to `CHANGELOG.md`.
3. Run `uv run python scripts/check_version.py`, then the validation commands
   from `README.md`.
4. Commit and push the release preparation to `main`. Wait for validation to
   pass.
5. Create and push the matching tag, for example:

   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```

The release workflow verifies that the tag matches both version files and then
creates the corresponding GitHub release with generated release notes. Never
move or reuse a published release tag.
