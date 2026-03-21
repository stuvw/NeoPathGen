# ══════════════════════════════════════════════════════════════════════════════
# Speed profile engine
# ══════════════════════════════════════════════════════════════════════════════

import numpy as np

def _smoothstep(x):
    return x * x * (3.0 - 2.0 * x)


def _speed_multiplier(u, prof):
    """
    Evaluate the speed multiplier m(u) for a list of (start, end, speed) tuples.

    Overlapping segments are MULTIPLIED together, so they stack naturally:
    a base slow-motion [0,1,0.5] plus a fast accent [0.3,0.5,3.0] gives
    m=1.5 in the overlap zone (0.5 × 3.0).

    Gaps between non-overlapping groups of segments are smoothly bridged
    with smoothstep between the exit speed of one group and the entry speed
    of the next. Regions before the first or after the last segment clamp
    to the nearest segment's contribution.
    """
    if not prof:
        return 1.0

    # Collect all segments that contain u and multiply their speeds
    active = [v for (a, b, v) in prof if a <= u <= b]
    if active:
        result = 1.0
        for v in active:
            result *= v
        return result

    # u is in a gap — find the surrounding non-overlapping boundary speeds
    # by evaluating the product at the edges of adjacent segments
    left_speed  = None   # effective speed just to the left of u
    left_end    = None
    right_speed = None
    right_start = None

    for (a, b, v) in prof:
        if b < u:
            # Segment ends before u — its right-edge contribution
            edge_speed = _speed_multiplier(b, prof)
            if left_end is None or b > left_end:
                left_end   = b
                left_speed = edge_speed
        if a > u:
            # Segment starts after u — its left-edge contribution
            edge_speed = _speed_multiplier(a, prof)
            if right_start is None or a < right_start:
                right_start = a
                right_speed = edge_speed

    if left_speed is not None and right_speed is not None:
        # Smooth bridge across the gap
        t = (u - left_end) / (right_start - left_end)
        return left_speed + (right_speed - left_speed) * _smoothstep(t)

    if left_speed is not None:
        return left_speed   # clamp past last segment
    if right_speed is not None:
        return right_speed  # clamp before first segment

    return 1.0


def apply_speed_profile(path_pts, dir_vecs, north_vecs, speed_profile, resolution):
    """
    Re-time path_pts / dir_vecs / north_vecs according to speed_profile.

    The speed profile defines relative speed multipliers over u ∈ [0,1].
    Slow sections (low multiplier) get more samples; fast sections fewer.

    Returns
    -------
    (rt_path, rt_dir, rt_north, u_samples)
        All three arrays are (resolution, 3).
        u_samples is the (resolution,) array of path parameter values used,
        which is useful for debugging / visualisation.
    """
    N = len(path_pts)
    if N < 2:
        raise ValueError("Need at least 2 path points.")

    # Build sorted profile tuples
    prof = sorted(
        [(float(s["start"]), float(s["end"]), float(s["speed"]))
         for s in speed_profile],
        key=lambda x: x[0]
    )

    # If no segments defined, treat as uniform (m=1 everywhere)
    if not prof:
        prof = [(0.0, 1.0, 1.0)]

    # Supersample parameter space to build the time-warp mapping
    oversample  = max(10, resolution * 10)
    u_dense     = np.linspace(0.0, 1.0, oversample)
    density     = np.array([1.0 / max(_speed_multiplier(u, prof), 1e-9)
                             for u in u_dense])

    cumulative  = np.cumsum(density)
    cumulative /= cumulative[-1]

    # Invert: uniform time → warped u
    t_uniform = np.linspace(0.0, 1.0, resolution)
    u_samples = np.interp(t_uniform, cumulative, u_dense)

    # Re-sample all three arrays at the new u positions using linear interp
    u_orig = np.linspace(0.0, 1.0, N)

    def _resample(arr):
        out = np.empty((resolution, 3), dtype=np.float64)
        for c in range(3):
            out[:, c] = np.interp(u_samples, u_orig, arr[:, c])
        return out

    rt_path  = _resample(path_pts)
    rt_dir   = _resample(dir_vecs)
    rt_north = _resample(north_vecs)

    # Re-normalise direction and north after interpolation
    for arr in (rt_dir, rt_north):
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        arr /= norms

    return rt_path, rt_dir, rt_north, u_samples


def eval_speed_curve(prof_list, n_points=400):
    """
    Evaluate the resolved m(u) curve at n_points for display.
    Returns (u_arr, m_arr) both shape (n_points,).
    """
    prof = sorted(
        [(float(s["start"]), float(s["end"]), float(s["speed"]))
         for s in prof_list],
        key=lambda x: x[0]
    )
    if not prof:
        u = np.linspace(0.0, 1.0, n_points)
        return u, np.ones(n_points)

    u = np.linspace(0.0, 1.0, n_points)
    m = np.array([_speed_multiplier(ui, prof) for ui in u])
    return u, m