# ══════════════════════════════════════════════════════════════════════════════
# Spline computation engine
# ══════════════════════════════════════════════════════════════════════════════

import numpy as np

from scipy.interpolate import splprep, splev


def compute_spline(pts, resolution, smoothness, closed):
    """
    Fit a B-spline through pts using splprep, evaluate at `resolution` samples.
    For closed splines the first point is appended at the end so splprep's
    periodic mode (per=True) has a well-defined closing segment.
    Returns np.ndarray (resolution, 3).
    """
    arr = np.array(pts, dtype=float)
    if len(arr) < 2:
        raise ValueError("Need at least 2 control points.")

    if closed:
        # splprep with per=True ignores the last point if it equals the first.
        # Explicitly append a clone of the first point so the loop closes.
        arr = np.vstack([arr, arr[0]])

    # Clamp spline degree to available points
    k = min(3, len(arr) - 1)

    # Remove consecutive duplicates (splprep crashes on zero-length segments)
    diffs = np.linalg.norm(np.diff(arr, axis=0), axis=1)
    mask  = np.concatenate(([True], diffs > 1e-9))
    arr   = arr[mask]
    if len(arr) < 2:
        raise ValueError("All control points are identical.")

    tck, _ = splprep(arr.T, s=smoothness, per=bool(closed), k=k)
    u   = np.linspace(0.0, 1.0, resolution)
    xyz = np.array(splev(u, tck)).T
    return xyz


def compute_direction_vectors(path_pts, direction_cfg, resolution):
    """
    Return (resolution, 3) float array of unit camera direction vectors.
    The vectors are normalised but NOT orthogonalised against north —
    that is the renderer's job, or done explicitly if needed.
    """
    mode = direction_cfg["mode"]

    if mode == "tangent":
        d     = np.gradient(path_pts, axis=0)
        norms = np.linalg.norm(d, axis=1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        return d / norms

    if mode == "spline":
        ctrl = direction_cfg["points"]
        if len(ctrl) < 2:
            raise ValueError("Direction spline needs at least 2 control points.")
        raw   = compute_spline(ctrl, resolution,
                               direction_cfg.get("smoothness", 0.0),
                               direction_cfg.get("closed", False))
        # raw holds world-space positions on the direction spline.
        # The direction vector is path_point → direction_spline_point, normalised.
        diff  = raw - path_pts
        norms = np.linalg.norm(diff, axis=1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        return diff / norms

    if mode == "look_at":
        target = np.array(direction_cfg["target"], dtype=float)
        d      = target[np.newaxis, :] - path_pts
        norms  = np.linalg.norm(d, axis=1, keepdims=True)
        norms  = np.where(norms < 1e-12, 1.0, norms)
        return d / norms

    if mode == "fixed_vector":
        v = np.array(direction_cfg["vector"], dtype=float)
        n = np.linalg.norm(v)
        v = v / n if n > 1e-12 else np.array([0.0, 1.0, 0.0])
        return np.tile(v, (resolution, 1))

    raise ValueError("Unknown direction mode: %s" % mode)


def compute_north_vectors(path_pts, north_cfg, resolution):
    """
    Return (resolution, 3) float array of unit north/up vectors.
    These are the RAW north vectors — no orthogonalisation against the
    direction vector is applied here.  The direction vector must not
    influence north; they are independent artist inputs.
    """
    mode = north_cfg["mode"]

    if mode == "fixed_vector":
        v = np.array(north_cfg["vector"], dtype=float)
        n = np.linalg.norm(v)
        v = v / n if n > 1e-12 else np.array([0.0, 0.0, 1.0])
        return np.tile(v, (resolution, 1))

    if mode == "spline":
        ctrl = north_cfg["points"]
        if len(ctrl) < 2:
            raise ValueError("North spline needs at least 2 control points.")
        raw   = compute_spline(ctrl, resolution,
                               north_cfg.get("smoothness", 0.0),
                               north_cfg.get("closed", False))
        # raw holds world-space positions on the north spline.
        # The north vector is path_point → north_spline_point, normalised.
        diff  = raw - path_pts
        norms = np.linalg.norm(diff, axis=1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        return diff / norms

    if mode == "fixed_point":
        target = np.array(north_cfg["target"], dtype=float)
        up     = target[np.newaxis, :] - path_pts
        norms  = np.linalg.norm(up, axis=1, keepdims=True)
        norms  = np.where(norms < 1e-12, 1.0, norms)
        return up / norms

    raise ValueError("Unknown north mode: %s" % mode)


def build_export_lines(path_pts, dir_vecs, north_vecs):
    """
    Return list of strings: "x y z cx cy cz nx ny nz" (no header).
    """
    lines = []
    for p, c, n in zip(path_pts, dir_vecs, north_vecs):
        lines.append("%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f"
                     % (p[0], p[1], p[2], c[0], c[1], c[2], n[0], n[1], n[2]))
    return lines