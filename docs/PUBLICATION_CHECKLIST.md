# GitHub publication checklist

No project repository initialization, commit, remote configuration, push or public release
was performed in milestone 3. This checklist is for a future reviewed action.

For the current **private, two-computer** repository plan, use
[github_publication_checklist.md](github_publication_checklist.md). The checklist
below retains the broader public/portfolio release review. Private visibility
does not remove privacy checks, but selecting a public code license is not a
technical prerequisite for the first private commit.

## First-commit blockers

1. **Review notebook outputs and machine paths.** Notebooks remain intact and
   eligible for tracking, but may embed unapproved images and local identifiers.
   Select reviewed originals or agree on separately named presentation copies.
2. **Choose and document licenses.** Code ownership, project license, third-party
   notices, image provenance and any data/media distribution terms remain open.
3. **Approve the exact staging list.** `.gitignore` intentionally keeps originals,
   weights, recordings, raw figures and old backups local; it is not blanket
   approval for everything it leaves visible. Do not begin with `git add .`.
4. **Acknowledge current reproducibility boundaries.** The notebook environment is
   observed, not locked; the complete curriculum is not clean-kernel validated.
   Do not advertise a green full suite or a public end-to-end dataset recipe.
5. **Document checksum discrepancies without rewriting references.** The legacy
   historical-file test fails against changed notebook 12; notebook 13 now has
   61 cells and `image_processing.ipynb` is absent. Preserve canonical v1 and its
   manifest; decide how future tests should distinguish frozen fixtures from
   editable notebooks in a later implementation task.

These are publication-quality gates, not claims that Git technically requires a
license or a passing test suite to create any commit.

## Privacy and credentials

- [ ] Review all 12 original photos and four educational assets, including screens,
  keys/keychains, wallet/ID-like objects, faces, location cues and reflections.
- [ ] Review full notebook renders, text outputs, tracebacks, embedded HTML,
  widgets and screenshots; checking source code alone is insufficient.
- [ ] Review the four JPEGs embedded in the Rerun recording before distributing it.
- [ ] Remove sensitive content only from explicitly approved public presentation
  copies; preserve scientific originals and references.
- [ ] Confirm local paths/usernames in notebooks are acceptable or agree on a
  separate reviewed public copy. No notebook sanitization was performed here.
- [ ] Run a secret scanner on the exact selected files and staging area before the
  first commit; scan history as well before the first push if history exists.
- [ ] If a real credential is ever found, revoke/rotate it; hiding the file in
  `.gitignore` is not credential remediation.

## Licenses, data and weights

- [ ] Choose a project code license and add it only after the decision is made.
- [ ] Record source, author, redistribution permission and attribution for images.
- [ ] Record upstream package and checkpoint license terms separately; review
  Ultralytics integration before asserting a compatible project license.
- [ ] Keep `.pt`, `.pth`, `.ckpt`, `.onnx` and other downloadable weights ignored.
- [ ] Preserve local weights; document official download methods and hashes later.
- [ ] Confirm whether approved raw data will be tracked, attached to a release,
  or supplied privately. Do not invent a dataset URL before one exists.

## Repository size and notebook outputs

- [ ] Inspect candidate file sizes after applying `.gitignore`; no SAM weights
  should appear. GitHub blocks regular Git files above 100 MiB.
- [ ] Decide how to handle large rendered notebooks while retaining local history.
- [ ] Keep canonical v1's six files together and verify its payload hashes.
- [ ] Keep Rerun validation/environment documentation with any reviewed recording.
- [ ] Use curated figures and short demos rather than committing every run/video.
- [ ] Review selected media for source rights and personal information.
- [ ] Evaluate Git LFS or release attachments only for artifacts that need it;
  do not use either as a reason to upload all downloaded dependencies.

## Setup, tests and scientific claims

- [ ] Keep notebook and Rerun requirements/environments separate.
- [ ] Validate fresh installation of the notebook stack in a disposable environment.
- [ ] Validate the Rerun pinned recipe on a clean supported machine before adding
  a portability claim; milestone 3 performed no installations.
- [ ] Document datasets and model downloads required for each notebook.
- [ ] Keep 8/8 milestone-2 Rerun tests distinguished from the historical suite's
  17 passes / 1 failure / 8 skips. Re-run appropriate checks before publication.
- [ ] Resolve or explicitly qualify missing assets and stateful notebook cells.
- [ ] Complete visual QA of the intended public Rerun layout/capture.
- [ ] Do not infer 3D correctness from low reprojection error or a working viewer.
- [ ] Label future VGGT, Gaussian Splatting and adversarial 3D work as planned.
- [ ] Add CI and badges only after the corresponding checks actually exist and pass.

## Future Git staging and publication review

When repository initialization is separately approved, inspect `git status`,
`git check-ignore -v`, the chosen path list and `git diff --cached` before a commit.
Include notebook renders/media in the review, since textual diffs do not reveal
all embedded content. An ignore rule does not remove an already tracked file.

Before a first push, review the complete commit history, the remote destination,
license notices and public README claims. This milestone authorizes none of those
publishing actions. See [the file-selection review](RELEASE_REVIEW.md) for the
current candidate/hold decisions.
