"""Non-destructive geometry diagnostics for notebook 13 (NumPy + OpenCV + Plotly)."""
from pathlib import Path
import csv
import json

import cv2
import numpy as np


def camera_center(pose):
    R, t = pose
    return -np.asarray(R).T @ np.asarray(t).reshape(3)


def pair_metrics(points, pixels_a, pixels_b, pose_a, pose_b, K):
    """Depth is camera Z; angle is between world-space point-to-center rays.

    Effective angle folds angles above 90 deg, also rejecting antiparallel rays.
    Undefined projections/rays remain NaN and must fail the finite check.
    """
    X = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    rays = [X - camera_center(p) for p in (pose_a, pose_b)]
    lengths = [np.linalg.norm(r, axis=1) for r in rays]
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        unit = [r / d[:, None] for r, d in zip(rays, lengths)]
        # atan2 is more stable than acos near parallel rays.
        angle = np.degrees(np.arctan2(
            np.linalg.norm(np.cross(*unit), axis=1),
            np.sum(unit[0] * unit[1], axis=1)))
    depths, errors = [], []
    for (R, t), pixels in zip((pose_a, pose_b), (pixels_a, pixels_b)):
        cam = X @ np.asarray(R).T + np.asarray(t).reshape(3)
        homogeneous = cam @ np.asarray(K).T
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            projected = homogeneous[:, :2] / homogeneous[:, 2:3]
            errors.append(np.linalg.norm(projected - np.asarray(pixels), axis=1))
        depths.append(cam[:, 2])
    return dict(angle_deg=angle, effective_angle_deg=np.minimum(angle, 180-angle),
                depth_a=depths[0], depth_b=depths[1],
                error_a_px=errors[0], error_b_px=errors[1],
                max_error_px=np.maximum(*errors),
                max_depth=np.maximum(*depths))


def replay_birth_observations(ns):
    """Replay expansion on COPIES, checking IDs/coordinates against the live map.

    Final keypoint dictionaries may have overwritten many-to-one associations.
    Capture original candidate observations before inserting each expansion.
    The original expand_map function is used unchanged; no RANSAC is repeated.
    """
    X = np.asarray(ns['global_points'])
    seed = ns['seed_matches']
    n = len(ns['seed_points_3d'])
    if len(seed) != n:
        raise ValueError('Seed match/point alignment is inconsistent; rerun in order.')
    maps = {
        2: {m.queryIdx: k for k, m in enumerate(seed)},
        3: {m.trainIdx: k for k, m in enumerate(seed)},
        4: dict(ns['view05_to_3d']),
        5: dict(ns['cam06']['kp_to_3d']),
    }
    poses = {v-1: p for v, p in ns['camera_poses'].items()}
    groups = [(np.arange(n), 2, 3, seed, 'Seed 03-04')]
    copied_X = ns['seed_points_3d'].copy()
    copied_colors = ns['seed_colors'].copy()
    for a, b, ids_name, label in [(3, 4, 'new_from_05', 'View 05'),
                                  (4, 5, 'new_from_06', 'View 06')]:
        good = [pair[0] for pair in ns['bf'].knnMatch(
            ns['descriptors'][a], ns['descriptors'][b], k=2)
            if len(pair) == 2 and pair[0].distance < .75 * pair[1].distance]
        # Mirror only identity propagation on private copies to identify candidates.
        ma, mb = maps[a].copy(), maps[b].copy()
        for m in good:
            if m.queryIdx in ma and m.trainIdx not in mb:
                mb[m.trainIdx] = ma[m.queryIdx]
            elif m.trainIdx in mb and m.queryIdx not in ma:
                ma[m.queryIdx] = mb[m.trainIdx]
        candidates = [m for m in good if m.queryIdx not in ma and m.trainIdx not in mb]
        pa = np.float32([ns['keypoints'][a][m.queryIdx].pt for m in candidates]).reshape(-1, 2)
        pb = np.float32([ns['keypoints'][b][m.trainIdx].pt for m in candidates]).reshape(-1, 2)
        # Same float32 observations, DLT and OpenCV projection as the historical code.
        if candidates:
            Ra, ta = poses[a]
            Rb, tb = poses[b]
            H = cv2.triangulatePoints(ns['K'] @ np.hstack((Ra, ta)),
                                     ns['K'] @ np.hstack((Rb, tb)), pa.T, pb.T)
            with np.errstate(divide='ignore', invalid='ignore'):
                xyz = (H[:3] / H[3]).T
            ca, cb = (Ra @ xyz.T + ta).T, (Rb @ xyz.T + tb).T
            ea = cv2.projectPoints(xyz, cv2.Rodrigues(Ra)[0], ta, ns['K'], None)[0].reshape(-1, 2)
            eb = cv2.projectPoints(xyz, cv2.Rodrigues(Rb)[0], tb, ns['K'], None)[0].reshape(-1, 2)
            valid = (np.isfinite(xyz).all(1) & (ca[:, 2] > 0) & (cb[:, 2] > 0)
                     & (np.linalg.norm(ea-pa, axis=1) < 3.0)
                     & (np.linalg.norm(eb-pb, axis=1) < 3.0))
            selected = [m for m, keep in zip(candidates, valid) if keep]
        else:
            selected = []
        copied_X, copied_colors, maps[a], maps[b], ids, _ = ns['expand_map'](
            a, b, *poses[a], *poses[b], copied_X, copied_colors,
            maps[a], maps[b], label, max_reprojection_error=3.0)
        if list(ids) != list(ns[ids_name]) or len(selected) != len(ids):
            raise ValueError('Expansion replay differs from the current map; rerun original cells in order.')
        groups.append((np.asarray(ids, dtype=int), a, b, selected, label))
    if copied_X.shape != X.shape or not np.allclose(copied_X, X, rtol=0, atol=1e-7):
        raise ValueError('Expansion coordinates differ from the current map; diagnostics aborted.')
    return groups


def diagnose_map(ns):
    """One row per original map ID; extra observations are audited separately."""
    groups = replay_birth_observations(ns)
    X = np.asarray(ns['global_points'], dtype=float)
    poses = {v-1: p for v, p in ns['camera_poses'].items()}
    rows = [None] * len(X)
    for ids, a, b, matches, label in groups:
        pixels = [np.array([ns['keypoints'][v][getattr(m, attr)].pt for m in matches]).reshape(-1, 2)
                  for v, attr in [(a, 'queryIdx'), (b, 'trainIdx')]]
        metrics = pair_metrics(X[ids], *pixels, poses[a], poses[b], ns['K'])
        baseline = np.linalg.norm(camera_center(poses[a])-camera_center(poses[b]))
        if not np.isfinite(baseline) or baseline <= 1e-12:
            raise ValueError('Degenerate birth-camera baseline.')
        for k, (point_id, m) in enumerate(zip(ids, matches)):
            row = dict(point_id=int(point_id), origin=label, view_a=a+1, view_b=b+1,
                       kp_a=int(m.queryIdx), kp_b=int(m.trainIdx),
                       x=float(X[point_id, 0]), y=float(X[point_id, 1]), z=float(X[point_id, 2]),
                       baseline=float(baseline))
            row.update({name: float(values[k]) for name, values in metrics.items()})
            row['depth_baselines'] = row['max_depth'] / baseline
            rows[point_id] = row
    if any(row is None for row in rows):
        raise ValueError('Some map points have no birth observations.')
    # Do not silently treat propagated descriptor matches as verified tracks.
    for row in rows:
        pid = row['point_id']
        errors, depths, count = [], [], 0
        for view, associations in ns['view_maps'].items():
            if view not in poses:
                continue
            R, t = poses[view]
            for kp, target in associations.items():
                if target != pid:
                    continue
                point = X[pid:pid+1]
                projected = cv2.projectPoints(point, cv2.Rodrigues(R)[0], t, ns['K'], None)[0].reshape(2)
                errors.append(float(np.linalg.norm(projected-ns['keypoints'][view][kp].pt)))
                depths.append(float((R @ X[pid] + np.asarray(t).reshape(3))[2]))
                count += 1
        row['associated_observations'] = count
        row['associated_max_error_px'] = max(errors, default=float('nan'))
        row['associated_min_depth'] = min(depths, default=float('nan'))
    return rows


def classify(rows, min_angle=2.0, max_error=3.0, max_depth_baselines=10.0,
             check_associations=False):
    """Return a mask and overlapping rejection reasons. Thresholds are inclusive."""
    if not (0 <= min_angle <= 90 and max_error >= 0 and max_depth_baselines > 0):
        raise ValueError('Invalid geometric thresholds.')
    mask, reasons = [], []
    fields = ['x', 'y', 'z', 'effective_angle_deg', 'depth_a', 'depth_b', 'max_error_px', 'depth_baselines']
    for row in rows:
        why = []
        if not all(np.isfinite(row[f]) for f in fields): why.append('nonfinite')
        if not (row['depth_a'] > 0 and row['depth_b'] > 0): why.append('cheirality')
        if row['effective_angle_deg'] < min_angle: why.append('angle')
        if row['max_error_px'] > max_error: why.append('reprojection')
        if row['depth_baselines'] > max_depth_baselines: why.append('depth')
        if check_associations and not (
            row['associated_observations'] >= 2
            and np.isfinite(row['associated_max_error_px'])
            and row['associated_max_error_px'] <= max_error
            and row['associated_min_depth'] > 0): why.append('associations')
        mask.append(not why)
        reasons.append(why)
    return np.asarray(mask, dtype=bool), reasons


def statistics(rows, mask=None):
    selected = rows if mask is None else [r for r, keep in zip(rows, mask) if keep]
    result = {'count': len(selected)}
    for field in ['z', 'max_depth', 'depth_baselines', 'effective_angle_deg', 'max_error_px', 'associated_max_error_px']:
        values = np.array([r[field] for r in selected])
        values = values[np.isfinite(values)]
        result[field] = {k: float(v) for k, v in zip(
            ['min', 'median', 'p95', 'max'],
            np.percentile(values, [0, 50, 95, 100]))} if len(values) else None
    return result


def export_diagnostics(rows, camera_poses, output_dir, **thresholds):
    """Write a standalone offline Plotly dashboard, CSV and reproducible summary."""
    import plotly.graph_objects as go
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    mask, reasons = classify(rows, **thresholds)
    summary = dict(thresholds=thresholds, before=statistics(rows), after=statistics(rows, mask),
                   rejected=int((~mask).sum()),
                   reasons={reason: sum(reason in why for why in reasons)
                            for reason in ['nonfinite', 'cheirality', 'angle', 'reprojection', 'depth', 'associations']},
                   by_origin={origin: {'before': sum(r['origin']==origin for r in rows),
                                       'after': int(sum(r['origin']==origin and keep for r, keep in zip(rows, mask)))}
                              for origin in sorted({r['origin'] for r in rows})})
    (output_dir/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    fields = list(rows[0]) + ['accepted', 'rejection_reasons'] if rows else ['accepted', 'rejection_reasons']
    with (output_dir/'points.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row, keep, why in zip(rows, mask, reasons):
            writer.writerow(dict(row, accepted=bool(keep), rejection_reasons=';'.join(why)))
    fig = go.Figure()
    for name, color in [('Aceptados', '#21b6a8'), ('Rechazados', '#f06a73')]:
        fig.add_trace(go.Scatter3d(x=[], y=[], z=[], mode='markers', name=name,
                                 marker=dict(color=color, size=4, opacity=.8),
                                 hovertemplate='%{text}<extra>%{fullData.name}</extra>'))
    centers = np.array([camera_center(p) for p in camera_poses.values()]).reshape(-1, 3)
    fig.add_trace(go.Scatter3d(x=centers[:, 0], y=centers[:, 1], z=centers[:, 2],
                             mode='markers+text', text=[f'View {v:02d}' for v in camera_poses],
                             marker=dict(size=7, symbol='diamond', color='#f2bd51'), name='Cámaras'))
    fig.update_layout(height=650, margin=dict(l=0, r=0, t=25, b=0), template='plotly_dark',
                      paper_bgcolor='#111827', uirevision='sfm-diagnostics',
                      scene=dict(aspectmode='data', xaxis_title='X (escala arbitraria)',
                                 yaxis_title='Y', zaxis_title='Z del mundo (View 03)'))
    # Nonfinite values become null in JSON; JavaScript explicitly rejects null.
    payload = [{k: (None if isinstance(v, float) and not np.isfinite(v) else v)
                for k, v in r.items()} for r in rows]
    script = (Path(__file__).with_name('triangulation_dashboard.js').read_text()
              .replace('__ROWS__', json.dumps(payload, allow_nan=False))
              .replace('__THRESHOLDS__', json.dumps(dict(min_angle=2., max_error=3., max_depth_baselines=10.,
                                                       check_associations=False) | thresholds)))
    plot_html = fig.to_html(full_html=False, include_plotlyjs=True, div_id='sfm-quality', post_script=script)
    header = '''<!doctype html><html lang="es"><meta charset="utf-8">
<title>Diagnóstico de triangulación · adversarial-vision</title>
<style>body{background:#111827;color:#e5e7eb;font:15px system-ui;margin:24px auto;max-width:1250px;padding:0 20px}
label{display:inline-block;margin:8px 22px 8px 0}input[type=number]{width:90px}table{border-collapse:collapse;width:100%;margin:14px 0}
th,td{text-align:left;padding:7px;border-bottom:1px solid #374151}select,button,input{font:inherit}#counts{font-size:20px;color:#5eead4}small{color:#9ca3af}</style>
<h1>Calidad de la reconstrucción 3D</h1>
<p>Filtros exploratorios sobre el mapa existente. Verde: aceptados; rojo: rechazados. Ningún punto se borra.
Arrastra para rotar; usa la leyenda para ocultar grupos y el hover para investigar IDs y motivos.</p>
<label>Ángulo efectivo mínimo (°) <input id="angle" type="number" min="0" max="90" step="0.25"></label>
<label>Error máximo por cámara (px) <input id="error" type="number" min="0" step="0.25"></label>
<label>Profundidad máxima / baseline <input id="depth" type="number" min="0.1" step="1"></label>
<label>Origen <select id="origin"><option value="all">Todos</option><option>Seed 03-04</option><option>View 05</option><option>View 06</option></select></label>
<label><input id="associations" type="checkbox"> Validar también asociaciones propagadas</label>
<button id="reset">Restablecer</button> <button id="focus">Encuadrar aceptados</button> <button id="allpoints">Encuadrar todos</button>
<p id="counts"></p><div id="stats"></div><div id="origins"></div><p id="reasons"></p>
<small>θ = ángulo entre X−Cₐ y X−Cᵦ; efectivo = min(θ, 180°−θ). z = (RX+t)₃.
Se exige z&gt;0 en ambas cámaras y valores finitos. Error = máximo de las dos distancias euclídeas en píxeles a las observaciones originales, a anchura 900 px.
El límite de profundidad usa la baseline de la pareja de nacimiento. Es una hipótesis exploratoria, no una frontera física ni una medida de incertidumbre.
Un error bajo puede coexistir con profundidad muy incierta. Intrínsecos aproximados, distorsión omitida y poses sin bundle adjustment limitan estas conclusiones.
Las asociaciones propagadas se auditan aparte: sus errores pueden indicar correspondencias incorrectas.</small>'''
    path = output_dir/'diagnostics.html'
    path.write_text(header+plot_html+'</html>')
    return path, summary
