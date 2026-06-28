#!/usr/bin/env python3
"""
generate_graph_layout.py
========================
One-time script to pre-compute deterministic 2-D sensor positions for the
TraffiTwin AI network visualization.

Run from the project root:
    python scripts/generate_graph_layout.py

Output:
    frontend/public/graph_layout.json

Each entry: { "id": <int>, "x": <float 0-1>, "y": <float 0-1> }

Node positions are normalised to [0, 1] so the frontend can scale them to
any canvas size without recomputing layouts.
"""

import json
import pickle
import pathlib
import sys

import numpy as np

# ── Attempt networkx import ───────────────────────────────────────────────────
try:
    import networkx as nx
except ImportError:
    print("networkx not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "networkx"])
    import networkx as nx

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).parent.parent
ADJ_PATH = ROOT / "datasets" / "raw" / "adj_mx.pkl"
OUT_PATH = ROOT / "frontend" / "public" / "graph_layout.json"

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_adjacency() -> np.ndarray:
    with open(ADJ_PATH, "rb") as f:
        data = pickle.load(f, encoding="latin-1")
    if isinstance(data, (tuple, list)) and len(data) == 3:
        _, _, A = data
    elif isinstance(data, np.ndarray):
        A = data
    else:
        raise ValueError(f"Unexpected adjacency structure: {type(data)}")
    return A.astype(np.float32)


def build_graph(A: np.ndarray) -> nx.Graph:
    G = nx.Graph()
    n = A.shape[0]
    G.add_nodes_from(range(n))
    for i in range(n):
        for j in range(i + 1, n):
            w = float(A[i, j])
            if w > 0:
                G.add_edge(i, j, weight=w)
    return G


def compute_layout(G: nx.Graph, seed: int = 42) -> dict[int, tuple[float, float]]:
    """
    spring_layout with a fixed seed for determinism.
    k controls spacing — higher = more spread.
    iterations=200 gives a well-settled layout.
    """
    print(f"Computing spring layout for {G.number_of_nodes()} nodes, "
          f"{G.number_of_edges()} edges …")
    pos = nx.spring_layout(
        G,
        seed=seed,
        k=0.35,
        iterations=200,
        weight="weight",
    )
    return pos


def normalise(pos: dict[int, tuple[float, float]]) -> dict[int, tuple[float, float]]:
    """Map all coordinates to [0.05, 0.95] so nodes stay within canvas bounds."""
    xs = np.array([v[0] for v in pos.values()])
    ys = np.array([v[1] for v in pos.values()])

    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()

    margin = 0.05
    span = 1.0 - 2 * margin

    normalised = {}
    for node_id, (x, y) in pos.items():
        nx_val = margin + (x - x_min) / (x_max - x_min) * span if x_max > x_min else 0.5
        ny_val = margin + (y - y_min) / (y_max - y_min) * span if y_max > y_min else 0.5
        normalised[node_id] = (float(nx_val), float(ny_val))
    return normalised


def main():
    print(f"Loading adjacency matrix from {ADJ_PATH} …")
    A = load_adjacency()
    print(f"Matrix shape: {A.shape}")

    G = build_graph(A)
    pos = compute_layout(G)
    pos = normalise(pos)

    layout = [
        {"id": node_id, "x": round(x, 6), "y": round(y, 6)}
        for node_id, (x, y) in sorted(pos.items())
    ]

    with open(OUT_PATH, "w") as f:
        json.dump(layout, f, separators=(",", ":"))

    print(f"✓ Wrote {len(layout)} node positions → {OUT_PATH}")


if __name__ == "__main__":
    main()
