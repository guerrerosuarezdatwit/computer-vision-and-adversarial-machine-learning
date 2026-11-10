"""Rerun 0.42 proof of concept reading the canonical export, never running SfM."""
import importlib.metadata
import json
from pathlib import Path
import platform

import numpy as np

from src.canonical_reconstruction import project, read_csv, require, sha256, validate_export, write_json


SDK_VERSION = "0.42.0"
POINT_PATHS = {"rgb": "/world/points/rgb", "accepted": "/world/points/accepted",
               "rejected": "/world/points/rejected"}


def load_reconstruction(canonical_dir, repository_root):
    """Validate all five canonical artifacts and keep original ID ordering."""
    folder, root = Path(canonical_dir), Path(repository_root)
    validate_export(folder, root)
    manifest = json.loads((folder / "manifest.json").read_text())
    with np.load(folder / "points.npz", allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in archive.files}
    metrics = read_csv(folder / "metrics.csv")
    threshold = manifest["diagnostic_thresholds"]
    accepted = []
    for row in metrics:
        # Re-evaluate the recorded diagnostic policy, including its original
        # association-count semantics. Do not introduce a new SfM filter.
        fields = [float(row[f]) for f in ("effective_angle_deg", "depth_a", "depth_b", "max_error_px", "depth_baselines")]
        angle, za, zb, error, depth = fields
        keep = (np.isfinite(fields).all() and za > 0 and zb > 0
                and angle >= threshold["min_angle"] and error <= threshold["max_error"]
                and depth <= threshold["max_depth_baselines"])
        if threshold["check_associations"]:
            keep &= (int(row["associated_observations"]) >= 2
                     and np.isfinite(float(row["associated_max_error_px"]))
                     and float(row["associated_max_error_px"]) <= threshold["max_error"]
                     and float(row["associated_min_depth"]) > 0)
        require(bool(keep) == (row["accepted"] == "True"), "Recorded diagnostic classification differs from recorded settings.")
        accepted.append(bool(keep))
    return dict(root=root, folder=folder, manifest=manifest, arrays=arrays, metrics=metrics,
                accepted=np.array(accepted), cameras=json.loads((folder / "cameras.json").read_text())["cameras"],
                observations=read_csv(folder / "observations.csv"))


def stage_masks(data, stage):
    available = data["arrays"]["stage"] <= stage
    return {"rgb": available, "accepted": available & data["accepted"],
            "rejected": available & ~data["accepted"]}


def point_attributes(data, ids):
    """Original IDs stay explicit even when a rendered layer uses subset indices."""
    metrics = [data["metrics"][int(pid)] for pid in ids]
    duplicates = {pid: ",".join(map(str, group))
                  for group in data["manifest"]["anomalies"]["duplicate_position_groups"] for pid in group}
    return dict(
        point_id=np.asarray(ids, dtype=np.int64), birth_stage=data["arrays"]["stage"][ids],
        accepted=data["accepted"][ids],
        angle_deg=np.array([float(r["effective_angle_deg"]) for r in metrics], dtype=np.float64),
        depth_baselines=np.array([float(r["depth_baselines"]) for r in metrics], dtype=np.float64),
        max_error_px=np.array([float(r["max_error_px"]) for r in metrics], dtype=np.float64),
        associated_max_error_px=np.array([float(r["associated_max_error_px"]) for r in metrics], dtype=np.float64),
        rejection_reasons=np.array([r["rejection_reasons"] for r in metrics], dtype=str),
        duplicate_ids=np.array([duplicates.get(int(pid), "") for pid in ids], dtype=str),
    )


def make_blueprint(cameras):
    import rerun.blueprint as rrb
    camera_paths = [f"/world/cameras/view_{c['camera_id']:02d}" for c in cameras]
    camera_contents = [f"+ {p}/**" for p in camera_paths]
    camera_contents += [f"- {p}/image/evidence/**" for p in camera_paths]
    rgb = rrb.Spatial3DView(origin="/world", name="Original RGB · preserved geometry",
                           contents=[POINT_PATHS["rgb"], *camera_contents])
    geometric = rrb.Spatial3DView(origin="/world", name="Diagnostic layers · accepted / rejected",
                                 contents=[POINT_PATHS["accepted"], POINT_PATHS["rejected"], *camera_contents])
    images = [rrb.Spatial2DView(origin=f"{path}/image", name=f"View {c['camera_id']:02d}",
                               contents=["$origin/**"])
              for path, c in zip(camera_paths, cameras)]
    diagnostics = rrb.Tabs(
        rrb.TextDocumentView(origin="/diagnostics/summary", name="Stage and scientific notes"),
        rrb.DataframeView(origin="/diagnostics/point_metrics", name="Point IDs and metrics (birth events)",
                          contents=["$origin/**"],
                          query=rrb.archetypes.DataframeQuery(timeline="stage", auto_scroll=True)),
        name="Diagnostics")
    return rrb.Blueprint(
        rrb.Horizontal(rrb.Tabs(rgb, geometric, active_tab=0),
                       rrb.Vertical(rrb.Tabs(*images, active_tab=1), diagnostics, row_shares=[.65, .35]),
                       column_shares=[.68, .32]),
        rrb.TimePanel(state="expanded", timeline="stage", fps=1., play_state="paused"),
        rrb.SelectionPanel(state="collapsed"), auto_layout=False, auto_views=False)


def stage_text(data, stage):
    masks = stage_masks(data, stage["stage"])
    thresholds = data["manifest"]["diagnostic_thresholds"]
    return f"""# Deku · stage {stage['stage']}: {stage['name']}

**Point IDs:** {int(masks['rgb'].sum())} · **accepted:** {int(masks['accepted'].sum())} · **rejected:** {int(masks['rejected'].sum())}

**Registered cameras:** {', '.join(map(str, stage['registered_camera_ids']))}

Use the two 3D tabs to compare original RGB with green accepted / red rejected layers.
Use the camera tabs to inspect original photographs; cyan marks observed pixels,
orange marks reprojections and residual segments. Click a point to inspect its
original ID and metrics in Selection. Overlapping duplicates remain separate IDs;
use the metrics table to distinguish them. Its rows are birth events over the full
recording, not a live count of only the current stage.

Recorded filters: angle ≥ {thresholds['min_angle']}°, maximum birth-pair error ≤ {thresholds['max_error']} px,
depth ≤ {thresholds['max_depth_baselines']} baselines. Association filtering: {thresholds['check_associations']}.
Error values remain in 900×1200 SIFT pixels; displayed images and overlays use
1152×1536 pixels with K_original. Filter results are fixed, not recalculated by the Viewer.

## Final snapshot audit (not intermediate track state)
386 original IDs, 364 distinct positions, 21 duplicate groups; all preserved.
Known high-error final associations involve IDs 62, 140, 161, 162, 192, 232, 295;
the maximum error is approximately 540.904 SIFT px. Red evidence denotes final
active propagated associations exceeding 3 px. Historical overwritten evidence
remains marked inactive in metadata, not silently removed.

Approximate intrinsics; no distortion correction or bundle adjustment; no metric
scale or ground truth. Eight original images have no poses. Evidence appears from
its recorded creation stage, but final-map activity is only known for the final
snapshot. **A recording is a visualization of existing results, not proof of
correct reconstruction. Low reprojection error does not establish reliable depth.**
"""


def log_camera(rec, data, camera, *, static=False):
    import rerun as rr
    cid = camera["camera_id"]
    path = f"/world/cameras/view_{cid:02d}"
    T = np.array(camera["T_camera_to_world"])
    rec.log(path, rr.Transform3D(mat3x3=T[:3, :3], translation=T[:3, 3],
                                relation=rr.TransformRelation.ParentFromChild),
            rr.TransformAxes3D(.2), rr.AnyValues(camera_id=cid), static=static)
    size = camera["original_size"]
    rec.log(path + "/image", rr.Pinhole(image_from_camera=camera["K_original"],
                                       resolution=[size["width"], size["height"]],
                                       camera_xyz=rr.ViewCoordinates.RDF,
                                       image_plane_distance=.28),
            rr.EncodedImage(path=data["root"] / camera["image_path"]), static=static)


def log_evidence(rec, data, camera, stage):
    import rerun as rr
    rows = [r for r in data["observations"] if int(r["camera_id"]) == camera["camera_id"] and int(r["stage"]) <= stage]
    path = f"/world/cameras/view_{camera['camera_id']:02d}/image/evidence"
    uv = np.array([[float(r["u_original"]), float(r["v_original"])] for r in rows]).reshape(-1, 2)
    scale = np.array(camera["scale_original_to_sift"])
    projected = np.array([[float(r["projected_u_sift"]), float(r["projected_v_sift"])] for r in rows]).reshape(-1, 2) / scale
    bad = [r["provenance"] == "descriptor_propagation" and r["active_in_final_map"] == "True"
           and float(r["reprojection_error_px"]) > 3 for r in rows]
    colors = np.array([[240, 65, 65] if b else [40, 210, 230] for b in bad], dtype=np.uint8).reshape(-1, 3)
    attrs = rr.AnyValues(point_id=np.array([int(r["point_id"]) for r in rows], dtype=np.int64),
                         observation_id=np.array([int(r["observation_id"]) for r in rows], dtype=np.int64),
                         provenance=np.array([r["provenance"] for r in rows], dtype=str),
                         active_in_final_map=np.array([r["active_in_final_map"] == "True" for r in rows]),
                         error_sift_px=np.array([float(r["reprojection_error_px"]) for r in rows]))
    labels = [f"ID {r['point_id']} · obs {r['observation_id']}" for r in rows]
    rec.log(path + "/observed", rr.Points2D(uv, colors=colors, radii=rr.Radius.ui_points(2.5),
                                            labels=labels, show_labels=False), attrs)
    rec.log(path + "/projected", rr.Points2D(projected, colors=[255, 160, 55], radii=rr.Radius.ui_points(1.5),
                                             labels=labels, show_labels=False), attrs)
    rec.log(path + "/residuals", rr.LineStrips2D(np.stack([uv, projected], axis=1),
                                                colors=[255, 160, 55], radii=rr.Radius.ui_points(.5)), attrs)


def export_recording(canonical_dir, repository_root, output_dir):
    import rerun as rr
    require(rr.__version__ == SDK_VERSION, f"Use pinned rerun-sdk=={SDK_VERSION}.")
    output = Path(output_dir)
    require(not output.exists(), "Output already exists; choose a new version directory.")
    data = load_reconstruction(canonical_dir, repository_root)
    source_hashes = {p.name: sha256(p) for p in data["folder"].iterdir() if p.is_file()}
    image_hashes = {image["path"]: sha256(data["root"] / image["path"]) for image in data["manifest"]["images"]}
    output.mkdir(parents=True, exist_ok=False)
    destination = output / "deku_reconstruction.rrd"
    with rr.RecordingStream("adversarial-vision-deku", recording_id="deku-canonical-v1-rerun-poc-v1") as rec:
        rec.save(destination, default_blueprint=make_blueprint(data["cameras"]))
        rec.log("/world", rr.ViewCoordinates.RDF, static=True)
        for stage in data["manifest"]["stages"]:
            s = stage["stage"]
            rec.set_time("stage", sequence=s)
            for camera in data["cameras"]:
                if camera["registration_stage"] == s:
                    log_camera(rec, data, camera)
                if camera["registration_stage"] <= s:
                    log_evidence(rec, data, camera, s)
            masks = stage_masks(data, s)
            for layer, mask in masks.items():
                ids = data["arrays"]["point_ids"][mask]
                colors = data["arrays"]["rgb"][mask] if layer == "rgb" else ([55, 205, 140] if layer == "accepted" else [245, 75, 75])
                rec.log(POINT_PATHS[layer], rr.Points3D(data["arrays"]["xyz"][mask], colors=colors,
                                                      radii=rr.Radius.ui_points(3), labels=[f"ID {pid}" for pid in ids],
                                                      show_labels=False, keypoint_ids=ids),
                        rr.AnyValues(**point_attributes(data, ids)))
            for pid in np.flatnonzero(data["arrays"]["stage"] == s):
                rec.log(f"/diagnostics/point_metrics/{pid:03d}", rr.AnyValues(**point_attributes(data, np.array([pid]))))
            rec.log("/diagnostics/summary", rr.TextDocument(stage_text(data, stage), media_type="text/markdown"))
        rec.flush()
    validation = validate_recording(destination, data)
    require(source_hashes == {p.name: sha256(p) for p in data["folder"].iterdir() if p.is_file()}, "Canonical artifacts changed.")
    require(all(sha256(data["root"] / path) == digest for path, digest in image_hashes.items()), "Original images changed.")
    report = dict(sdk_version=rr.__version__, python=platform.python_version(),
                  platform=platform.platform(), recording=destination.name, recording_sha256=sha256(destination),
                  recording_bytes=destination.stat().st_size, canonical_files_sha256=source_hashes,
                  images_sha256=image_hashes, canonical_unchanged=True, original_images_unchanged=True,
                  validation=validation,
                  environment={name: importlib.metadata.version(name) for name in
                               ["rerun-sdk", "numpy", "Pillow", "pyarrow", "attrs", "psutil", "typing_extensions"]},
                  visual_inspection="not yet performed; numerical and RRD readback validation only",
                  limitations=data["manifest"]["limitations"] + [
                      "Fixed diagnostic classifications, not interactive threshold recomputation.",
                      "Metrics table contains birth events over the recording; it is not a current-stage point counter.",
                      "Semantic click-to-ID synchronization across arbitrary views is not implemented."])
    write_json(output / "validation.json", report)
    return report


def read_recording(path):
    """Read actual serialized Arrow batches, not the inputs passed to the logger."""
    from rerun.chunk import RrdReader
    reader = RrdReader(path)
    require(len(reader.recordings()) == 1, "Expected one reconstruction recording.")
    require(len(reader.blueprints()) >= 1, "Default layout blueprint is absent.")
    result = {}
    for chunk in reader.stream(store=reader.recordings()[0]):
        batch = chunk.to_record_batch().to_pydict()
        for i in range(chunk.num_rows):
            result.setdefault(chunk.entity_path, []).append({k: v[i] for k, v in batch.items()})
    return result


def validate_recording(path, data):
    rows = read_recording(path)
    stages = []
    for stage in data["manifest"]["stages"]:
        s = stage["stage"]
        counts = {}
        for layer, mask in stage_masks(data, s).items():
            samples = [r for r in rows[POINT_PATHS[layer]] if r.get("stage") == s and r.get("Points3D:positions") is not None]
            require(len(samples) == 1, "Expected exactly one complete point-layer update per stage.")
            sample = samples[0]
            ids = data["arrays"]["point_ids"][mask]
            require(sample["point_id"] == ids.tolist(), "RRD point IDs differ from canonical IDs.")
            actual = np.asarray(sample["Points3D:positions"], dtype=np.float32).reshape(-1, 3)
            require(np.array_equal(actual, data["arrays"]["xyz"][mask]), "RRD geometry differs from canonical XYZ.")
            require(sample["accepted"] == data["accepted"][mask].tolist(), "RRD classifications differ.")
            if layer == "rgb":
                colors = np.array(sample["Points3D:colors"], dtype=np.uint32)
                decoded = np.column_stack([(colors >> shift) & 255 for shift in [24, 16, 8]]).astype(np.uint8)
                require(np.array_equal(decoded, data["arrays"]["rgb"][mask]), "RRD RGB differs from canonical samples.")
            counts[layer] = len(ids)
        require(counts["rgb"] == stage["point_count"] and counts["accepted"] + counts["rejected"] == counts["rgb"], "Stage counts differ.")
        stages.append(dict(stage=s, **counts))
    for c in data["cameras"]:
        path = f"/world/cameras/view_{c['camera_id']:02d}"
        transform = next(r for r in rows[path] if r.get("Transform3D:mat3x3") is not None)
        require(transform["stage"] == c["registration_stage"], "Camera appears at the wrong stage.")
        # Rerun's matrices are serialized column-major as float32.
        rotation = np.asarray(transform["Transform3D:mat3x3"][0]).reshape(3, 3, order="F")
        translation = np.array(transform["Transform3D:translation"][0])
        T = np.array(c["T_camera_to_world"])
        require(np.allclose(rotation, T[:3, :3], rtol=0, atol=1e-7) and np.allclose(translation, T[:3, 3], rtol=0, atol=2e-7), "Serialized camera-to-world pose differs.")
        require(transform["Transform3D:relation"] == [1], "Transform relation must be ParentFromChild.")
        pinhole = next(r for r in rows[path + "/image"] if r.get("Pinhole:image_from_camera") is not None)
        K = np.array(pinhole["Pinhole:image_from_camera"][0]).reshape(3, 3, order="F")
        require(np.allclose(K, c["K_original"], rtol=0, atol=1e-4), "Serialized intrinsics do not match original image size.")
        image = next(r for r in rows[path + "/image"] if r.get("EncodedImage:blob") is not None)
        require(bytes(image["EncodedImage:blob"][0]) == (data["root"] / c["image_path"]).read_bytes(), "Embedded JPEG differs from original photograph.")
        evidence_path = path + "/image/evidence/observed"
        final = next(r for r in rows[evidence_path] if r.get("stage") == 4 and r.get("Points2D:positions") is not None)
        expected = [r for r in data["observations"] if int(r["camera_id"]) == c["camera_id"]]
        require(final["observation_id"] == [int(r["observation_id"]) for r in expected], "RRD observation provenance coverage differs.")
        require(np.allclose(np.array(final["Points2D:positions"]), [[float(r["u_original"]), float(r["v_original"])] for r in expected], rtol=0, atol=1e-4), "RRD observed pixels have the wrong resolution.")
        projected, _ = project(data["arrays"]["xyz"], rotation.T, -rotation.T @ translation, K)
        reference, _ = project(data["arrays"]["xyz"], c["R_world_to_camera"], c["t_world_to_camera"], c["K_original"])
        require(np.max(np.abs(projected - reference)) < .001, "Float32 Rerun transforms produce inconsistent camera projections.")
    final = next(r for r in rows[POINT_PATHS["rgb"]] if r.get("stage") == 4)
    unique = len(np.unique(np.array(final["Points3D:positions"]), axis=0))
    require(unique == data["manifest"]["anomalies"]["unique_position_count"], "Duplicate positions were changed.")
    return dict(stages=stages, cameras=4, embedded_original_images=4, final_point_ids=386,
                unique_positions=unique, original_rgb_exact=True, original_xyz_exact=True,
                all_observations_logged=897, camera_projection_tolerance_px=.001,
                high_error_final_association_point_ids=data["manifest"]["anomalies"]["high_error_final_association_point_ids"])
