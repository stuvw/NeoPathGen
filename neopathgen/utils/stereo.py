# ══════════════════════════════════════════════════════════════════════════════
# Stereo offset engine
# ══════════════════════════════════════════════════════════════════════════════

import numpy as np

def compute_stereo_offset(path_pts, dir_vecs, north_vecs, offset):
    """
    Compute left and right offset paths for stereo rendering.

    Lateral axis = normalize(dir × north)  (camera's right vector).
    Left  path = path − 0.5 * offset * lateral
    Right path = path + 0.5 * offset * lateral

    Direction and north vectors are identical for both eyes.

    Returns
    -------
    left_path, left_dir, left_north,
    right_path, right_dir, right_north   — all (N, 3) float arrays.
    """
    lateral = np.cross(dir_vecs, north_vecs)
    norms   = np.linalg.norm(lateral, axis=1, keepdims=True)
    norms   = np.where(norms < 1e-12, 1.0, norms)
    lateral = lateral / norms

    half       = 0.5 * float(offset)
    left_path  = path_pts - half * lateral
    right_path = path_pts + half * lateral

    return (left_path,  dir_vecs.copy(), north_vecs.copy(),
            right_path, dir_vecs.copy(), north_vecs.copy())