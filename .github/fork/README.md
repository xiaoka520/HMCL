# Unrestricted fork automation

`Fork Sync and Build` runs every hour at minute 23 (UTC), on a push/PR to
`main`, or manually from the Actions tab. Scheduled runs with no upstream
changes skip the build. GitHub may delay scheduled workflows.

The workflow merges **already merged** commits from `HMCL-dev/HMCL:main`.
It does not merge arbitrary open upstream PRs. It reapplies the download policy,
builds/tests the exact resulting commit, packages both macOS architectures, and
only then fast-forwards this fork's `main`. PR runs verify/build without publishing.
All jobs use the same source commit. A push made with `GITHUB_TOKEN` does not
trigger another push workflow, so builds happen in this workflow itself.

## Download policy

`RegionUtils.isIsChinaMainlandNetwork()` always returns `false`; `init()` does
nothing. The IP query, network response parser, cached result and failure-based
blocking behavior from upstream PR #7017 are absent. The disabled UI branches
and translations may remain upstream, but they cannot be entered through this
API. Machine-region detection remains intact for mirror selection, account
defaults and Terracotta. Changing language/time zone or setting JVM flags is
unnecessary.

The normalizer preserves the upstream machine-detection method. It checks for
unknown RegionUtils methods, new callers, inverted UI checks and the known IP
query. The build also checks the shipped JAR bytecode: the network method must
be exactly `iconst_0; ireturn`, and initialization must be just `return`.
These checks cover the known restriction design, not arbitrary future upstream
implementations. Review policy checks when upstream changes the design.

Only a merge conflict in `RegionUtils.java` can be resolved automatically, by
keeping upstream's machine detector and reapplying the policy. Other conflicts,
policy drift, failed tests/builds or a concurrent update to `main` stop publication.
No forced updates to `main` are used.

## Downloads

Open a successful run's **Artifacts** (retained for 90 days):

* Windows/Linux/universal: `.exe`, `.jar`, `.sh`, `.deb` and SHA-256 files.
* macOS Intel: `.dmg` with an x86_64 JavaFX runtime.
* macOS Apple Silicon: `.dmg` with an arm64 JavaFX runtime.

macOS images are ad-hoc signed, without Apple notarization. Windows/Linux/JAR
distributions retain upstream Java runtime requirements. These are unofficial
builds, not signed upstream releases. Test reports are retained for 14 days.

No additional secret is needed to synchronize/build. Optional repository secrets
`MICROSOFT_AUTH_ID` and `CURSEFORGE_API_KEY` enable the corresponding upstream
integrations; without them, builds succeed but Microsoft login and CurseForge
API functionality may be unavailable. No upstream credentials are copied.

## Local checks

```sh
python3 .github/fork/download_policy.py --apply
python3 .github/fork/test_download_policy.py
python3 .github/fork/download_policy.py
./gradlew build checkTranslations --no-daemon --parallel
python3 .github/fork/download_policy.py --jar HMCL/build/libs/HMCL-*.jar
```
