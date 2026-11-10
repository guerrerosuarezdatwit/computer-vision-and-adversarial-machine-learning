"""Final-snapshot observation inspection for the pinned Rerun 0.42.0 SDK.

An ID-indexed timeline coordinates views; it is not a Viewer selection callback
or a reconstruction timeline. Canonical coordinates and source files are immutable.
"""
from collections import Counter
import json
from pathlib import Path
import platform

import numpy as np

from src.canonical_reconstruction import project, require, sha256, write_json
from src.rerun_reconstruction import (
    SDK_VERSION, load_reconstruction, log_camera, point_attributes, read_recording,
)

TIMELINE = "inspect_point_id"
SELECTED = "/world/inspection/selected"
COLORS = {"active_consistent": [40, 210, 230], "active_inconsistent": [245, 65, 65],
          "inactive_consistent": [185, 130, 230], "inactive_inconsistent": [225, 100, 160]}


def observation_records(data):
    """Recompute predictions and residuals from actual observations, not errors.

    Three-pixel consistency is independent of point-level acceptance. Activity is
    the final snapshot flag, not an inferred history of track validity.
    """
    cameras = {c["camera_id"]: c for c in data["cameras"]}
    active = {}
    for row in data["observations"]:
        if row["active_in_final_map"] == "True":
            active[(int(row["camera_id"]), int(row["keypoint_id"]))] = int(row["point_id"])
    result = []
    for row in data["observations"]:
        pid, cid, kp = (int(row[k]) for k in ("point_id", "camera_id", "keypoint_id"))
        c = cameras[cid]
        uv = np.array([float(row["u_original"]), float(row["v_original"])])
        sift = np.array([float(row["u_sift"]), float(row["v_sift"])])
        xyz = data["arrays"]["xyz"][pid]
        predicted, depth = project(xyz, c["R_world_to_camera"], c["t_world_to_camera"], c["K_original"])
        predicted_sift, _ = project(xyz, c["R_world_to_camera"], c["t_world_to_camera"], c["K_sift"])
        error = float(np.linalg.norm(predicted_sift - sift))
        original_error = float(np.linalg.norm(predicted - uv))
        require(np.allclose(uv * c["scale_original_to_sift"], sift, rtol=0, atol=1e-9), "Observed pixel scaling mismatch.")
        require(np.isclose(error, float(row["reprojection_error_px"]), rtol=0, atol=1e-8), "Recorded residual mismatch.")
        consistent = bool(depth > 0 and error <= 3.)
        require(consistent == (row["geometrically_consistent_3px"] == "True"), "Recorded consistency mismatch.")
        is_active = row["active_in_final_map"] == "True"
        replacement = active.get((cid, kp)) if not is_active else None
        result.append(dict(
            point_id=pid, camera_id=cid, keypoint_id=kp, observation_id=int(row["observation_id"]),
            creation_stage=int(row["stage"]), provenance=row["provenance"],
            source_evidence=row["source_evidence"],
            source_camera_id=row["source_camera_id"], source_keypoint_id=row["source_keypoint_id"],
            active_in_final_map=is_active, consistent_3px=consistent,
            overwritten_by_point_id=-1 if replacement is None else replacement,
            status=("active" if is_active else "inactive") + ("_consistent" if consistent else "_inconsistent"),
            error_sift_px=error, error_original_px=original_error, depth_camera=float(depth),
            observed=uv, projected=predicted))
    return result


def observation_attributes(rows):
    fields = {"point_id": np.int64, "camera_id": np.int64, "keypoint_id": np.int64,
              "observation_id": np.int64, "creation_stage": np.int64,
              "overwritten_by_point_id": np.int64, "active_in_final_map": bool,
              "consistent_3px": bool, "error_sift_px": np.float64,
              "error_original_px": np.float64, "depth_camera": np.float64,
              "status": str, "provenance": str, "source_evidence": str,
              "source_camera_id": str, "source_keypoint_id": str}
    return {k: np.array([r[k] for r in rows], dtype=dtype) for k, dtype in fields.items()}


def inspection_text(data, records, pid):
    rows = [r for r in records if r["point_id"] == pid]
    attrs = point_attributes(data, np.array([pid]))
    lines = [f"# Canonical point ID {pid}",
             f"Birth stage: {int(attrs['birth_stage'][0])}; triangulation accepted: {bool(attrs['accepted'][0])}.",
             f"Angle: {attrs['angle_deg'][0]:.4f} deg; depth: {attrs['depth_baselines'][0]:.4f} baselines.",
             f"Duplicate IDs: {attrs['duplicate_ids'][0] or 'none'} (positions are never merged).",
             "", "| Camera | Observation / keypoint | Status | Provenance | Error SIFT / original px | Replaced by ID |",
             "| --- | --- | --- | --- | --- | --- |"]
    for c in data["cameras"]:
        evidence = [r for r in rows if r["camera_id"] == c["camera_id"]]
        if not evidence:
            lines.append(f"| {c['camera_id']:02d} | none recorded | missing evidence | unknown | n/a | n/a |")
        for r in evidence:
            replacement = r["overwritten_by_point_id"]
            lines.append(f"| {c['camera_id']:02d} | {r['observation_id']} / {r['keypoint_id']} | {r['status']} | "
                         f"{r['provenance']} | {r['error_sift_px']:.6f} / {r['error_original_px']:.6f} | "
                         f"{replacement if replacement >= 0 else 'none'} |")
    lines += ["", f"Set **{TIMELINE}** to any integer ID 0-385; all inspection views use that index.",
              "This index is not time or reconstruction stage. Clicking geometry does not change it.",
              "Cyan: active consistent; red: active inconsistent; purple: inactive evidence; orange: reprojection. Residual segments use observation-status colors.",
              "Missing evidence does not mean occlusion or a failed match; rejected matches were not exported.",
              "Activity describes the final snapshot. Inactive evidence is retained; replacement IDs use the final camera/keypoint map.",
              "Consistency means positive depth and <=3 SIFT px, independent of triangulation acceptance.",
              "Approximate intrinsics, no bundle adjustment, arbitrary scale. Small residuals do not prove correct 3D geometry."]
    return "\n\n".join(lines[:4]) + "\n\n" + "\n".join(lines[4:])


def make_inspection_blueprint(cameras):
    import rerun as rr
    import rerun.blueprint as b
    paths = [f"/world/cameras/view_{c['camera_id']:02d}" for c in cameras]
    spatial = b.Spatial3DView(origin="/world", name="RGB reconstruction and inspected ID",
                              contents=["/world/points/rgb", SELECTED,
                                        *[f"+ {p}/**" for p in paths],
                                        *[f"- {p}/image/inspection/**" for p in paths]])
    images = [b.Spatial2DView(origin=p + "/image", name=f"View {c['camera_id']:02d} · inspected observations",
                              contents=["$origin", "$origin/inspection/**"],
                              visual_bounds=b.VisualBounds2D(x_range=[0, c["original_size"]["width"]],
                                                             y_range=[0, c["original_size"]["height"]]))
              for p, c in zip(paths, cameras)]
    return b.Blueprint(
        b.Horizontal(spatial, b.Vertical(
            b.Vertical(b.Horizontal(*images[:2]), b.Horizontal(*images[2:])),
            b.Tabs(b.TextDocumentView(origin="/inspection/summary", name="ID, camera coverage and residuals"),
                   b.RawDataView(origin="/inspection/observations", name="Selected observation metadata",
                                 contents=["$origin"])), row_shares=[.7, .3]), column_shares=[.5, .5]),
        b.TimePanel(state="expanded", timeline=TIMELINE, play_state="paused", fps=1.,
                    time_selection=rr.encodings.AbsoluteTimeRange(min=rr.encodings.TimeInt(seq=0),
                                                                 max=rr.encodings.TimeInt(seq=385))),
        b.SelectionPanel(state="collapsed"), auto_layout=False, auto_views=False)


def log_observations(rec, path, rows):
    import rerun as rr
    # A recursive tombstone at every ID prevents stale markers in missing views.
    rec.log(path, rr.Clear(recursive=True))
    if not rows:
        return
    uv = np.array([r["observed"] for r in rows])
    projected = np.array([r["projected"] for r in rows])
    attrs = rr.AnyValues(**observation_attributes(rows))
    labels = [f"ID {r['point_id']} / obs {r['observation_id']} / {r['status']}" for r in rows]
    colors = [COLORS[r["status"]] for r in rows]
    ids = [r["point_id"] for r in rows]
    rec.log(path + "/observed", rr.Points2D(uv, colors=colors, radii=rr.Radius.ui_points(5),
                                            labels=labels, show_labels=True, keypoint_ids=ids), attrs)
    rec.log(path + "/projected", rr.Points2D(projected, colors=[255, 165, 45],
                                             radii=rr.Radius.ui_points(2), keypoint_ids=ids), attrs)
    rec.log(path + "/residuals", rr.LineStrips2D(np.stack([uv, projected], axis=1),
                                                colors=colors, radii=rr.Radius.ui_points(1)), attrs)


def export_inspection(canonical_dir, repository_root, output_dir):
    import rerun as rr
    require(rr.__version__ == SDK_VERSION, f"Use rerun-sdk=={SDK_VERSION}.")
    output = Path(output_dir)
    require(not output.exists(), "Output already exists; choose a fresh version directory.")
    data = load_reconstruction(canonical_dir, repository_root)
    records = observation_records(data)
    protected = {str(p): sha256(p) for p in data["folder"].iterdir() if p.is_file()}
    protected.update({str(data["root"] / i["path"]): sha256(data["root"] / i["path"])
                      for i in data["manifest"]["images"]})
    output.mkdir(parents=True, exist_ok=False)
    destination = output / "deku_inspection.rrd"
    with rr.RecordingStream("adversarial-vision-deku-inspection", recording_id="deku-canonical-v1-inspection-v02") as rec:
        rec.save(destination, default_blueprint=make_inspection_blueprint(data["cameras"]))
        rec.log("/world", rr.ViewCoordinates.RDF, static=True)
        for c in data["cameras"]:
            log_camera(rec, data, c, static=True)
        ids = data["arrays"]["point_ids"]
        rec.log("/world/points/rgb", rr.Points3D(data["arrays"]["xyz"], colors=data["arrays"]["rgb"],
                                               keypoint_ids=ids, labels=[f"ID {pid}" for pid in ids],
                                               show_labels=False, radii=rr.Radius.ui_points(2)),
                rr.AnyValues(**point_attributes(data, ids)), static=True)
        for pid in ids:
            pid = int(pid)
            rec.set_time(TIMELINE, sequence=pid)
            selected = [r for r in records if r["point_id"] == pid]
            rec.log(SELECTED, rr.Points3D(data["arrays"]["xyz"][[pid]], colors=[255, 240, 60],
                                         labels=[f"ID {pid}"], show_labels=True, keypoint_ids=[pid],
                                         radii=rr.Radius.ui_points(7)),
                    rr.AnyValues(**point_attributes(data, np.array([pid]))))
            for c in data["cameras"]:
                path = f"/world/cameras/view_{c['camera_id']:02d}/image/inspection"
                log_observations(rec, path, [r for r in selected if r["camera_id"] == c["camera_id"]])
            rec.log("/inspection/observations", rr.AnyValues(**observation_attributes(selected)))
            rec.log("/inspection/summary", rr.TextDocument(inspection_text(data, records, pid), media_type="text/markdown"))
        rec.flush()
    report = validate_inspection(destination, data)
    require(all(sha256(p) == h for p, h in protected.items()), "Canonical data or photographs changed.")
    report.update(sdk_version=rr.__version__, python=platform.python_version(),
                  recording=destination.name, recording_bytes=destination.stat().st_size,
                  recording_sha256=sha256(destination),
                  canonical_files_sha256={p.name: sha256(p) for p in data["folder"].iterdir() if p.is_file()},
                  exporter_source_sha256={name: sha256(data["root"] / name) for name in
                                          ["src/rerun_inspection.py", "src/rerun_reconstruction.py",
                                           "src/canonical_reconstruction.py", "scripts/export_rerun_inspection.py"]},
                  original_images_unchanged=True, canonical_unchanged=True,
                  interaction="ID-indexed timeline; no click-to-ID selection callback",
                  visual_inspection="not performed; serialized data and blueprint validated")
    write_json(output / "validation.json", report)
    return report


def validate_inspection(path, data):
    """Validate serialized 3D, images, transforms and every 2D evidence row."""
    rows = read_recording(path)
    expected = observation_records(data)
    cloud = next(r for r in rows["/world/points/rgb"] if r.get("Points3D:positions") is not None)
    ids = data["arrays"]["point_ids"].tolist()
    require(cloud["point_id"] == ids and cloud["Points3D:keypoint_ids"] == ids, "Canonical point ID mismatch.")
    require(np.array_equal(np.array(cloud["Points3D:positions"], dtype=np.float32), data["arrays"]["xyz"]), "Cloud XYZ mismatch.")
    colors = np.array(cloud["Points3D:colors"], dtype=np.uint32)
    rgb = np.column_stack([(colors >> shift) & 255 for shift in [24, 16, 8]]).astype(np.uint8)
    require(np.array_equal(rgb, data["arrays"]["rgb"]), "Cloud RGB mismatch.")
    require(TIMELINE not in cloud, "Context cloud must be static.")
    selected = [r for r in rows[SELECTED] if r.get("Points3D:positions") is not None]
    require(sorted(r[TIMELINE] for r in selected) == ids, "Missing inspection steps.")
    for r in selected:
        pid = r[TIMELINE]
        require(r["point_id"] == r["Points3D:keypoint_ids"] == [pid], "Selected point ID mismatch.")
        require(np.array_equal(np.array(r["Points3D:positions"], dtype=np.float32), data["arrays"]["xyz"][[pid]]), "Selected XYZ mismatch.")
        for field, value in point_attributes(data, np.array([pid])).items():
            require(r[field] == value.tolist(), f"Selected metric mismatch: {field}.")
    seen, missing = [], 0
    for c in data["cameras"]:
        base = f"/world/cameras/view_{c['camera_id']:02d}"
        pose = next(r for r in rows[base] if r.get("Transform3D:mat3x3") is not None)
        R = np.array(pose["Transform3D:mat3x3"][0]).reshape(3, 3, order="F")
        require(np.allclose(R, np.array(c["T_camera_to_world"])[:3, :3], rtol=0, atol=1e-7), "Camera rotation mismatch.")
        require(np.allclose(pose["Transform3D:translation"][0], c["center_world"], rtol=0, atol=2e-7)
                and pose["Transform3D:relation"] == [1], "Camera translation/convention mismatch.")
        image = next(r for r in rows[base + "/image"] if r.get("EncodedImage:blob") is not None)
        require(bytes(image["EncodedImage:blob"][0]) == (data["root"] / c["image_path"]).read_bytes(), "Original image mismatch.")
        K = np.array(image["Pinhole:image_from_camera"][0]).reshape(3, 3, order="F")
        require(np.allclose(K, c["K_original"], rtol=0, atol=1e-4), "Image intrinsics mismatch.")
        require(image["Pinhole:resolution"] == [[c["original_size"]["width"], c["original_size"]["height"]]], "Image size mismatch.")
        evidence = base + "/image/inspection"
        clears = [r for r in rows[evidence] if r.get("Clear:is_recursive") == [True]]
        require(sorted(r[TIMELINE] for r in clears) == ids, "Missing recursive clear; stale evidence possible.")
        for pid in ids:
            wanted = [r for r in expected if r["camera_id"] == c["camera_id"] and r["point_id"] == pid]
            for layer in ["observed", "projected", "residuals"]:
                actual = [r for r in rows.get(evidence + "/" + layer, []) if r.get(TIMELINE) == pid]
                require(len(actual) == bool(wanted), "Missing or stale 2D evidence.")
                if not wanted:
                    continue
                sample = actual[0]
                for field, value in observation_attributes(wanted).items():
                    require(sample[field] == value.tolist(), f"Observation metadata mismatch: {field}.")
                a, b = np.array([r["observed"] for r in wanted]), np.array([r["projected"] for r in wanted])
                positions = np.stack([a, b], axis=1) if layer == "residuals" else (a if layer == "observed" else b)
                component = "LineStrips2D:strips" if layer == "residuals" else "Points2D:positions"
                require(np.allclose(sample[component], positions, rtol=0, atol=1e-4), "Serialized overlay coordinate mismatch.")
                if layer != "residuals":
                    require(sample["Points2D:keypoint_ids"] == [pid] * len(wanted), "2D canonical IDs mismatch.")
            seen.extend(r["observation_id"] for r in wanted)
            missing += not bool(wanted)
    require(sorted(seen) == list(range(len(expected))), "Observation coverage mismatch.")
    return dict(point_ids=len(ids), unique_positions=len(np.unique(data["arrays"]["xyz"], axis=0)),
                observation_rows=len(seen), cameras=4, missing_point_camera_pairs=int(missing),
                observation_status_counts=dict(Counter(r["status"] for r in expected)),
                overwritten_observations=sum(r["overwritten_by_point_id"] >= 0 for r in expected),
                examples=[{k: r[k] for k in ("point_id", "observation_id", "camera_id", "status", "provenance", "error_sift_px", "error_original_px")}
                          for oid in [0, 782, 460, 582] for r in expected if r["observation_id"] == oid])
