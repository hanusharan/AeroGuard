# Contributing and commit conventions

AeroGuard is a single-author research project, so this is a lightweight guide to
keeping Git history readable and honest, not a process. It applies to future
commits only; existing history is not rewritten, and older commits use mixed
subject styles.

A commit records that a change was made. It does not show that the change is
scientifically valid.

## Commit subjects

Use `type: short imperative subject`, in lowercase, ideally under about 70
characters. An optional scope is fine: `fix(ml): …`.

| Type | Use for | Example (illustrative, not an existing commit) |
|---|---|---|
| `research` | Hypotheses, experiment decisions, results and `RESEARCH_LOG.md` entries, plus the result files they cite | `research: record a new experiment decision` |
| `feat`, `fix`, `refactor` | Scientific or software code: simulator, dataset generation, features, training, evaluation, dashboard | `fix: correct an evaluation edge case` |
| `docs` | README, reproducibility instructions, citations, `CHANGELOG.md`, log structure | `docs: document reproducibility requirements` |
| `test` | Adding or changing tests | `test: add temporal leakage regression coverage` |
| `ci`, `build`, `deps`, `chore` | Workflows, dependency configuration, tooling | `ci: configure dataset-independent test checks` |

## Commit messages

The subject says *what* changed. The body (a few lines is enough) says *why*, and
for anything that could affect results it also says what was and was not checked.
For `research` commits, name the log entry (for example `RL-NNN`), the seed and
dataset/configuration, and keep **observations** (what was measured) separate from
**interpretation** (what it might mean). Do not put words like "validated" or
"proves" in a subject unless independent evidence exists.

If Claude Code assisted with a change, keep the co-author trailer it adds. Do not
add or remove it for work that does not match, so the history agrees with the
README's "AI assistance" section.

## When to split commits

Separate commits when changes have different reasons to exist or different
risks:

- **Scientific code vs. everything else.** Do not mix a change to the simulator,
  features, labels, splits, models, thresholds or evaluation with unrelated
  documentation, tooling or formatting. Reviewers should be able to see exactly
  what could alter a result.
- **Code vs. the results it produces.** Commit the code change first, then
  commit new outputs and the `RESEARCH_LOG.md` entry that interprets them as a
  `research` commit that names the code commit.
- **Dependency, CI or test changes vs. code,** unless one cannot work without
  the other.

Keep **one atomic commit** when splitting would leave the repository
inconsistent or broken: a fix and the test that covers it, a rename and its
reference updates, or a documentation change that must land with the behavior it
describes. A coherent change is more important than a tidy category.

Each commit should leave the CI test selection passing (see
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md)). Documentation-only commits are
exempt from re-running tests.

## Changelog and research log

- **[`CHANGELOG.md`](CHANGELOG.md)** records substantive changes to the repository
  and software. Add or update the entry under *Unreleased* in the same commit as
  the change, or in the commit that completes it. Pure typo fixes need none.
- **[`RESEARCH_LOG.md`](RESEARCH_LOG.md)** records research reasoning. Commit the
  hypothesis and expected outcome *before* running an experiment, then add the
  result, interpretation and decision after. Failed or null results get an entry
  too. Follow the rules in that file; do not edit past entries, add a new one.
- A change that touches both (for example, a new evaluation method) updates both,
  each with its own purpose: what changed in the software versus what was
  decided and observed.

## Frozen research artifacts

The v0.1–v0.3 datasets and reports, the model
`outputs/ml_v03/models/primary_model_D_1s.joblib`, and the published paper are
frozen. New experiments write new files under new names. A commit should never
edit a frozen artifact; if one is genuinely wrong, add a correction as a new
entry and a new commit.

## History hygiene

- Do not rewrite or force-push history that has been pushed or published.
- Do not commit generated datasets or other gitignored bulky outputs.
- Do not commit credentials or local tooling configuration (`.claude/`,
  `.venv/`).
- Keep unfinished or exploratory work on a branch; keep `main` consistent with
  what the dashboard, README and paper describe.

## Versions and releases

Several different things carry version-like names in this project. They do not
share a number and must not be conflated:

| Kind | What it is | Current state (checked 2026-10-12) |
|---|---|---|
| Research baseline | A dataset, model and report set. The frozen baseline is **v0.3**; see [`baselines/README.md`](baselines/README.md). | v0.3 manifest in `baselines/v0.3.sha256`. |
| Research-record label | "v1.0" names the frozen research packaging in commit messages and the dashboard pill ("Frozen Research · v1.0"). | A label only; no tag or release. |
| Paper / publication | The Zenodo record, DOI 10.5281/zenodo.22724022, and its PDF. | Not editable from this repo. The PDF still shows the older repository URL. Zenodo metadata not checked (unreachable). |
| Software release | A tagged, documented state of the code. | **None exists.** No Git tags (local), and no tags or GitHub releases on `hanusharan/AeroGuard`. |
| Dashboard label | `dashboard/package.json` (`0.0.0`, a private scaffold) and the hero pill. | Not release versions. |
| Git refs | Commits, branches, tags. | `main` at `66b5661`; a separate remote branch `credibility-v1.1` exists with unmerged changes. |

A software release does not establish new scientific validity, does not
re-version the v0.3 results, and does not replace the paper.

**Proposal (not adopted; needs the author's approval).** Treat the corrected
repository as a *software release* with its own version, separate from v0.3
and from the paper. The author's unmerged `credibility-v1.1` branch already
uses the working name "v1.1 (correction release, unreleased draft)", so `v1.1`
is the natural candidate, but that branch also adds new analyses
(`outputs/analysis_v11/`: rule baselines and bootstrap intervals), which are
research results, not corrections. Decide whether to release those separately or
under their own `RESEARCH_LOG.md` entry. No version number should be written into
`CITATION.cff` or elsewhere until a release actually exists.

**Before cutting a release** (none of this has been done):

1. Commit and merge the local work, reconciling it with `credibility-v1.1`
   (both add `LICENSE`, `CITATION.cff`, `.github/workflows/tests.yml` and edit
   the README, paper link and hero; their content differs).
2. Confirm the GitHub Actions test workflow passes on the merged commit. Note
   that merging to `main` also triggers the dashboard's Pages deploy.
3. Run `sha256sum -c baselines/v0.3.sha256` and the checks in
   [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).
4. Rebuild the paper PDF (`paper/build_paper.py`, which needs Chrome and the
   paper's fonts) and publish a new Zenodo version, so the paper no longer shows
   the old repository URL.
5. Turn the *Unreleased* section of [`CHANGELOG.md`](CHANGELOG.md) into a dated
   entry, then add `version` and `date-released` to `CITATION.cff` using the real
   release.
6. Create an annotated tag and a GitHub release whose notes link to the
   changelog entry and state that the release makes no new scientific claims.

