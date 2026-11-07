"""Portable, lossless export of notebook 13's existing map, without filtering it.

The validator reads only the exported files (and optionally referenced images).
It does not need a notebook kernel, Plotly, PyTorch, OpenCV, or Rerun.
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


SCHEMA_VERSION = "1.0.0"
FILES = ("points.npz", "cameras.json", "observations.csv", "metrics.csv")
OBSERVATION_FIELDS = (
    "observation_id", "point_id", "camera_id", "keypoint_id", "stage", "provenance",
    "source_camera_id", "source_keypoint_id", "active_in_final_map",
    "u_sift", "v_sift", "u_original", "v_original", "projected_u_sift",
    "projected_v_sift", "depth_camera", "reprojection_error_px",
    "geometrically_consistent_3px", "source_evidence",
)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def project(xyz, R, t, K):
    """Project using X_camera = R @ X_world + t, in row-array notation."""
    camera = np.asarray(xyz, dtype=float) @ np.asarray(R).T + np.asarray(t).reshape(3)
    homogeneous = camera @ np.asarray(K).T
    with np.errstate(divide="ignore", invalid="ignore"):
        uv = homogeneous[..., :2] / homogeneous[..., 2:3]
    return uv, camera[..., 2]


def capture_propagation(ns, view_a, view_b, stage):
    """Observe the historical propagation rule on copies before expand_map runs.

    This records only inserted associations, not descriptor matches rejected or
    ignored by the historical code. No geometry gate is added to that algorithm.
    """
    maps = {v: ns["view_maps"][v].copy() for v in (view_a, view_b)}
    good = [m for m, n in ns["bf"].knnMatch(
        ns["descriptors"][view_a], ns["descriptors"][view_b], k=2)
        if m.distance < .75 * n.distance]
    events = []
    for match in good:
        qa, qb = match.queryIdx, match.trainIdx
        if qa in maps[view_a] and qb not in maps[view_b]:
            target, kp, source, source_kp = view_b, qb, view_a, qa
        elif qb in maps[view_b] and qa not in maps[view_a]:
            target, kp, source, source_kp = view_a, qa, view_b, qb
        else:
            continue
        pid = maps[source][source_kp]
        maps[target][kp] = pid
        events.append(dict(point_id=int(pid), camera_id=target + 1,
                           keypoint_id=int(kp), stage=stage,
                           provenance="descriptor_propagation",
                           source_camera_id=source + 1, source_keypoint_id=int(source_kp),
                           source_evidence=f"pre-expansion descriptor propagation, stage {stage}"))
    return events


def canonical_arrays(ns):
    """Preserve source XYZ dtype/values; encode reversible integer RGB samples."""
    xyz = np.asarray(ns["global_points"]).copy()
    normalized = np.asarray(ns["global_colors"])
    rgb = np.rint(normalized * 255).astype(np.uint8)
    require(np.array_equal(rgb.astype(float) / 255., normalized),
            "Source colors are not losslessly representable as uint8 RGB.")
    stage = np.full(len(xyz), -1, dtype=np.int64)
    stage[:len(ns["seed_points_3d"])], stage[ns["new_from_05"]], stage[ns["new_from_06"]] = 0, 3, 4
    require(np.all(stage >= 0), "Some points have no reconstruction stage.")
    return dict(point_ids=np.arange(len(xyz), dtype=np.int64), xyz=xyz, rgb=rgb, stage=stage)


def build_cameras(ns):
    cameras = []
    for camera_id, (rotation, translation) in sorted(ns["camera_poses"].items()):
        index = camera_id - 1
        R, t = np.asarray(rotation), np.asarray(translation).reshape(3)
        C = -R.T @ t
        oh, ow = ns["images_rgb"][index].shape[:2]
        sh, sw = ns["gray_views"][index].shape
        scale = np.diag([sw / ow, sh / oh, 1.])
        K = np.asarray(ns["K"])
        w2c, c2w = np.eye(4), np.eye(4)
        w2c[:3, :3], w2c[:3, 3] = R, t
        c2w[:3, :3], c2w[:3, 3] = R.T, C
        require(np.allclose(C, ns["camera_centers"][camera_id], atol=1e-12, rtol=0),
                f"Camera {camera_id} center differs from historical variable.")
        cameras.append(dict(
            camera_id=camera_id, image_index=index,
            registration_stage={3: 0, 4: 0, 5: 1, 6: 2}[camera_id],
            image_path=f"data/{ns['image_paths'][index].name}",
            original_size=dict(width=ow, height=oh), sift_size=dict(width=sw, height=sh),
            scale_original_to_sift=[sw / ow, sh / oh],
            K_sift=K.tolist(), K_original=(np.linalg.inv(scale) @ K).tolist(),
            R_world_to_camera=R.tolist(), t_world_to_camera=t.tolist(),
            center_world=C.tolist(), T_world_to_camera=w2c.tolist(),
            T_camera_to_world=c2w.tolist(),
            intrinsics_status="approximate_shared_K; original-resolution K derived by scaling",
            distortion_status="not modeled; original images have not been undistorted"))
    return dict(schema_version=SCHEMA_VERSION,
                pose_convention="X_camera = R_world_to_camera @ X_world + t_world_to_camera",
                camera_axes="right-handed RDF: +X right, +Y down, +Z forward",
                world_frame="View 03 camera frame; arbitrary monocular scale; seed baseline = 1",
                pixel_convention="(u,v) = (column,row), top-left origin; linear scaling between image sizes",
                resize="cv2.resize default INTER_LINEAR; target width 900; height int(h * 900 / w)",
                cameras=cameras)


def build_observations(ns, groups, propagation_events):
    """Union of birth evidence, retained PnP inliers, and propagation events.

    An overwritten birth association remains a row with active_in_final_map=False.
    Provenance describes its creation, not a claim of correct correspondence.
    """
    events = []
    for ids, a, b, matches, label in groups:
        stage = {"Seed 03-04": 0, "View 05": 3, "View 06": 4}[label]
        for pid, match in zip(ids, matches):
            for camera, kp in [(a + 1, match.queryIdx), (b + 1, match.trainIdx)]:
                events.append(dict(point_id=int(pid), camera_id=camera, keypoint_id=int(kp),
                                   stage=stage, provenance="seed_triangulation" if stage == 0 else "new_triangulation",
                                   source_camera_id="", source_keypoint_id="",
                                   source_evidence=f"original birth pair {a+1:02d}-{b+1:02d}; verified replay"))
    for camera, mapping in [(5, ns["view05_to_3d"]), (6, ns["cam06"]["kp_to_3d"])]:
        for kp, pid in sorted(mapping.items()):
            events.append(dict(point_id=int(pid), camera_id=camera, keypoint_id=int(kp),
                               stage=camera - 4, provenance="pnp_inlier",
                               source_camera_id="", source_keypoint_id="",
                               source_evidence="retained keypoint-to-point dictionary after original PnP RANSAC"))
    events.extend(propagation_events)
    events.sort(key=lambda r: (r["stage"], r["camera_id"], r["point_id"], r["keypoint_id"], r["provenance"]))
    for observation_id, row in enumerate(events):
        pid, camera, kp = row["point_id"], row["camera_id"], row["keypoint_id"]
        view = camera - 1
        u, v = ns["keypoints"][view][kp].pt
        R, t = ns["camera_poses"][camera]
        uv, depth = project(ns["global_points"][pid], R, t, ns["K"])
        error = float(np.linalg.norm(uv - [u, v]))
        oh, ow = ns["images_rgb"][view].shape[:2]
        sh, sw = ns["gray_views"][view].shape
        row.update(observation_id=observation_id,
                   active_in_final_map=ns["view_maps"][view].get(kp) == pid,
                   u_sift=u, v_sift=v, u_original=u * ow / sw, v_original=v * oh / sh,
                   projected_u_sift=float(uv[0]), projected_v_sift=float(uv[1]),
                   depth_camera=float(depth), reprojection_error_px=error,
                   geometrically_consistent_3px=bool(np.isfinite(error) and depth > 0 and error <= 3))
    final = {(int(pid), view + 1, int(kp)) for view, mapping in ns["view_maps"].items()
             for kp, pid in mapping.items()}
    recorded = {(r["point_id"], r["camera_id"], r["keypoint_id"]) for r in events if r["active_in_final_map"]}
    require(recorded == final, "Observation provenance does not account for all final map associations.")
    return events


def duplicate_groups(xyz):
    groups = {}
    for pid, point in enumerate(xyz):
        groups.setdefault(tuple(point.tolist()), []).append(pid)
    return [ids for ids in groups.values() if len(ids) > 1]


def export_canonical(ns, propagation_events, repository_root, output_dir, protected_hashes):
    """Export only after source variables agree with the persisted diagnostics."""
    import importlib.metadata
    import platform
    from datetime import datetime, timezone
    from src import triangulation_diagnostics as td

    root, output_dir = Path(repository_root), Path(output_dir)
    require(not output_dir.exists(), "Output directory already exists; choose a new version.")
    points_before = ns["global_points"].copy()
    colors_before = ns["global_colors"].copy()
    maps_before = {v: mapping.copy() for v, mapping in ns["view_maps"].items()}
    arrays, cameras = canonical_arrays(ns), build_cameras(ns)
    require(len(arrays["point_ids"]) == 386, "This export targets the historical 386-ID reconstruction.")
    groups = td.replay_birth_observations(ns)
    current_metrics = td.diagnose_map(ns)
    historic_path = root / "results/triangulation_diagnostics/points.csv"
    historic = read_csv(historic_path)
    summary = json.loads((historic_path.parent / "summary.json").read_text())
    mask, reasons = td.classify(current_metrics, **summary["thresholds"])
    require(len(historic) == len(current_metrics) == 386, "Historical diagnostic count differs.")
    max_delta = 0.
    for old, current, accepted, why in zip(historic, current_metrics, mask, reasons):
        for name, value in current.items():
            if isinstance(value, str):
                require(old[name] == value, f"Historical metric text differs: {name}")
            else:
                delta = abs(float(old[name]) - value)
                max_delta = max(max_delta, delta)
                require(np.isfinite(delta) and delta <= 1e-7, f"Historical metric differs: point {current['point_id']}, {name}")
        require(old["accepted"] == str(bool(accepted)) and old["rejection_reasons"] == ";".join(why), "Historical diagnostic decisions differ.")
    require(np.array_equal(arrays["xyz"], [[float(row[k]) for k in ("x", "y", "z")] for row in historic]), "Historical XYZ differs; no new reconstruction will be substituted.")
    observations = build_observations(ns, groups, propagation_events)
    require(np.array_equal(ns["global_points"], points_before) and np.array_equal(ns["global_colors"], colors_before)
            and ns["view_maps"] == maps_before, "Export changed historical in-memory state.")
    # Check provenance recorder against actual final maps; report overwritten evidence.
    inactive_birth = [r["observation_id"] for r in observations if "triangulation" in r["provenance"] and not r["active_in_final_map"]]
    unique_active = {(r["camera_id"], r["keypoint_id"]): r for r in observations if r["active_in_final_map"]}
    high = sorted({r["point_id"] for r in unique_active.values() if r["reprojection_error_px"] > 3})
    images = []
    for path, image in zip(ns["image_paths"], ns["images_rgb"]):
        h, w = image.shape[:2]
        images.append(dict(path=f"data/{path.name}", sha256=sha256(root / "data" / path.name), width=w, height=h))
    duplicates = duplicate_groups(arrays["xyz"])
    counts = [len(ns["seed_points_3d"])] * 3 + [len(ns["seed_points_3d"]) + len(ns["new_from_05"]), len(arrays["xyz"])]
    labels = ["seed_03_04", "register_camera_05", "register_camera_06", "expand_04_05", "expand_05_06"]
    manifest = dict(
        schema_version=SCHEMA_VERSION, export_version=output_dir.name, scene="Deku",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        point_count=386, registered_camera_count=4, observation_count=len(observations),
        diagnostic_accepted_count=int(mask.sum()), diagnostic_thresholds=summary["thresholds"],
        coordinate_convention="X_camera = R @ X_world + t; world is View 03; right-handed RDF; arbitrary scale",
        point_array_schema={k: dict(shape=list(v.shape), dtype=str(v.dtype)) for k, v in arrays.items()},
        rgb_encoding="uint8 RGB [0,255]; rgb.astype(float64)/255 equals source global_colors exactly",
        stages=[dict(stage=i, name=label, point_count=counts[i],
                     registered_camera_ids=[[3, 4], [3, 4, 5], [3, 4, 5, 6], [3, 4, 5, 6], [3, 4, 5, 6]][i])
                for i, label in enumerate(labels)],
        images=images,
        environment=dict(python=platform.python_version(), platform=platform.system(), architecture=platform.machine(),
                         packages={name: importlib.metadata.version(name) for name in ["numpy", "opencv-python", "Pillow", "plotly", "matplotlib"]}),
        reproduction=dict(source_notebook="results/triangulation_diagnostics/original_13_multiview_3d_reconstruction.ipynb",
                          notebook_algorithm="unchanged; original code cells in order; historical pip cell skipped; displays suppressed",
                          random_seed="not explicitly set by historical notebook; RNG behavior preserved",
                          metrics="byte-for-byte copy of historical points.csv after comparison with replay",
                          protected_files_sha256=protected_hashes,
                          exporter_source_sha256={p: sha256(root / p) for p in ["src/canonical_reconstruction.py", "scripts/export_canonical_reconstruction.py", "src/triangulation_diagnostics.py"]}),
        source_comparison=dict(xyz_exact_match=True, rgb_normalization_exact_roundtrip=True,
                               camera_centers_match_historical_variables=True, max_metric_absolute_difference=float(max_delta),
                               point_ids_preserved=True, source_state_unchanged=True),
        anomalies=dict(duplicate_position_groups=duplicates, unique_position_count=len(np.unique(arrays["xyz"], axis=0)),
                       duplicate_extra_id_count=sum(len(g) - 1 for g in duplicates),
                       diagnostic_rejected_point_ids=np.flatnonzero(~mask).tolist(),
                       high_error_final_association_point_ids=high,
                       max_final_association_error_px=max(r["reprojection_error_px"] for r in unique_active.values()),
                       inactive_birth_observation_ids=inactive_birth,
                       historical_point_birth_length=len(ns["point_birth"]),
                       canonical_stage_length=len(arrays["stage"]),
                       original_expansion_rejected_candidates=int(ns["stats05"]["candidates"] + ns["stats06"]["candidates"] - len(ns["new_from_05"]) - len(ns["new_from_06"]))),
        limitations=[
            "Approximate shared intrinsics f=0.9*900; no calibration, distortion model, or bundle adjustment.",
            "Only Views 03-06 have poses. The other eight images remain unregistered.",
            "Duplicate positions and all rejected point IDs are preserved; counts refer to IDs, not unique landmarks.",
            "Descriptor propagation was not geometrically validated by the original SfM algorithm.",
            "Observation consistency flags are post-hoc checks, not new inlier decisions or ground truth.",
            "PnP provenance covers retained dictionaries, not a complete history of RANSAC trials or discarded correspondences.",
            "Birth observations overwritten in final dictionaries are retained but marked inactive.",
            "The 107 originally rejected expansion candidates have no original map IDs and are not exported as map points.",
            "Depth is in arbitrary seed-baseline units. Low reprojection error does not establish reliable depth.",
            "Original-resolution K and pixels use conventional linear scaling; no recalibration or half-pixel correction is applied.",
            "Observation stages reflect actual notebook chronology; camera 06 is registered before either map expansion.",
        ],
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output_dir / "points.npz", **arrays)
    write_json(output_dir / "cameras.json", cameras)
    with (output_dir / "observations.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=OBSERVATION_FIELDS)
        writer.writeheader()
        writer.writerows(observations)
    (output_dir / "metrics.csv").write_bytes(historic_path.read_bytes())
    manifest["artifacts"] = {name: dict(sha256=sha256(output_dir / name), bytes=(output_dir / name).stat().st_size) for name in FILES}
    write_json(output_dir / "manifest.json", manifest)
    validation = validate_export(output_dir, root)
    print(json.dumps(dict(output=str(output_dir), validation=validation,
                          source_comparison=manifest["source_comparison"], anomalies=manifest["anomalies"]), indent=2))
    return manifest


def validate_export(output_dir, repository_root=None):
    """Independently check schemas, hashes, poses, projections, and cross-file IDs."""
    folder = Path(output_dir)
    manifest = json.loads((folder / "manifest.json").read_text())
    require(manifest["schema_version"] == SCHEMA_VERSION, "Unsupported schema version.")
    for filename in FILES:
        require(sha256(folder / filename) == manifest["artifacts"][filename]["sha256"], f"Artifact hash mismatch: {filename}")
    with np.load(folder / "points.npz", allow_pickle=False) as archive:
        require(set(archive.files) == {"point_ids", "xyz", "rgb", "stage"}, "Unexpected NPZ schema.")
        arrays = {name: archive[name] for name in archive.files}
    ids, xyz, rgb, stages = (arrays[k] for k in ("point_ids", "xyz", "rgb", "stage"))
    n = manifest["point_count"]
    require(ids.shape == (n,) and np.issubdtype(ids.dtype, np.integer) and np.array_equal(ids, np.arange(n)), "Point IDs must preserve original contiguous row indices.")
    require(xyz.shape == (n, 3) and np.issubdtype(xyz.dtype, np.floating) and np.isfinite(xyz).all(), "Invalid XYZ shape or values.")
    require(rgb.shape == (n, 3) and rgb.dtype == np.uint8, "Invalid RGB shape or dtype.")
    require(stages.shape == (n,) and np.issubdtype(stages.dtype, np.integer) and set(stages) <= {0, 3, 4}, "Invalid point birth stages.")
    require(duplicate_groups(xyz) == manifest["anomalies"]["duplicate_position_groups"], "Duplicate anomaly report mismatch.")
    camera_file = json.loads((folder / "cameras.json").read_text())
    cameras = {c["camera_id"]: c for c in camera_file["cameras"]}
    require(len(cameras) == len(camera_file["cameras"]) == 4 and set(cameras) == {3, 4, 5, 6}, "Expected four unique registered cameras.")
    for cid, c in cameras.items():
        R, t, C = (np.array(c[k]) for k in ("R_world_to_camera", "t_world_to_camera", "center_world"))
        K, Ko = np.array(c["K_sift"]), np.array(c["K_original"])
        T, inv = np.array(c["T_world_to_camera"]), np.array(c["T_camera_to_world"])
        require(R.shape == (3, 3) and t.shape == C.shape == (3,), "Invalid camera pose shape.")
        require(np.allclose(R.T @ R, np.eye(3), atol=1e-10) and np.isclose(np.linalg.det(R), 1, atol=1e-10), "Camera rotation is not SO(3).")
        require(np.allclose(C, -R.T @ t, atol=1e-10), "Camera center convention mismatch.")
        require(T.shape == inv.shape == (4, 4) and np.allclose(T @ inv, np.eye(4), atol=1e-10), "Camera transform inverse mismatch.")
        require(np.allclose(T[:3, :3], R) and np.allclose(T[:3, 3], t) and np.allclose(T[3], [0, 0, 0, 1]), "World-to-camera transform mismatch.")
        require(np.allclose(inv[:3, :3], R.T) and np.allclose(inv[:3, 3], C), "Camera-to-world transform mismatch.")
        original, sift = c["original_size"], c["sift_size"]
        sx, sy = c["scale_original_to_sift"]
        require(original["width"] > 0 and original["height"] > 0 and sift == {"width": 900, "height": int(original["height"] * 900 / original["width"])}, "Inconsistent SIFT dimensions.")
        require(np.allclose([sx, sy], [sift["width"] / original["width"], sift["height"] / original["height"]]), "Invalid resize scales.")
        require(K.shape == Ko.shape == (3, 3) and np.allclose(K, np.diag([sx, sy, 1]) @ Ko), "Intrinsics and image scales disagree.")
        require(c["image_index"] == cid - 1 and c["registration_stage"] == {3: 0, 4: 0, 5: 1, 6: 2}[cid], "Camera identity/stage mismatch.")
        if repository_root is not None:
            from PIL import Image
            with Image.open(Path(repository_root) / c["image_path"]) as image:
                require(image.size == (original["width"], original["height"]), "Referenced image dimensions mismatch.")
    require(np.allclose(cameras[3]["R_world_to_camera"], np.eye(3)) and np.allclose(cameras[3]["t_world_to_camera"], 0), "World frame is not View 03.")
    require(np.isclose(np.linalg.norm(np.array(cameras[3]["center_world"]) - cameras[4]["center_world"]), 1), "Seed baseline must be one arbitrary unit.")
    observations, metrics = read_csv(folder / "observations.csv"), read_csv(folder / "metrics.csv")
    require(len(observations) == manifest["observation_count"], "Observation count mismatch.")
    require([int(r["observation_id"]) for r in observations] == list(range(len(observations))), "Invalid observation IDs.")
    require([int(r["point_id"]) for r in metrics] == ids.tolist(), "Metrics point IDs mismatch.")
    birth, active = {}, {}
    for row in observations:
        pid, cid, kp = (int(row[f]) for f in ("point_id", "camera_id", "keypoint_id"))
        require(0 <= pid < n and cid in cameras and kp >= 0, "Association references an unknown point/camera/keypoint.")
        c = cameras[cid]
        uv = np.array([float(row["u_sift"]), float(row["v_sift"])])
        predicted, depth = project(xyz[pid], c["R_world_to_camera"], c["t_world_to_camera"], c["K_sift"])
        error = float(np.linalg.norm(predicted - uv))
        require(np.isfinite(uv).all() and np.all(uv >= 0) and np.all(uv < [c["sift_size"]["width"], c["sift_size"]["height"]]), "Observed keypoint lies outside the SIFT image.")
        require(np.allclose(predicted, [float(row["projected_u_sift"]), float(row["projected_v_sift"])], rtol=0, atol=1e-8), "Observation projection mismatch.")
        require(np.isclose(depth, float(row["depth_camera"]), atol=1e-8) and np.isclose(error, float(row["reprojection_error_px"]), atol=1e-8), "Observation depth/error mismatch.")
        require(np.allclose(uv / c["scale_original_to_sift"], [float(row["u_original"]), float(row["v_original"])]), "Original pixel scaling mismatch.")
        original_projection, _ = project(xyz[pid], c["R_world_to_camera"], c["t_world_to_camera"], c["K_original"])
        require(np.allclose(original_projection, predicted / c["scale_original_to_sift"], atol=1e-8), "Original-resolution projection mismatch.")
        require(row["active_in_final_map"] in {"True", "False"} and row["geometrically_consistent_3px"] == str(bool(depth > 0 and error <= 3)), "Invalid observation flags.")
        stage = int(row["stage"])
        require(stage >= int(stages[pid]) and stage >= c["registration_stage"] and stage <= 4, "Observation predates its point/camera.")
        provenance = row["provenance"]
        require(provenance in {"seed_triangulation", "new_triangulation", "pnp_inlier", "descriptor_propagation"}, "Unknown provenance.")
        if provenance in {"seed_triangulation", "new_triangulation"}:
            require(stage == int(stages[pid]), "Birth observation stage mismatch.")
            birth.setdefault(pid, []).append(row)
        if provenance == "descriptor_propagation":
            require(int(row["source_camera_id"]) in cameras and int(row["source_keypoint_id"]) >= 0 and stage in {3, 4}, "Invalid propagation source.")
        if row["active_in_final_map"] == "True":
            key = (cid, kp)
            require(key not in active or int(active[key]["point_id"]) == pid, "Conflicting final associations.")
            active[key] = row
    for pid, metric in enumerate(metrics):
        require(np.allclose([float(metric[k]) for k in ("x", "y", "z")], xyz[pid], atol=0, rtol=0), "Metrics XYZ mismatch.")
        rows = birth.get(pid, [])
        require(len(rows) == 2 and len({r["camera_id"] for r in rows}) == 2, "Each point needs two distinct birth cameras.")
        for suffix in ("a", "b"):
            row = next((r for r in rows if r["camera_id"] == metric[f"view_{suffix}"]), None)
            require(row is not None and row["keypoint_id"] == metric[f"kp_{suffix}"], "Birth association and metric mismatch.")
            require(np.isclose(float(row["reprojection_error_px"]), float(metric[f"error_{suffix}_px"]), atol=2e-6, rtol=0), "Birth reprojection error mismatch.")
            require(np.isclose(float(row["depth_camera"]), float(metric[f"depth_{suffix}"]), atol=1e-8), "Birth depth mismatch.")
        associated = [r for r in active.values() if int(r["point_id"]) == pid]
        require(len(associated) == int(metric["associated_observations"]), "Final association count differs from historical metrics.")
        if associated:
            require(np.isclose(max(float(r["reprojection_error_px"]) for r in associated), float(metric["associated_max_error_px"]), atol=2e-6, rtol=0), "Final association error differs from historical metrics.")
    require(sum(r["accepted"] == "True" for r in metrics) == manifest["diagnostic_accepted_count"], "Diagnostic acceptance count mismatch.")
    for stage in manifest["stages"]:
        require(int(np.sum(stages <= stage["stage"])) == stage["point_count"], "Stage point count mismatch.")
    if repository_root is not None:
        for image in manifest["images"]:
            require(sha256(Path(repository_root) / image["path"]) == image["sha256"], "Original image hash mismatch.")
    return dict(points=n, cameras=len(cameras), observations=len(observations),
                final_associations=len(active), diagnostic_accepted=manifest["diagnostic_accepted_count"],
                unique_positions=len(np.unique(xyz, axis=0)))
