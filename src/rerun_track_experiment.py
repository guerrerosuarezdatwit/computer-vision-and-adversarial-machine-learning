"""Rerun 0.42 recording for Experiment 02; frozen geometry, five gate policies."""
from pathlib import Path

import numpy as np

from src.canonical_reconstruction import project, require, validate_export
from src.rerun_reconstruction import SDK_VERSION, log_camera, read_recording

TIMELINE = "gate_variant"


def attributes(decisions):
    types = dict(observation_id=np.int64, point_id=np.int64, camera_id=np.int64,
                 keypoint_id=np.int64, stage=np.int64, source_camera_id=np.int64,
                 source_keypoint_id=np.int64, accepted=bool, action=str,
                 rejection_reasons=str, error_sift_px=np.float64, depth_camera=np.float64)
    return {k: np.array([r[k] for r in decisions], dtype=t) for k, t in types.items()}


def coordinates(rows, camera):
    scale = np.asarray(camera["scale_original_to_sift"])
    observed = np.array([r["observed_sift"] for r in rows]).reshape(-1, 2) / scale
    predicted = np.array([r["projected_sift"] for r in rows]).reshape(-1, 2) / scale
    return observed, predicted


def log_associations(rec, path, decisions, camera, color, *, static=False):
    import rerun as rr
    rec.log(path, rr.Clear(recursive=True), static=static)
    if not decisions:
        return
    observed, predicted = coordinates(decisions, camera)
    meta = rr.AnyValues(**attributes(decisions))
    labels = [f"ID {r['point_id']} / obs {r['observation_id']}" for r in decisions]
    ids = [r["point_id"] for r in decisions]
    rec.log(path + "/observed", rr.Points2D(observed, colors=color, labels=labels,
                                            show_labels=False, keypoint_ids=ids, radii=rr.Radius.ui_points(4)),
            meta, static=static)
    rec.log(path + "/projected", rr.Points2D(predicted, colors=[255, 165, 45],
                                             keypoint_ids=ids, radii=rr.Radius.ui_points(2)), meta, static=static)
    rec.log(path + "/residuals", rr.LineStrips2D(np.stack([observed, predicted], axis=1),
                                                colors=color, radii=rr.Radius.ui_points(.8)), meta, static=static)


def experiment_blueprint(data):
    import rerun.blueprint as b
    cameras = data["cameras"]
    camera_paths = [f"/world/cameras/view_{c['camera_id']:02d}" for c in cameras]
    spatial = b.Spatial3DView(origin="/world", name="Frozen RGB map and propagation decisions",
                              contents=["/world/points/**", "/world/candidates/**",
                                        *[f"+ {p}/**" for p in camera_paths],
                                        *[f"- {p}/image/baseline/**" for p in camera_paths],
                                        *[f"- {p}/image/filtered/**" for p in camera_paths]])
    pairs = []
    for p, c in zip(camera_paths, cameras):
        bounds = b.VisualBounds2D(x_range=[0, c["original_size"]["width"]], y_range=[0, c["original_size"]["height"]])
        pairs.append(b.Horizontal(
            b.Spatial2DView(origin=p + "/image", name=f"View {c['camera_id']:02d} baseline · all proposals",
                            contents=["$origin", "$origin/baseline/**"], visual_bounds=bounds),
            b.Spatial2DView(origin=p + "/image", name=f"View {c['camera_id']:02d} policy · green kept / red rejected",
                            contents=["$origin", "$origin/filtered/**"], visual_bounds=bounds),
            name=f"Camera {c['camera_id']:02d}"))
    return b.Blueprint(
        b.Horizontal(spatial, b.Vertical(b.Tabs(*pairs, active_tab=3),
                       b.Tabs(b.TextDocumentView(origin="/experiment/summary", name="Threshold comparison and limitations"),
                              b.RawDataView(origin="/experiment/associations", name="All 34 proposal decisions",
                                            contents=["$origin"])), row_shares=[.7, .3]), column_shares=[.35, .65]),
        b.TimePanel(state="expanded", timeline=TIMELINE, play_state="paused", fps=1.),
        b.SelectionPanel(state="collapsed"), auto_layout=False, auto_views=False)


def summary_text(report, index):
    current = report["variants"][index]
    lines = [f"# Experiment 02 · {index}: {current['variant']}", "",
             "Fixed final poses and fixed proposal universe; **not an end-to-end SfM comparison**.", "",
             "| Step | Policy | Proposed | Kept | Rejected | Kept median / max SIFT px | Active evidence | Tracks >=3 cameras |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i, row in enumerate(report["variants"]):
        e, c = row["accepted_errors"], row["retained_final_coverage"]
        lines.append(f"| {i} | {row['variant']} | {row['proposed']} | {row['accepted']} | {row['rejected']} | "
                     f"{e['median']:.3f} / {e['max']:.3f} | {c['associations']} | {c['points_with_at_least_three_cameras']} |")
    lines += ["", f"Choose **{TIMELINE}** 0-4. Left image: fixed cyan baseline. Right: green kept / red rejected; small orange dots are predictions.",
              "Click/hover markers for original point and observation IDs, residuals and rejection reasons. No click synchronization is implemented.",
              "Point 162 / View 06 / obs 782: propagated residual 540.904 SIFT px (692.358 original px); rejected by every tested gate.",
              "Point 278 / View 06 / obs 810: propagated residual 0.354187 SIFT px; kept by every policy. Low residual is not ground truth.",
              "Point 62 / View 06 / obs 460: PnP residual 3.462303 SIFT px, outside this propagation-only gate; remains inconsistent.",
              "All 386 original point IDs, 364 distinct XYZ positions and four camera poses remain fixed. The five inactive historical observations are untouched.",
              "Blank image overlays mean no recorded PROPAGATION proposal, not no observations at all. Error units are SIFT 900x1200; overlays use original 1152x1536.",
              "Baseline disables geometry verification; green means retained by policy, not a scientifically verified match.",
              "No PnP or triangulation was rerun; retained evidence coverage is not improved reconstruction coverage.",
              *report["limitations"]]
    return "\n\n".join(lines[:3]) + "\n\n" + "\n".join(lines[3:])


def export_track_recording(data, report, decisions, destination, repository_root):
    import rerun as rr
    require(rr.__version__ == SDK_VERSION, f"Use rerun-sdk=={SDK_VERSION}.")
    root, destination = Path(repository_root), Path(destination)
    require(not destination.exists(), "Recording already exists.")
    validate_export(data["folder"], root)  # Original image hashes/dimensions too.
    scene = dict(data, root=root)
    baseline = [r for r in decisions if r["variant"] == "baseline"]
    with rr.RecordingStream("adversarial-vision-experiment-02", recording_id="track-verification-exp02-v1") as rec:
        rec.save(destination, default_blueprint=experiment_blueprint(data))
        rec.log("/world", rr.ViewCoordinates.RDF, static=True)
        ids = data["arrays"]["point_ids"]
        rec.log("/world/points/rgb", rr.Points3D(data["arrays"]["xyz"], colors=data["arrays"]["rgb"],
                                               keypoint_ids=ids, radii=rr.Radius.ui_points(2)),
                rr.AnyValues(point_id=ids), static=True)
        for c in data["cameras"]:
            log_camera(rec, scene, c, static=True)
            path = f"/world/cameras/view_{c['camera_id']:02d}/image/baseline"
            log_associations(rec, path, [r for r in baseline if r["camera_id"] == c["camera_id"]],
                             c, [40, 210, 230], static=True)
        for index, variant in enumerate(report["variants"]):
            rec.set_time(TIMELINE, sequence=index)
            current = [r for r in decisions if r["variant"] == variant["variant"]]
            for c in data["cameras"]:
                base = f"/world/cameras/view_{c['camera_id']:02d}/image/filtered"
                for name, keep, color in [("accepted", True, [50, 210, 130]), ("rejected", False, [245, 65, 65])]:
                    selected = [r for r in current if r["camera_id"] == c["camera_id"] and r["accepted"] == keep]
                    log_associations(rec, base + "/" + name, selected, c, color)
            for name, keep, color in [("accepted", True, [50, 210, 130]), ("rejected", False, [245, 65, 65])]:
                path = "/world/candidates/" + name
                rec.log(path, rr.Clear(recursive=True))
                selected = [r for r in current if r["accepted"] == keep]
                if selected:
                    ids = [r["point_id"] for r in selected]
                    rec.log(path, rr.Points3D(data["arrays"]["xyz"][ids], colors=color, keypoint_ids=ids,
                                              radii=rr.Radius.ui_points(4)), rr.AnyValues(**attributes(selected)))
            rec.log("/experiment/associations", rr.AnyValues(**attributes(current)))
            rec.log("/experiment/summary", rr.TextDocument(summary_text(report, index), media_type="text/markdown"))
        rec.flush()
    return validate_track_recording(destination, data, report, decisions, root)


def validate_track_recording(path, data, report, decisions, root):
    rows = read_recording(path)
    cloud = next(r for r in rows["/world/points/rgb"] if r.get("Points3D:positions") is not None)
    require(cloud["point_id"] == data["arrays"]["point_ids"].tolist(), "Cloud IDs changed.")
    require(np.array_equal(np.array(cloud["Points3D:positions"], dtype=np.float32), data["arrays"]["xyz"]), "Cloud XYZ changed.")
    color = np.asarray(cloud["Points3D:colors"], dtype=np.uint32)
    rgb = np.column_stack([(color >> shift) & 255 for shift in [24, 16, 8]]).astype(np.uint8)
    require(np.array_equal(rgb, data["arrays"]["rgb"]), "Cloud RGB changed.")
    checked = 0
    for c in data["cameras"]:
        p = f"/world/cameras/view_{c['camera_id']:02d}"
        pose = next(r for r in rows[p] if r.get("Transform3D:mat3x3") is not None)
        R = np.array(pose["Transform3D:mat3x3"][0]).reshape(3, 3, order="F")
        require(np.allclose(R, np.array(c["R_world_to_camera"]).T, atol=1e-7, rtol=0)
                and np.allclose(pose["Transform3D:translation"][0], c["center_world"], atol=2e-7, rtol=0)
                and pose["Transform3D:relation"] == [1], "Camera pose changed.")
        image = next(r for r in rows[p + "/image"] if r.get("EncodedImage:blob") is not None)
        require(bytes(image["EncodedImage:blob"][0]) == (Path(root) / c["image_path"]).read_bytes(), "Photograph bytes changed.")
        K = np.array(image["Pinhole:image_from_camera"][0]).reshape(3, 3, order="F")
        require(np.allclose(K, c["K_original"], rtol=0, atol=1e-4), "Image intrinsics changed.")
        require(image["Pinhole:resolution"] == [[c["original_size"]["width"], c["original_size"]["height"]]], "Image size changed.")
        baseline = [r for r in decisions if r["variant"] == "baseline" and r["camera_id"] == c["camera_id"]]
        observed = [r for r in rows.get(p + "/image/baseline/observed", []) if r.get("Points2D:positions") is not None]
        require(len(observed) == bool(baseline), "Baseline overlay coverage differs.")
        if baseline:
            require(TIMELINE not in observed[0], "Baseline overlay must be static.")
            for field, value in attributes(baseline).items():
                require(observed[0][field] == value.tolist(), "Baseline metadata differs.")
            require(np.allclose(observed[0]["Points2D:positions"], coordinates(baseline, c)[0], rtol=0, atol=1e-4), "Baseline pixels differ.")
        for index, variant in enumerate(report["variants"]):
            for layer, keep in [("accepted", True), ("rejected", False)]:
                wanted = [r for r in decisions if r["variant"] == variant["variant"]
                          and r["camera_id"] == c["camera_id"] and r["accepted"] == keep]
                base = p + "/image/filtered/" + layer
                require(any(r.get(TIMELINE) == index and r.get("Clear:is_recursive") == [True]
                            for r in rows[base]), "Missing stale-marker clear.")
                for primitive, component in [("observed", "Points2D:positions"), ("projected", "Points2D:positions"),
                                             ("residuals", "LineStrips2D:strips")]:
                    samples = [r for r in rows.get(base + "/" + primitive, []) if r.get(TIMELINE) == index]
                    require(len(samples) == bool(wanted), "Policy overlay count mismatch.")
                    if not wanted:
                        continue
                    sample = samples[0]
                    for field, value in attributes(wanted).items():
                        require(sample[field] == value.tolist(), f"Decision metadata changed: {field}.")
                    a, b = coordinates(wanted, c)
                    direct, _ = project(data["arrays"]["xyz"][[r["point_id"] for r in wanted]],
                                        c["R_world_to_camera"], c["t_world_to_camera"], c["K_original"])
                    require(np.allclose(b, direct, rtol=0, atol=1e-9), "Original/SIFT projection scaling differs.")
                    expected = np.stack([a, b], axis=1) if primitive == "residuals" else (a if primitive == "observed" else b)
                    require(np.allclose(sample[component], expected, rtol=0, atol=1e-4), "Overlay coordinate mismatch.")
                    if primitive != "residuals":
                        require(sample["Points2D:keypoint_ids"] == [r["point_id"] for r in wanted], "2D IDs changed.")
                    if primitive == "observed":
                        checked += len(wanted)
    require(checked == len(decisions), "Serialized decision coverage differs.")
    for index, variant in enumerate(report["variants"]):
        wanted = [r for r in decisions if r["variant"] == variant["variant"]]
        table = next(r for r in rows["/experiment/associations"] if r.get(TIMELINE) == index)
        for field, value in attributes(wanted).items():
            require(table[field] == value.tolist(), "Serialized decision table differs.")
        for layer, keep in [("accepted", True), ("rejected", False)]:
            group = [r for r in wanted if r["accepted"] == keep]
            samples = [r for r in rows["/world/candidates/" + layer]
                       if r.get(TIMELINE) == index and r.get("Points3D:positions") is not None]
            require(len(samples) == bool(group), "3D candidate coverage differs.")
            if group:
                require(samples[0]["point_id"] == [r["point_id"] for r in group], "3D candidate IDs changed.")
                require(np.array_equal(np.array(samples[0]["Points3D:positions"], dtype=np.float32),
                                       data["arrays"]["xyz"][[r["point_id"] for r in group]]), "3D candidate XYZ changed.")
    return dict(variants=5, serialized_association_decisions=checked, original_point_ids=386,
                cameras=4, original_photographs=4, original_rgb_xyz_exact=True,
                overlay_tolerance_original_px=1e-4,
                visual_inspection="not performed; actual RRD readback and blueprint serialization tested")
