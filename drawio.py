# -*- coding: utf-8 -*-
"""
drawio.py — Core library for draw.io XML manipulation.

This module owns all file I/O, XML parsing, and diagram primitives.
It has no dependency on MCP. Import it directly for scripting, testing,
or building higher-level tools on top of the diagram engine.

Public API
----------
File I/O
    load_diagram(path)          -> ET.ElementTree
    save_diagram(tree, path)    -> None
    get_root_cell(tree)         -> ET.Element
    read_file(path)             -> str
    write_file(path, content)   -> str
    blank_template(page_name)   -> str

Node / Edge primitives
    next_id(root_el)            -> str
    get_nodes(path)             -> str          (JSON)
    insert_node(...)            -> str          (new cell id)
    insert_edge(...)            -> str          (new cell id)
    modify_node(...)            -> str
    remove_node(path, cell_id)  -> str

Layout
    apply_layout(...)           -> str
"""

import json
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from pathlib import Path


# ==============================================================================
# FILE I/O
# ==============================================================================

def load_diagram(path: str) -> ET.ElementTree:
    """
    Parse a .drawio / .xml file and return the ElementTree.

    Args:
        path: Full path to the diagram file.

    Returns:
        Parsed ElementTree.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Diagram not found: {path}")
    return ET.parse(str(p))


def save_diagram(tree: ET.ElementTree, path: str) -> None:
    """
    Write an ElementTree back to disk with XML declaration and indentation.

    Args:
        tree: The ElementTree to serialise.
        path: Destination file path.
    """
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def get_root_cell(tree: ET.ElementTree) -> ET.Element:
    """
    Return the <root> element that contains all diagram cells.

    Args:
        tree: Parsed ElementTree of a draw.io file.

    Returns:
        The <root> ET.Element.

    Raises:
        ValueError: If no <root> element is found (malformed file).
    """
    root_el = tree.find(".//root")
    if root_el is None:
        raise ValueError("Malformed draw.io file: no <root> element found.")
    return root_el


def read_file(path: str) -> str:
    """
    Read the raw XML content of a diagram file as a string.

    Args:
        path: Full path to the .drawio or .xml file.

    Returns:
        Raw XML string, or an error message prefixed with 'ERROR:'.
    """
    p = Path(path)
    if not p.exists():
        return f"ERROR: File not found -> {path}"
    return p.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    """
    Write (overwrite) a diagram file with the supplied XML string.
    Creates parent directories if they do not exist.

    Args:
        path:    Destination file path.
        content: Full XML string to write.

    Returns:
        Confirmation message with the resolved absolute path.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Saved: {p.resolve()}"


def blank_template(page_name: str = "Page-1") -> str:
    """
    Return a minimal valid draw.io XML string for a blank diagram.

    Args:
        page_name: Name of the first diagram page.

    Returns:
        XML string ready to write to a .drawio file.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<mxfile version="24.0.0">
  <diagram name="{page_name}" id="page1">
    <mxGraphModel dx="1034" dy="546" grid="1" gridSize="10" guides="1"
                  tooltips="1" connect="1" arrows="1" fold="1"
                  page="1" pageScale="1" pageWidth="1169" pageHeight="827"
                  math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""


# ==============================================================================
# CELL ID GENERATION
# ==============================================================================

def next_id(root_el: ET.Element) -> str:
    """
    Generate a unique 8-character cell ID that does not clash with
    any existing cell ID in the diagram.

    Args:
        root_el: The <root> element of the diagram.

    Returns:
        A unique string ID.
    """
    existing = {cell.get("id", "") for cell in root_el.findall("mxCell")}
    while True:
        new_id = str(uuid.uuid4())[:8]
        if new_id not in existing:
            return new_id


# ==============================================================================
# NODE / EDGE PRIMITIVES
# ==============================================================================

def get_nodes(path: str) -> str:
    """
    Return all nodes (vertices) and edges in a diagram as a JSON string.

    Each entry includes:
        id, label, type ('vertex' or 'edge'), style, source, target.

    Args:
        path: Full path to the .drawio file.

    Returns:
        JSON array string, or an error message prefixed with 'ERROR:'.
    """
    try:
        tree    = load_diagram(path)
        root_el = get_root_cell(tree)
        cells   = []
        for cell in root_el.findall("mxCell"):
            cid = cell.get("id")
            if cid in ("0", "1"):
                continue
            cells.append({
                "id":     cid,
                "label":  cell.get("value", ""),
                "type":   "edge" if cell.get("edge") == "1" else "vertex",
                "style":  cell.get("style", ""),
                "source": cell.get("source"),
                "target": cell.get("target"),
            })
        return json.dumps(cells, indent=2)
    except Exception as e:
        return f"ERROR: {e}"


def insert_node(
    path: str,
    label: str,
    x: int = 100,
    y: int = 100,
    width: int = 120,
    height: int = 60,
    style: str = "rounded=1;whiteSpace=wrap;html=1;",
) -> str:
    """
    Add a new vertex (shape) to the diagram.

    Args:
        path:   Full path to the .drawio file.
        label:  Text label displayed inside the shape.
        x:      X position in pixels.
        y:      Y position in pixels.
        width:  Shape width in pixels.
        height: Shape height in pixels.
        style:  draw.io style string.

    Returns:
        The new cell's ID on success, or an error message.
    """
    try:
        tree    = load_diagram(path)
        root_el = get_root_cell(tree)
        new_id  = next_id(root_el)

        cell = ET.SubElement(root_el, "mxCell")
        cell.set("id",     new_id)
        cell.set("value",  label)
        cell.set("style",  style)
        cell.set("vertex", "1")
        cell.set("parent", "1")

        geo = ET.SubElement(cell, "mxGeometry")
        geo.set("x",      str(x))
        geo.set("y",      str(y))
        geo.set("width",  str(width))
        geo.set("height", str(height))
        geo.set("as",     "geometry")

        save_diagram(tree, path)
        return new_id
    except Exception as e:
        return f"ERROR: {e}"


def insert_edge(
    path: str,
    source_id: str,
    target_id: str,
    label: str = "",
    style: str = "edgeStyle=orthogonalEdgeStyle;",
) -> str:
    """
    Add a directed edge (connector) between two existing nodes.

    Args:
        path:      Full path to the .drawio file.
        source_id: Cell ID of the source node.
        target_id: Cell ID of the target node.
        label:     Optional label to display on the edge.
        style:     draw.io edge style string.

    Returns:
        The new edge's ID on success, or an error message.
    """
    try:
        tree    = load_diagram(path)
        root_el = get_root_cell(tree)
        new_id  = next_id(root_el)

        cell = ET.SubElement(root_el, "mxCell")
        cell.set("id",     new_id)
        cell.set("value",  label)
        cell.set("style",  style)
        cell.set("edge",   "1")
        cell.set("source", source_id)
        cell.set("target", target_id)
        cell.set("parent", "1")

        geo = ET.SubElement(cell, "mxGeometry")
        geo.set("relative", "1")
        geo.set("as",       "geometry")

        save_diagram(tree, path)
        return new_id
    except Exception as e:
        return f"ERROR: {e}"


def modify_node(
    path: str,
    cell_id: str,
    label: str | None = None,
    style: str | None = None,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> str:
    """
    Update the label, style, and/or geometry of an existing node.
    Only the fields you supply will be changed.

    Args:
        path:          Full path to the .drawio file.
        cell_id:       ID of the cell to update.
        label:         New label text (optional).
        style:         New style string (optional).
        x:             New X position (optional).
        y:             New Y position (optional).
        width:         New width (optional).
        height:        New height (optional).

    Returns:
        Confirmation string, or an error message.
    """
    try:
        tree    = load_diagram(path)
        root_el = get_root_cell(tree)
        cell    = root_el.find(f"mxCell[@id='{cell_id}']")
        if cell is None:
            return f"ERROR: Cell id={cell_id} not found."

        if label is not None:
            cell.set("value", label)
        if style is not None:
            cell.set("style", style)

        geo = cell.find("mxGeometry")
        if geo is not None:
            if x      is not None: geo.set("x",      str(x))
            if y      is not None: geo.set("y",      str(y))
            if width  is not None: geo.set("width",  str(width))
            if height is not None: geo.set("height", str(height))

        save_diagram(tree, path)
        return f"Updated cell id={cell_id}"
    except Exception as e:
        return f"ERROR: {e}"


def remove_node(path: str, cell_id: str) -> str:
    """
    Delete a node (or edge) by ID. Also removes any edges that were
    connected to the deleted node to keep the diagram consistent.

    Args:
        path:    Full path to the .drawio file.
        cell_id: ID of the cell to delete.

    Returns:
        Confirmation string (including orphan count), or an error message.
    """
    try:
        tree    = load_diagram(path)
        root_el = get_root_cell(tree)

        target = root_el.find(f"mxCell[@id='{cell_id}']")
        if target is None:
            return f"ERROR: Cell id={cell_id} not found."
        root_el.remove(target)

        orphans = [
            c for c in root_el.findall("mxCell")
            if c.get("source") == cell_id or c.get("target") == cell_id
        ]
        for orphan in orphans:
            root_el.remove(orphan)

        save_diagram(tree, path)
        msg = f"Deleted cell id={cell_id}"
        if orphans:
            msg += f" + {len(orphans)} orphaned edge(s)"
        return msg
    except Exception as e:
        return f"ERROR: {e}"


# ==============================================================================
# LAYOUT
# ==============================================================================

def apply_layout(
    path: str,
    direction: str = "TB",
    start_x: int = 80,
    start_y: int = 80,
    layer_spacing: int = 180,
    node_spacing: int = 100,
) -> str:
    """
    Arrange all vertices using a layered graph algorithm.

    Layers are determined by edge relationships (BFS from root nodes).
    Disconnected or cyclic nodes are placed in a trailing layer.
    Existing node dimensions are preserved; only positions change.

    Supported directions:
        TB  Top-to-Bottom  (default)
        BT  Bottom-to-Top
        LR  Left-to-Right
        RL  Right-to-Left

    Args:
        path:          Full path to the .drawio file.
        direction:     Layout direction: TB | BT | LR | RL.
        start_x:       Canvas X origin for the first layer.
        start_y:       Canvas Y origin for the first layer.
        layer_spacing: Pixel gap between consecutive layers.
        node_spacing:  Pixel gap between sibling nodes in the same layer.

    Returns:
        Confirmation string, or an error message.
    """
    try:
        direction = direction.upper().strip()
        if direction not in {"TB", "BT", "LR", "RL"}:
            return f"ERROR: Unsupported direction '{direction}'. Use TB, BT, LR, or RL."

        tree    = load_diagram(path)
        root_el = get_root_cell(tree)

        # ── collect vertices and edges ─────────────────────────────────────
        vertices: dict = {}
        edges:    list = []

        for cell in root_el.findall("mxCell"):
            cid = cell.get("id")
            if cid in ("0", "1"):
                continue

            if cell.get("vertex") == "1":
                geo    = cell.find("mxGeometry")
                width  = int(float(geo.get("width",  "120"))) if geo is not None else 120
                height = int(float(geo.get("height", "60")))  if geo is not None else 60
                old_x  = int(float(geo.get("x", "0")))        if geo is not None else 0
                old_y  = int(float(geo.get("y", "0")))        if geo is not None else 0
                vertices[cid] = {
                    "cell": cell, "geo": geo,
                    "width": width, "height": height,
                    "label": cell.get("value", ""),
                    "old_x": old_x, "old_y": old_y,
                }
            elif cell.get("edge") == "1":
                src, tgt = cell.get("source"), cell.get("target")
                if src and tgt:
                    edges.append((src, tgt))

        if not vertices:
            return "ERROR: No vertices found in diagram."

        # ── build adjacency structures ─────────────────────────────────────
        outgoing:       dict = defaultdict(list)
        incoming_count: dict = defaultdict(int)

        for vid in vertices:
            incoming_count[vid] = 0
        for src, tgt in edges:
            if src in vertices and tgt in vertices:
                outgoing[src].append(tgt)
                incoming_count[tgt] += 1

        # ── BFS layer assignment ───────────────────────────────────────────
        roots = [vid for vid in vertices if incoming_count[vid] == 0]
        if not roots:
            roots = sorted(
                vertices.keys(),
                key=lambda v: (vertices[v]["old_y"], vertices[v]["old_x"], v),
            )

        layer_of: dict = {}
        q = deque()
        for r in roots:
            if r not in layer_of:
                layer_of[r] = 0
                q.append(r)

        while q:
            cur = q.popleft()
            for nbr in outgoing[cur]:
                depth = layer_of[cur] + 1
                if nbr not in layer_of or depth > layer_of[nbr]:
                    layer_of[nbr] = depth
                    q.append(nbr)

        # ── place disconnected / cyclic leftovers ─────────────────────────
        unassigned = [vid for vid in vertices if vid not in layer_of]
        if unassigned:
            base = (max(layer_of.values()) + 1) if layer_of else 0
            for idx, vid in enumerate(
                sorted(unassigned, key=lambda v: (vertices[v]["old_y"], vertices[v]["old_x"], v))
            ):
                layer_of[vid] = base + idx

        # ── group by layer and sort within layer ──────────────────────────
        layers: dict = defaultdict(list)
        for vid, lyr in layer_of.items():
            layers[lyr].append(vid)

        for lyr in layers:
            layers[lyr].sort(key=lambda v: (
                vertices[v]["old_y"], vertices[v]["old_x"],
                vertices[v]["label"].lower(), v,
            ))

        # ── position each node ────────────────────────────────────────────
        for layer_index, layer_id in enumerate(sorted(layers.keys())):
            cursor = 0
            for vid in layers[layer_id]:
                item = vertices[vid]
                geo  = item["geo"]
                if geo is None:
                    geo = ET.SubElement(item["cell"], "mxGeometry")
                    geo.set("as", "geometry")
                    item["geo"] = geo

                if direction == "TB":
                    x = start_x + cursor
                    y = start_y + layer_index * layer_spacing
                    cursor += item["width"] + node_spacing
                elif direction == "BT":
                    x = start_x + cursor
                    y = start_y - layer_index * layer_spacing
                    cursor += item["width"] + node_spacing
                elif direction == "LR":
                    x = start_x + layer_index * layer_spacing
                    y = start_y + cursor
                    cursor += item["height"] + node_spacing
                else:  # RL
                    x = start_x - layer_index * layer_spacing
                    y = start_y + cursor
                    cursor += item["height"] + node_spacing

                geo.set("x",      str(x))
                geo.set("y",      str(y))
                geo.set("width",  str(item["width"]))
                geo.set("height", str(item["height"]))

        save_diagram(tree, path)
        return f"Auto-layout applied: direction={direction}, layers={len(layers)}, nodes={len(vertices)}"

    except Exception as e:
        return f"ERROR: {e}"