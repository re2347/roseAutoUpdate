# Rose CN Release Automation

This branch is the China-ready Rose build line. It keeps the upstream Rose
application code, adds China server LCU compatibility, downloads skins from the
GitCode `cloneSkin` mirror, and updates Rose from the GitCode CN release repo.

## Repository Roles

- `Alban1911/Rose`: upstream Rose source.
- `re2347/roseAutoUpdate`: GitHub mirror connected to CircleCI. Keep `main`
  as the clean upstream mirror, and keep the China changes on `cn`.
- `Re2347/cloneSkin`: skin repository mirror. Updating this repository does not
  require rebuilding Rose.
- `Re2347/guoneibanrosedl`: CN release channel. Store release attachments here
  and keep `latest.json` at the repo root.

## Automated Flow

1. Sync upstream `Alban1911/Rose` into `roseAutoUpdate/main`.
2. Merge or rebase `main` into `cn`.
3. Push `cn`.
4. `.circleci/config.yml` runs on a Windows cloud runner.
5. The workflow runs `python -m unittest discover -v`.
6. The workflow runs `python scripts/build_pyinstaller.py`.
7. The workflow packages `dist/Rose` as `release/Rose-CN-<version>.zip`.
8. The workflow publishes the ZIP as a GitCode release attachment and updates
   `guoneibanrosedl/latest.json`.
9. Installed CN Rose clients read `latest.json`, download the ZIP from GitCode,
   verify SHA-256, and install it.

Your PC does not need to be online for steps 3-9 when the workflow runs on a
cloud Windows runner.

## Required Secret

Add this secret to the cloud CI project:

- `GITCODE_TOKEN`: a GitCode token that can create releases, upload release
  attachments, and update files in `Re2347/guoneibanrosedl`.

The workflow uses CircleCI because Rose needs a Windows build runner. GitCode
stays the public download source.

If `Re2347/guoneibanrosedl` is still completely empty, create an initial
`README.md` on GitCode first so the `main` branch exists before the first
automated publish.

## Versioning

The package version defaults to `config.APP_VERSION`. For normal upstream
updates, use the upstream version, for example `1.2.15`.

For a CN-only rebuild of the same upstream version, bump to a numeric
four-part version before building, for example:

```powershell
python scripts/set_app_version.py 1.2.14.1
```

Do not use suffix versions such as `1.2.14-cn.1`. The current Rose version
parser ignores suffixes, so that can compare equal to `1.2.14`.

## Manual Release Commands

Run these commands from the Rose source root if you need to reproduce the CI
locally:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -v
python scripts/build_pyinstaller.py
python scripts/package_cn_release.py --version 1.2.14.1 --output-dir release
$env:GITCODE_TOKEN = "<token>"
python scripts/publish_gitcode_release.py --manifest release/latest.json --zip release/Rose-CN-1.2.14.1.zip --skip-if-current
```

## When You Need To Intervene

You only need to step in when:

- Git merge or rebase conflicts happen between upstream `main` and `cn`.
- Unit tests fail.
- Windows build fails.
- GitCode publish fails because `GITCODE_TOKEN` is missing or expired.
- The workflow refuses a same-version package with a different SHA-256. Bump the
  version to a four-part CN hotfix version.
- The changed code touches real LCU, injection, or WeGame path detection and
  needs a real China-server gameplay check.
