# NeoPathGen — Camera Path Generator

NeoPathGen is a desktop tool for designing, previewing, and exporting camera paths for offline renderers. It provides an interactive 3D viewport for placing control points, a B-spline generator, a non-linear speed profile editor, and a stereo offset stage. Paths are exported as plain-text files readable by any renderer.

---

## Requirements

| Package | Version |
|---------|---------|
| Python | 3.9+ |
| PyQt5 | 5.15+ |
| Vispy | 0.13+ |
| NumPy | 1.23+ |
| SciPy | 1.10+ |
| Trimesh | 4.0+ |

Create Python virtual environment:

```bash
python3 -m venv ./.venv
```

Activate Python virtual environment:

| Platform |   Shell    |             Command                   |
| -------- | ---------- | ------------------------------------- |
|  POSIX   | bash/zsh   | `$ source ./.venv/bin/activate`       |
|          | fish       | `$ source ./.venv/bin/activate.fish`  |
|          | csh/tcsh   | `$ source ./.venv/bin/activate.csh`   |
|          | pwsh       | `$ ./.venv/bin/Activate.ps1`          |
| Windows  | cmd.exe    | `C:\> <venv>\Scripts\activate.bat`    |
|          | PowerShell | `PS C:\> <venv>\Scripts\Activate.ps1` |

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Running

```bash
python -m neopathgen
```

---

## Workflow Overview

The application is organised into four sequential stages, accessible via the tab bar at the top of the window. Later stages depend on earlier ones, and the app will warn you if you navigate forward with missing data.

---

### Stage 1 — Point Placement

Place and edit the control points that define your splines.

**Active layer selector** switches between three independent point clouds:

- **PATH** (blue) — the camera's world-space trajectory. This is the only mandatory layer.
- **DIRECTION** (amber) — controls where the camera looks.
- **NORTH** (teal) — controls the camera's up vector.

**Adding points**

- Click the **Add** button to insert a point offset from the last one, then adjust its position using the X / Y / Z spinboxes and sliders in the panel.
- Toggle **PLACE POINT** in the toolbar to enter click-to-place mode, which snaps new points to the ground plane (Z = 0). Press **Escape** to exit.
> WIP, is broken

**Direction modes**

| Mode | Behaviour |
|------|-----------|
| Auto-tangent | Direction follows the path's forward derivative at each sample |
| Spline | Direction interpolated through a separate set of control points |
| Look-at point | Camera always faces a fixed world-space coordinate |
| Fixed vector | Camera always faces a constant direction |

**North modes**

| Mode | Behaviour |
|------|-----------|
| Fixed vector (Z-up) | Constant up vector, default (0, 0, 1) |
| Spline | Up vector interpolated through a separate set of control points |
| Fixed point | Up vector points toward a fixed world-space coordinate |

**Reference mesh**

Load an OBJ, PLY, or STL file as a dim wireframe overlay to help position points relative to scene geometry. Visibility can be toggled freely.

**Viewport navigation** — left-drag to orbit, scroll to zoom. Preset views (PERSP / TOP / FRONT / SIDE) are available in the toolbar.

---

### Stage 2 — Spline Generation

Fits B-splines through the control points using `scipy.interpolate.splprep` and previews the result in the 3D viewport.

**Parameters**

- **Resolution** — number of output samples, shared across all splines (10 – 100 000).
- **Smoothness** — per-layer `s` parameter passed to `splprep`. A value of 0 forces the spline to pass exactly through every control point; higher values allow it to deviate for a smoother curve.
- **Closed loop** — per-layer. When enabled, the first control point is cloned and appended before fitting, ensuring a seamless loop.

When direction or north mode is **Spline**, the direction/north vectors at each sample are computed as the unit vector from the corresponding path sample toward the corresponding direction/north spline sample. All other modes compute vectors analytically.

**Visibility toggles** allow each spline line and each vector field (direction arrows, north arrows) to be shown or hidden independently.

**Export (Stage 2)**

Exports the uniform spline as a plain-text file with one line per sample:

```
x y z cx cy cz nx ny nz
```

No header. All values are space-separated 6-decimal floats. `c` is the unit direction vector, `n` is the unit north vector.

---

### Stage 3 — Speed Profile (optional)

Re-times the path so that samples are non-uniformly distributed along the curve parameter, allowing sections to feel slower or faster in the renderer.

**Speed segments**

Each segment defines a speed multiplier `m` over a sub-range `[start, end]` of the path parameter `u ∈ [0, 1]`:

- `m = 1.0` — normal speed
- `m = 2.0` — twice as fast (fewer samples in this region)
- `m = 0.5` — half speed (more samples, appears to slow down)

Segments do not need to cover the full `[0, 1]` range. Gaps are smoothly bridged using a smoothstep function. Regions before the first or after the last segment clamp to the nearest defined speed.

**Overlapping segments multiply.** A base segment `[0, 1, 0.5]` combined with an accent `[0.3, 0.5, 3.0]` produces `m = 1.5` in the overlap zone (`0.5 × 3.0`). This allows layered speed compositions.

**Apply to** checkboxes control which arrays are re-timed. Path is always re-timed. Direction and north can be kept on uniform parametrisation if you want them to move independently of the path timing — though in most cases keeping all three in sync is correct.

The **speed curve widget** shows the resolved `m(u)` function live as you edit the table, including smoothstep transitions.

A dot-cloud visualisation in the 3D viewport shows the re-timed sample density: clustered dots indicate slow regions, sparse dots indicate fast regions.

**Export (Stage 3)**

Same format as Stage 2, but samples are non-uniformly spaced along `u`. The file is written as `path_retimed.txt` by default.

---

### Stage 4 — Stereo Offset (optional)

Generates a left/right camera pair offset laterally from the main path.

**Inter-ocular distance** — total separation between the two cameras. Each eye is offset by half this value.

The lateral axis is computed as `normalize(direction × north)`, giving the camera's right vector in world space. This produces a **parallel stereo rig**: both cameras face the same direction, with only the origin shifted. Direction and north vectors are identical for both eyes.

**Source data** — Stage 4 automatically uses Stage 3 re-timed arrays if they exist, otherwise falls back to the Stage 2 uniform splines. The panel displays which source is active.

**Export (Stage 4)**

A single save dialog asks for a base filename. Two files are written:

```
<name>_left.txt
<name>_right.txt
```

Both use the same `x y z cx cy cz nx ny nz` format.

---

## Project File Format

Projects are saved as `.npj` files (JSON). The structure is human-readable and can be edited manually.

```json
{
  "path": { "points": [[x, y, z], ...] },
  "direction": {
    "mode": "tangent",
    "points": [],
    "target": [0, 0, 0],
    "vector": [0, 0, 1],
    "smoothness": 0.0,
    "closed": false
  },
  "north": {
    "mode": "fixed_vector",
    "points": [],
    "target": [0, 0, 0],
    "vector": [0, 0, 1],
    "smoothness": 0.0,
    "closed": false
  },
  "spline": {
    "resolution": 500,
    "smoothness": 0.0,
    "closed": false
  },
  "speed_profile": [
    { "start": 0.0, "end": 0.5, "speed": 0.5 },
    { "start": 0.5, "end": 1.0, "speed": 2.0 }
  ],
  "stereo_offset": 0.1,
  "mesh_path": null
}
```

Spline samples and computed vectors are not saved — they are recomputed on demand.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Escape | Exit place-point mode |

---

## Notes

- Spline fitting requires at least 2 control points. Cubic fitting (`k=3`) requires at least 4; the degree is automatically clamped for smaller point sets.
- Consecutive duplicate control points are silently removed before fitting to prevent `splprep` from failing.
- North vectors are independent of direction vectors — no Gram-Schmidt orthogonalisation is applied at export. If your renderer requires orthonormal camera frames, apply the orthogonalisation on the renderer side.
- The stereo rig is parallel (no toe-in). Toe-in is generally discouraged for large screens and VR due to vertical disparity artefacts at the image edges.