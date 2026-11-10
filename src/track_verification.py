"""Experiment 02: fixed-final-pose verification of recorded propagation proposals.

This is a closed-candidate diagnostic, not replay of incremental SfM. Only the
34 recorded propagation events are assessed; no point IDs or poses are changed.
"""
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np

from src.canonical_reconstruction import project, read_csv, require, validate_export

VARIANTS = [("baseline", None), ("gate_1px", 1.), ("gate_2px", 2.),
            ("gate_3px", 3.), ("gate_5px", 5.)]


def load_frozen(canonical_dir):
    """Numeric-only loader: no photographs, cv2, torch, or Rerun are needed."""
    folder = Path(canonical_dir)
    validate_export(folder)
    with np.load(folder / "points.npz", allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in archive.files}
    return dict(folder=folder, arrays=arrays,
                manifest=json.loads((folder / "manifest.json").read_text()),
                cameras=json.loads((folder / "cameras.json").read_text())["cameras"],
                observations=read_csv(folder / "observations.csv"),
                metrics=read_csv(folder / "metrics.csv"))


def recorded_candidates(data):
    """Canonical row order is deterministic but is NOT original match-loop order."""
    return [dict(observation_id=int(r["observation_id"]), point_id=int(r["point_id"]),
                 camera_id=int(r["camera_id"]), keypoint_id=int(r["keypoint_id"]),
                 stage=int(r["stage"]), observed_sift=[float(r["u_sift"]), float(r["v_sift"])],
                 source_camera_id=int(r["source_camera_id"]),
                 source_keypoint_id=int(r["source_keypoint_id"]))
            for r in data["observations"] if r["provenance"] == "descriptor_propagation"]


def verify_associations(candidates, xyz, cameras, *, threshold=None, existing=None):
    """Optional insertion gate, usable by a future registered-camera caller.

    Inputs and existing maps are not mutated. Target keys are (camera_id,
    keypoint_id), not XYZ or point ID. Existing identities win; different incoming
    IDs for an unmapped target are all rejected as ambiguous (no nearest-ID guess).
    Exact duplicate proposals are rejected after their first occurrence. An
    existing identical mapping can be reused. Multiple keypoints for one point
    in a camera are allowed and counted separately. No source-track replay occurs.

    threshold=None disables geometry checks, preserving the no-gate baseline.
    Gated proposals require finite XYZ/pixels/projection/depth and z>0, with an
    inclusive residual <=threshold in SIFT-image pixels. Only the TARGET is gated.
    """
    require(threshold is None or (np.isfinite(threshold) and threshold >= 0), "Invalid threshold.")
    cameras = {c["camera_id"]: c for c in cameras}
    identities = defaultdict(set)
    for c in candidates:
        identities[(c["camera_id"], c["keypoint_id"])].add(c["point_id"])
    current = dict(existing or {})
    seen, decisions = set(), []
    for c in candidates:
        row = dict(c)
        pid, cid, kp = c["point_id"], c["camera_id"], c["keypoint_id"]
        target, triple = (cid, kp), (cid, kp, pid)
        reasons = []
        valid_ref = isinstance(pid, (int, np.integer)) and 0 <= pid < len(xyz) and cid in cameras and kp >= 0
        predicted, depth, error = np.full(2, np.nan), np.nan, np.nan
        if not valid_ref:
            reasons.append("unknown_reference")
        else:
            camera = cameras[cid]
            with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                predicted, depth = project(xyz[pid], camera["R_world_to_camera"], camera["t_world_to_camera"], camera["K_sift"])
                error = float(np.linalg.norm(predicted - np.asarray(c["observed_sift"])))
            finite = (np.isfinite(xyz[pid]).all() and np.isfinite(c["observed_sift"]).all()
                      and np.isfinite(predicted).all() and np.isfinite([depth, error]).all())
            if threshold is not None:
                if not finite:
                    reasons.append("nonfinite_geometry")
                if np.isfinite(depth) and depth <= 0:
                    reasons.append("nonpositive_depth")
                if np.isfinite(error) and error > threshold:
                    reasons.append("reprojection_error")
        if triple in seen:
            reasons.append("duplicate_candidate")
        if target in current and current[target] != pid:
            reasons.append("existing_keypoint_conflict")
        elif target not in current and len(identities[target]) > 1:
            reasons.append("ambiguous_candidate_ids")
        seen.add(triple)
        action = "reject" if reasons else ("reuse" if target in current else "insert")
        if not reasons:
            current[target] = pid
        row.update(accepted=not reasons, action=action, rejection_reasons=";".join(reasons),
                   depth_camera=float(depth) if np.isfinite(depth) else None,
                   error_sift_px=float(error) if np.isfinite(error) else None,
                   projected_sift=predicted.tolist() if np.isfinite(predicted).all() else None)
        decisions.append(row)
    return decisions


def distribution(values):
    values = [v for v in values if v is not None and np.isfinite(v)]
    if not values:
        return dict(n=0, min=None, median=None, mean=None, p95=None, max=None)
    return dict(n=len(values), min=float(np.min(values)), median=float(np.median(values)),
                mean=float(np.mean(values)), p95=float(np.percentile(values, 95)), max=float(np.max(values)))


def coverage(rows):
    tracks = defaultdict(set)
    pairs = Counter()
    for r in rows:
        tracks[int(r["point_id"])].add(int(r["camera_id"]))
        pairs[(int(r["point_id"]), int(r["camera_id"]))] += 1
    return dict(associations=len(rows), point_ids=len(tracks),
                point_camera_pairs=len(pairs), point_camera_pairs_with_multiple_keypoints=sum(v > 1 for v in pairs.values()),
                camera_ids=sorted({int(r["camera_id"]) for r in rows}),
                points_with_at_least_two_cameras=sum(len(v) >= 2 for v in tracks.values()),
                points_with_at_least_three_cameras=sum(len(v) >= 3 for v in tracks.values()))


def compare_variants(data):
    candidates = recorded_candidates(data)
    # This is a fixed final snapshot, not a claim about available maps at stage 3.
    fixed = [r for r in data["observations"] if r["provenance"] != "descriptor_propagation"
             and r["active_in_final_map"] == "True"]
    existing = {(int(r["camera_id"]), int(r["keypoint_id"])): int(r["point_id"]) for r in fixed}
    summaries, decisions = [], []
    canonical = {int(r["observation_id"]): r for r in data["observations"]}
    for name, threshold in VARIANTS:
        result = verify_associations(candidates, data["arrays"]["xyz"], data["cameras"],
                                     threshold=threshold, existing=existing)
        for r in result:
            reference = canonical[r["observation_id"]]
            require(np.isclose(r["error_sift_px"], float(reference["reprojection_error_px"]),
                               atol=1e-8, rtol=0), "Canonical reprojection mismatch.")
            r.update(variant=name, threshold_sift_px=threshold)
        accepted, rejected = ([r for r in result if r["accepted"] == keep] for keep in [True, False])
        kept_ids = {r["observation_id"] for r in accepted}
        retained = fixed + [r for r in data["observations"] if int(r["observation_id"]) in kept_ids
                            and r["active_in_final_map"] == "True"]
        reasons = Counter(reason for r in rejected for reason in r["rejection_reasons"].split(";"))
        summaries.append(dict(
            variant=name, threshold_sift_px=threshold, proposed=len(result), accepted=len(accepted), rejected=len(rejected),
            inserted=sum(r["action"] == "insert" for r in result), reused=sum(r["action"] == "reuse" for r in result),
            rejection_reasons=dict(reasons),
            proposed_errors=distribution([r["error_sift_px"] for r in result]),
            accepted_errors=distribution([r["error_sift_px"] for r in accepted]),
            rejected_errors=distribution([r["error_sift_px"] for r in rejected]),
            accepted_candidate_coverage=coverage(accepted), retained_final_coverage=coverage(retained),
            retained_active_errors=distribution([float(r["reprojection_error_px"]) for r in retained]),
            retained_active_over_3px=sum(float(r["reprojection_error_px"]) > 3 for r in retained),
            accepted_propagation_over_3px=sum(r["error_sift_px"] > 3 for r in accepted),
            rejected_propagation_at_most_3px=sum(r["error_sift_px"] <= 3 for r in rejected),
            point_cloud_ids=len(data["arrays"]["point_ids"]), registered_cameras=len(data["cameras"]),
            downstream_pnp="not rerun", downstream_triangulation="not rerun"))
        decisions.extend(result)
    keys = Counter((c["camera_id"], c["keypoint_id"]) for c in candidates)
    targets = defaultdict(set)
    for c in candidates:
        targets[(c["camera_id"], c["keypoint_id"])].add(c["point_id"])
    nonprop_bad = [int(r["observation_id"]) for r in fixed if float(r["reprojection_error_px"]) > 3]
    report = dict(experiment="02_geometric_track_verification", mode="frozen_final_pose_diagnostic",
                  proposal_universe="34 recorded descriptor_propagation events only; not all descriptor matches",
                  candidate_order="canonical observation_id, not original match-loop order",
                  conflict_policy="existing wins; reject ambiguous unmapped targets; reject duplicate proposals",
                  variants=summaries,
                  candidate_duplicate_target_keys=sum(v > 1 for v in keys.values()),
                  candidate_conflicting_target_keys=sum(len(v) > 1 for v in targets.values()),
                  candidate_existing_conflicts=sum((c["camera_id"], c["keypoint_id"]) in existing
                                                   and existing[(c["camera_id"], c["keypoint_id"])] != c["point_id"] for c in candidates),
                  canonical_inactive_rows=sum(r["active_in_final_map"] == "False" for r in data["observations"]),
                  unique_xyz_positions=len(np.unique(data["arrays"]["xyz"], axis=0)),
                  duplicate_xyz_groups=len(data["manifest"]["anomalies"]["duplicate_position_groups"]),
                  unaffected_nonpropagation_over_3px_observation_ids=nonprop_bad,
                  limitations=["Final-pose, fixed-candidate diagnostic; no source-availability cascade or rematching.",
                               "Canonical events were sorted after capture; within-stage match order is unavailable.",
                               "Removed proposals can change later candidate availability and triangulation in a real replay.",
                               "Approximate shared intrinsics, no distortion model or bundle adjustment, no ground truth.",
                               "All point IDs and camera poses are fixed. Coverage is retained evidence, not recovered geometry.",
                               "A small reprojection residual alone does not establish a correct feature identity."])
    return report, decisions
