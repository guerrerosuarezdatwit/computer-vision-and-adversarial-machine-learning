# File selection and publication review

Review date: **2026-11-06**. This is a local publication assessment, not a public
release approval or a guarantee that all sensitive content has been found.
No project Git repository, commit, remote, push or release was created in milestone 3.

The **2026-11-07 follow-up** targets private GitHub synchronization between Mac and
Windows. Notebook token-pattern checks again found no apparent matches; local
paths remain in notebooks 06, 07 and 13. The four downloadable weight copies and
the large notebook outputs remain local and unchanged. The earlier visual review
and its sampling limits still apply; private hosting is not clearance to share all
photos or embedded notebook outputs. See the current
[private staging plan](github_publication_checklist.md).

## Recommended tracking policy

`.gitignore` protects local environments, credentials, weights and unreviewed
media. Being eligible for tracking is not the same as being approved for release.
Do not use a broad `git add .` before the notebook-output review.

| Files | Recommended decision | Reason / prerequisites |
| --- | --- | --- |
| Root README, `.gitignore`, `docs/`, requirements files | Track after review. | Public-facing explanation and setup evidence. Notebook requirements are explicitly observational. |
| `src/`, `scripts/`, `tests/` | Track after code/license review. | Reusable implementation and verification. Keep known test failures visible. |
| `notebooks/01_*.ipynb` through `13_*.ipynb` | Preserve locally; candidates to track only after manual output/privacy and asset-rights review. | Educational history, but embedded images, traces and machine paths need review. No notebook was cleaned or rewritten here. |
| `results/canonical_reconstruction/v1/` | Track as an immutable, small numerical reference after rights/provenance review. | Required by artifact tests; contains arrays, observations, metrics and schema, but no original JPEG bytes. Keep all six files together. |
| Diagnostic `points.csv`, `summary.json`, `control_cases.json`, `image_sha256.json`, README | Track after review. | Small scientific evidence and test inputs. |
| Rerun v1 README, `environment.txt`, `validation.json` | Track after review. | Reproduction and validation records; historical statuses remain dated records. |
| Original `data/` and `assets/` | Ignore pending review. | Photos/rights unresolved; some images expose personal workspace details or people. |
| `.rrd` / `.rbl` | Ignore by default; consider a reviewed GitHub Release asset later. | RRD contains four original JPEGs, not just numerical geometry. |
| Generated PNGs, Plotly HTML and notebook backup | Keep locally and ignore initially. | Images may reproduce unapproved source assets; HTML bundles Plotly; backup duplicates outputs and local paths. |
| `.venv`, `.venv-rerun`, caches and model weights | Ignore; preserve local copies. | Machine-specific or large/downloadable dependencies, not source code. |
| Future videos / GIFs | Ignore until individually reviewed. | Screen captures may include desktop notifications, paths or unrelated windows. |

The ignore policy selects canonical **v1** only. Newly generated v2/v3 directories
remain ignored until explicitly reviewed and selected. It does not ignore all NPZ
or CSV files, which would hide essential numerical fixtures. Excluded data and the
ignored frozen notebook backup mean a source-only checkout cannot yet replay the
entire classical pipeline; the numerical payload can be validated independently.

## Size assessment

The current local project is approximately **827 MiB excluding both environments
and caches**. Two identical SAM files are about 357.7 MiB each; two YOLO files are
about 5.35 MiB each. Local weights are retained, not deleted or relocated.

The largest notebooks are approximately 17.35 MiB (07), 16.27 MiB (06),
10.64 MiB (11) and 10.36 MiB (08), mostly due to outputs. These can produce noisy
diffs even if allowed by hosting limits. GitHub blocks ordinary Git files over
100 MiB and warns above 50 MiB; model weights must not enter the first commit.
See [GitHub's large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

Do not solve size concerns by deleting notebook history or outputs in this
milestone. Decide later whether to publish reviewed original notebooks or clearly
identified presentation copies, with archival provenance preserved.

The actual ignore rules were checked with Git using temporary metadata outside
the project: **22 exclusion cases and 26 eligibility cases passed**. The resulting
candidate set is **46 files, approximately 77.4 MiB**, including unapproved notebook
outputs; its largest file is about 17.35 MiB. No file in that set exceeds 100 MiB.
This is a size/selection check, not permission to stage or publish those files.

## Sensitive-information review

### Verified observations

- A text-pattern scan of 41 non-environment files found no apparent private-key
  headers, AWS access IDs, GitHub/Hugging Face/OpenAI token patterns or credential
  URLs. Notebook code and textual outputs were inspected without printing secrets.
- An extended check also covered notebook text/HTML/Plotly JSON outputs and literal
  credential assignments; no matching credential locations were found.
- Machine paths occur in notebooks 06, 07 and 13, the historical notebook backup,
  and `results/REPOSITORY_AUDIT.md`. The audit and backup are ignored. Notebooks
  still require output review; an ignored raw photo can remain embedded in a
  tracked notebook's outputs.
- All 16 original/educational images were checked for a GPS EXIF tag; none was
  found. This does not remove privacy risk from visible image content.
- Visual sampling covered `data/view_01.jpg`, `view_06.jpg`, `view_12.jpg` and all
  four `assets/` images. Other Deku views still need individual visual review.
- Sampled Deku photos show a personal workspace and computer displays. The
  two `assets/multiview_*.jpeg` photos also show keys/keychains, a wallet and screen
  content. The street image includes people, vehicles, signs and location cues.
- The RRD embeds the original photographs associated with Views 03–06.
  Excluding `data/` alone does not protect those images if the recording is released.

### Limits and next decisions

The scan did not deserialize model weights, inspect arbitrary binaries for
credentials, perform exhaustive OCR, inspect external user caches, or audit Git
history (there is no local Git history). Pattern scans are not a secret-free
certification. A future secret scanner should also run against the selected
staging area and any history that will actually be published.

The owner should review all raw images, notebook renderings and screen captures
before release. Do not edit the scientific originals to resolve presentation
concerns: any later approved cropped/redacted presentation copy must have a
separate name and provenance. Changing photos used by reconstruction requires a
new, explicitly different experiment and must not invalidate canonical v1.

## Candidate figures, videos and datasets

| Material | Public-release recommendation |
| --- | --- |
| `notebooks/multiview_geometric_connectivity.png` | Strong candidate after visual review: explains camera overlap without needing a desktop screenshot. Copy to a reviewed documentation-media path later; do not relocate the historical file. |
| Numerical plots of angle, depth and reprojection error | Preferred portfolio figures. Generate presentation copies from canonical metrics in a future task, with thresholds and units in captions. No new figures were generated here. |
| Existing FGSM/PGD and quantization PNGs | Conditional: establish the dog image's source/license; preserve perturbation scaling and avoid calling a single-image result a general attack success rate. |
| `results/eot_translation_robustness.png` | Inspect the rendered content before selection; filename alone does not establish that the correct figure was saved. |
| Plotly `diagnostics.html` | Useful downloadable demo after content/embedded-data and bundled-library notice review. Not selected for the first source commit. |
| Rerun `.rrd` | Useful future release attachment after embedded-photo review; about 3.8 MiB, so Git LFS is not required merely because it is an RRD. Keep SDK/version and checksum alongside it. |
| A future 20–40 second Rerun video | Good portfolio candidate: show stages, RGB/diagnostic tabs and an investigated point. Capture only the approved viewer content; label it a sparse four-camera prototype. No video currently exists. |
| The 12-photo Deku sequence | Small dataset candidate after ownership, background/privacy, attribution and depiction-rights review. Original photos remain unchanged and ignored. |
| `assets/street.webp` and `assets/dog.jpeg` | Do not redistribute based solely on local possession. Source URLs, author/license and required attribution are not documented. |
| `assets/multiview_*.jpeg` | Keep private pending workspace/screen/keys review, even if the photographs were self-captured. |

## Licenses and model provenance

No project-wide `LICENSE` was created: a license choice needs ownership and
dependency/asset review. Code, images, derived media, data and pretrained weights
may need different notices. Do not present one code license as permission to
redistribute all third-party material.

Record the exact sources, hashes, versions and license conditions of `sam_b.pt`,
`yolo11n.pt`, torchvision weights and Hugging Face checkpoints before distributing
or claiming a reproducible model download. Names alone do not prove artifact
identity. Review the actual Ultralytics package/checkpoint terms rather than
assuming its dependency is covered by the project's eventual license. The local
SAM checkpoint must likewise be traced to its source; the upstream
[Segment Anything license](https://github.com/facebookresearch/segment-anything/blob/main/LICENSE)
does not by itself establish the provenance of every similarly named file.

This document records publication work remaining; it is not a legal conclusion
or a completed rights clearance.
