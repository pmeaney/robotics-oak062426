# Scan Parameter Space

## Pat's Initial Framing

The size of the shelf and its cells can change in x, y, and z axes — so those axis lengths will be parameters.

The "resolution" (what should we call it?) of 1 inch could change. On it we base things like "move [Unit] up, take another reading" — i.e. move 1 inch up to take the next vertical cross-section reading.

Then there's the collection of readings. On each new cell, a new object is created:

```
readingsCollection: [ cell1 ]
```

...becomes:

```
readingsCollection: [ cell1, cell2 ]
```

...once the 2nd cell reading starts. Each cell item contains however many vertical cross-section scans are needed (e.g. ~23 or 24 for a 2' high cell).

---

## Refined Parameter Space

### Shelf Geometry
*(all variable, defined per config)*

| Parameter | Axis | Description |
|---|---|---|
| `shelfWidth` | X | Total width of the shelf |
| `shelfHeight` | Y | Total height of the shelf |
| `shelfDepth` | Z | How deep each cell goes (what the lidar shoots into) |
| `cellCountX` | — | Number of cells across |
| `cellCountY` | — | Number of cell rows |

**Derived:**
- `cellWidth = shelfWidth / cellCountX`
- `cellHeight = shelfHeight / cellCountY`

---

### Scan Resolution

**Parameter name: `scanStep`**

One value drives everything. It is the unit of gantry movement between readings:

- Vertical distance the gantry moves between slices: `scanStep`
- Number of slices per cell: `Math.ceil(cellHeight / scanStep)`
- Voxel bin size in Y: `scanStep` *(should match — one param controls both)*

---

### Per-Scan Reading
*(one lidar sweep at one gantry position)*

| Field | Description |
|---|---|
| `angle` | 0–360° |
| `distance` | mm |
| `quality` | Signal confidence |
| `gantryX` | Gantry X position at time of reading |
| `gantryY` | Gantry Y position at time of reading |

---

### Data Structure

```json
readingsCollection: [
  {
    "cellId": "A1",
    "cellX": 0,
    "cellY": 0,
    "capturedAt": "<timestamp>",
    "slices": [
      {
        "sliceIndex": 0,
        "gantryY": 0,
        "readings": [
          { "angle": 0.0, "distance": 0.0, "quality": 0 }
        ]
      },
      {
        "sliceIndex": 1,
        "gantryY": 25,
        "readings": []
      }
    ]
  },
  {
    "cellId": "A2",
    "cellX": 1,
    "cellY": 0,
    "capturedAt": "<timestamp>",
    "slices": []
  }
]
```

---

## Open Questions

- **`scanStep` = voxel size?** Probably yes in X and Y — one param controls both. Worth locking in.
- **Raw vs. converted readings?** Store raw polar (angle + distance) to keep files small and allow reprocessing. Convert to Cartesian (x, y, z) at visualization time, not capture time.
