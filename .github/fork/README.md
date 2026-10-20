# Unrestricted fork automation

`Fork Sync and Build` checks upstream every five minutes (UTC minutes
2, 7, 12, ..., 57), on a push/PR to `main`, or manually from the Actions tab.
It follows every commit on upstream `main`, including direct commits and PR
merges. Scheduled runs and external notifications with no upstream changes skip
the build. GitHub may delay scheduled workflows; five minutes is its minimum
schedule interval, not a guaranteed maximum synchronization delay.

A push in the upstream repository does not automatically trigger workflows in
this fork. An authenticated external listener can send a `repository_dispatch`
event with type `upstream-main-updated` for immediate checking. No upstream
webhook/listener is configured by this repository; the five-minute schedule is
the active automatic trigger. Creating a webhook on upstream requires upstream
owner/admin access. The receiver always fetches upstream `main` itself and does
not accept source commits or shell commands from the event payload.

The workflow merges **already merged** commits from `HMCL-dev/HMCL:main`.
It does not merge arbitrary open upstream PRs. It reapplies the download policy,
builds/tests the exact resulting commit, packages both macOS architectures, and
only then fast-forwards this fork's `main`. PR runs verify/build without publishing.
All jobs use the same source commit. A push made with `GITHUB_TOKEN` does not
trigger another push workflow, so builds happen in this workflow itself.

This fork keeps only `Fork Sync and Build`. The upstream Java CI, mirror,
release, PR labeling and code-check/comment workflows are removed; code-style
and translation checks run inside the remaining build job. Each sync filters
out new or modified upstream workflow files and preserves the fork's own
workflow, so upstream CI changes do not reintroduce extra Actions.

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

Merge conflicts in `RegionUtils.java` are resolved by keeping upstream's machine
detector and reapplying the download policy. Workflow conflicts are resolved by
preserving the fork's workflow and removing upstream workflows. Other conflicts,
policy drift, failed tests/builds or a concurrent update to `main` stop publication.
No forced updates to `main` are used.

## Downloads

Open a successful run's **Artifacts** (retained for 90 days):

Each distribution is uploaded as a separate, unzipped file. Both the artifact
name and downloaded filename use
`HMCL-unrestricted-<system>-<architecture>-<format>-<commitID>.<extension>`,
where `commitID` is the full 40-character commit that was built.

| System | Architecture | Format | Filename prefix |
| --- | --- | --- | --- |
| macOS / Windows / Linux | universal | JAR | `HMCL-unrestricted-all-universal-jar-` |
| Windows | read from the EXE PE header (currently x86) | EXE | `HMCL-unrestricted-windows-x86-exe-` |
| Linux | universal | SH | `HMCL-unrestricted-linux-universal-sh-` |
| Linux | all (Debian package metadata) | DEB | `HMCL-unrestricted-linux-all-deb-` |
| macOS Intel | x86_64 | DMG | `HMCL-unrestricted-macos-x86_64-dmg-` |
| macOS Apple Silicon | arm64 | DMG | `HMCL-unrestricted-macos-arm64-dmg-` |

The same universal JAR is available separately for macOS users who prefer the
standard launcher over a DMG. DMGs contain architecture-specific JavaFX runtimes.
No separate checksum files are generated in distribution staging or uploaded as
artifacts. GitHub provides artifact digests; build inputs and staged copies are
still verified internally.
The Windows architecture describes the native launcher executable, not the Linux
build runner. Internal source bundles and test reports keep descriptive names.

macOS images are ad-hoc signed, without Apple notarization. Windows/Linux/JAR
distributions retain upstream Java runtime requirements. These are unofficial
builds, not signed upstream releases. Test reports are retained for 14 days.

No additional secret is needed to synchronize/build. Optional repository secrets
`MICROSOFT_AUTH_ID` and `CURSEFORGE_API_KEY` enable the corresponding upstream
integrations; without them, builds succeed but Microsoft login and CurseForge
API functionality may be unavailable. No upstream credentials are copied.

Upstream workflow definitions are filtered out. If GitHub rejects a publication
because of workflow-file permissions, the optional `UPSTREAM_SYNC_TOKEN` secret
can provide repository Contents and Workflows write access (classic PAT: `repo`
and `workflow`). The default token cannot grant itself Workflows permission;
a rejected push leaves `main` unchanged.
This token is used only in the publish job, after builds pass. A PAT-authenticated
push triggers one additional run; that run finds no new commits and performs no
further push.

## Local checks

```sh
python3 .github/fork/download_policy.py --apply
python3 .github/fork/workflow_policy.py
python3 .github/fork/test_download_policy.py
python3 .github/fork/download_policy.py
./gradlew build checkstyle checkTranslations --no-daemon --parallel
python3 .github/fork/download_policy.py --jar HMCL/build/libs/HMCL-*.jar
```
