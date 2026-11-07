# Private GitHub repository and Windows clone checklist

Reviewed **2026-11-07**. The project currently has **no `.git` directory**.
No initialization, commit, remote creation or push was performed. This document
is the precise future procedure, **not authorization to execute it now**.

## Gate 1: approve the staging/privacy plan BEFORE initialization

- [ ] Back up the full existing project, including ignored originals, weights,
  environments and generated results, using a separate local/private backup.
- [ ] Review [RELEASE_REVIEW.md](RELEASE_REVIEW.md): notebook outputs have local
  paths and may embed people, screens, keys/keychains and other private scene details.
- [ ] Confirm that candidate notebook files are acceptable for the private remote.
  Keep originals unchanged; any later sanitized public copy needs a separate name.
- [ ] Review code/docs/tests, requirements and the selected numerical fixtures.
- [ ] Keep `data/`, `assets/`, private datasets, credentials, downloadable weights,
  RRD/RBL files and raw videos excluded. An RRD embeds four original photos.
- [ ] Decide which validation records and reviewed numerical plots to synchronize.
  Numerical canonical v1 plus small diagnostic CSV/JSON files are recommended;
  newly generated versions stay local until individually approved.
- [ ] Record unresolved source/asset licenses and ownership. Private use does not
  resolve redistribution permissions; a public portfolio release needs its own gate.
- [ ] Approve an exact list of notebook files or explicitly choose a source/docs-only
  first commit. In the latter case qualify README links to notebooks not yet committed.
- [ ] Review a credential-pattern/secret scan of selected files, outputs and any
  future staged area. No current token-pattern findings are a guarantee of safety.
- [ ] Check the largest files: two SAM copies are about 357.7 MiB each and must
  remain ignored; YOLO copies are also downloadable local weights.
- [ ] Acknowledge known notebook/test limitations and the historical hash mismatch.

**Stop here until the owner approves this plan.** No repository initialization
should precede that approval. A private first commit does not require pretending
the entire curriculum is reproducible or selecting a public code license prematurely.

## Gate 2: create an empty PRIVATE remote, after approval

- [ ] Confirm the intended owner/account and repository name `adversarial-vision`.
- [ ] In GitHub, select **New repository → Private**. Do not select Public.
- [ ] For this existing local project, leave automatic README, `.gitignore` and
  license initialization unchecked; avoid an unrelated initial remote commit.
- [ ] Review visibility and access list; create only after the owner authorizes it.
- [ ] Authenticate each computer separately using Git Credential Manager/browser
  login or device-specific SSH keys. Never embed tokens in repository URLs.

Official references: [create a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)
and [authentication](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github).

## Gate 3: reviewed local initialization and first commit on the Mac

Only after Gate 1 approval and explicit permission for these actions:

```bash
git init -b main
git status --short --ignored
git check-ignore -v .venv/bin/python .venv-rerun/bin/python sam_b.pt data/view_03.jpg
git check-attr text eol -- results/canonical_reconstruction/v1/metrics.csv
```

Configure the intended commit author locally. Review the actual ignore and
attribute behavior before staging. The following is a candidate **source/docs**
selection; it intentionally omits notebooks pending their separate review:

```bash
git add --dry-run -- .gitignore .gitattributes README.md docs requirements requirements-rerun.txt requirements-notebooks.observed.txt src scripts tests results/canonical_reconstruction/v1
```

Add individually approved diagnostic and Rerun metadata files and notebooks to
the plan; do not add entire raw-results/data folders or use `git add .`.
After reviewing the dry-run output, stage only the approved paths, then inspect:

```bash
git diff --cached --stat
git diff --cached --name-only
git diff --cached --check
git diff --cached
git status --short
```

- [ ] No weights, environment contents, credentials, original images or RRDs staged.
- [ ] Canonical v1 retains all six files and payload-only validation passes.
- [ ] Notebook/output renders and the actual staged content have been reviewed.
- [ ] Privacy, copyright/attribution and intended access have been acknowledged.
- [ ] Commit is explicitly approved; no commit was made by preparing this guide.

When the reviewed staging area is ready and committing is authorized:

```bash
git commit -m "Establish private research project foundation"
git remote add origin https://github.com/OWNER/adversarial-vision.git
git remote -v
```

Replace `OWNER`, verify the exact destination and private visibility again, and
obtain approval for the first push before executing `git push -u origin main`.
Do not force-push to reconcile an unexpected remote history. A secret already
committed needs credential rotation and history review, not just a new ignore rule.

## Gate 4: clone on Windows after the reviewed first push

- [ ] Install/verify Git for Windows and an appropriate CPython 3.12 x64 interpreter.
- [ ] Authenticate the same authorized owner/account; confirm private access.
- [ ] Clone into a **new** directory, not over an existing research project:

```powershell
git clone https://github.com/OWNER/adversarial-vision.git
Set-Location adversarial-vision
git status --short
git remote -v
git check-attr text eol -- results/canonical_reconstruction/v1/metrics.csv
```

- [ ] Follow [setup_windows.md](setup_windows.md); recreate both environments
  locally, never copy the Mac ones.
- [ ] Verify `nvidia-smi`, the CUDA torch build, explicit-device tensor smoke
  check and `pip check` before a GPU experiment. These remain untested here.
- [ ] Run device-policy tests and payload-only canonical validation first.
- [ ] Privately provision only approved images/recordings/weights when needed.
  Full hash validation must pass; do not normalize or resize transferred originals.
- [ ] Generate a new RRD version, verify it, and inspect the Viewer on Windows.
- [ ] Record Python patch, packages, driver/GPU and test results before claiming
  Windows setup is validated. Retain the existing Mac historical metadata.

## Gate 5: everyday synchronization

Use one active branch per change, inspect a clean working tree, pull with
`--ff-only`, and review exact paths before each commit/push. Keep a notebook owned
by one active machine at a time where possible. See
[development_workflow.md](development_workflow.md) for the two-computer routine.

Private hosting is not a public release. Any later public repository, portfolio
video, dataset or recording requires the separate privacy/license review in
[PUBLICATION_CHECKLIST.md](PUBLICATION_CHECKLIST.md). No CI badges, complete
notebook reproducibility, VGGT or Gaussian Splatting implementation are claimed.
