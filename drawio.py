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
# DEVICE ROLE DEFINITIONS
# ==============================================================================

#: Maps a device role name to its canonical diagram layer (int) or
#: the string "sidebar" for management / monitoring nodes that are
#: placed in a dedicated column outside the main grid.
ROLE_LAYER: dict[str, int | str] = {
    # Core fabric
    "spine":              0,
    "core_switch":        0,
    "router":             0,
    # Perimeter / security (placed in a separate left column at layer 0 height)
    "firewall":           0,
    "load_balancer":      1,
    # Aggregation / distribution
    "border_leaf":        1,
    # Access / ToR
    "leaf":               2,
    # Compute / workload
    "gpu_node":           3,
    "storage_node":       3,
    "compute_node":       3,
    # Out-of-band (sidebar column, not in main grid)
    "management_switch":  "sidebar",
    "monitoring_node":    "sidebar",
}

#: Default style used when a role/profile lookup produces no result.
DEFAULT_STYLE: str = "rounded=1;whiteSpace=wrap;html=1;"

# Style resolution is delegated to styles.py.
# ROLE_STYLE and LINK_STYLE dicts have been removed — all callers use:
#   styles.resolve_node_style(role, profile)
#   styles.resolve_edge_style(link_type)


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


# ==============================================================================
# PHASE 2 — NETWORK-AWARE DEVICE & LINK PRIMITIVES
# ==============================================================================

def add_device(
    path: str,
    hostname: str,
    role: str,
    vendor: str = "",
    platform: str = "",
    site: str = "",
    zone: str = "",
    redundancy_group: str = "",
    x: int = 100,
    y: int = 100,
    width: int = 78,
    height: int = 78,
    style: str | None = None,
) -> str:
    """
    Add a network device node to the diagram.

    The device carries structured metadata stored as a JSON string in the
    draw.io ``tooltip`` attribute so that it survives file round-trips and
    is visible in the draw.io UI on hover.

    The ``layer`` field in the metadata is derived automatically from
    ``ROLE_LAYER[role]`` and is stored for reference by layout functions.

    If ``style`` is not supplied the role's default style from
    ``ROLE_STYLE`` is used, falling back to ``DEFAULT_STYLE``.

    Args:
        path:             Full path to the .drawio file.
        hostname:         Device hostname (used as the cell label).
        role:             Device role key — must be a key in ROLE_LAYER.
                          E.g. 'spine', 'leaf', 'firewall', 'gpu_node'.
        vendor:           Vendor name (e.g. 'NVIDIA', 'Fortinet', 'Cumulus').
        platform:         Platform / model (e.g. 'H200', 'FortiGate-4201F').
        site:             Site identifier (e.g. 'DC1', 'DC2').
        zone:             Security or network zone (e.g. 'DMZ', 'PROD').
        redundancy_group: HA / MLAG / ECMP group identifier.
        x:                X position in pixels.
        y:                Y position in pixels.
        width:            Node width in pixels (default 78 for icon shapes).
        height:           Node height in pixels (default 78 for icon shapes).
        style:            Explicit draw.io style string. If omitted the
                          role default from ROLE_STYLE is used.

    Returns:
        The new cell's ID on success, or an error message prefixed 'ERROR:'.
    """
    if role not in ROLE_LAYER:
        known = ", ".join(sorted(ROLE_LAYER.keys()))
        return f"ERROR: Unknown role '{role}'. Known roles: {known}"

    import styles as _styles
    resolved_style = style or _styles.resolve_node_style(role, "minimal")
    layer          = ROLE_LAYER[role]

    metadata = {
        "hostname":         hostname,
        "role":             role,
        "vendor":           vendor,
        "platform":         platform,
        "layer":            layer,
        "site":             site,
        "zone":             zone,
        "redundancy_group": redundancy_group,
    }

    try:
        tree    = load_diagram(path)
        root_el = get_root_cell(tree)
        new_id  = next_id(root_el)

        cell = ET.SubElement(root_el, "mxCell")
        cell.set("id",      new_id)
        cell.set("value",   hostname)
        cell.set("style",   resolved_style)
        cell.set("tooltip", json.dumps(metadata))
        cell.set("vertex",  "1")
        cell.set("parent",  "1")

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


def add_link(
    path: str,
    source_id: str,
    target_id: str,
    link_type: str = "default",
    label: str = "",
) -> str:
    """
    Add a network link (edge) between two device nodes.

    The visual style is resolved from ``LINK_STYLE[link_type]``.
    Unknown link types fall back to ``LINK_STYLE['default']``.

    Supported link types:
        fabric      — spine↔leaf interconnect (thick blue)
        uplink      — leaf↔compute / access uplinks
        management  — out-of-band management connections (dashed amber)
        default     — generic link

    Args:
        path:      Full path to the .drawio file.
        source_id: Cell ID of the source device.
        target_id: Cell ID of the target device.
        link_type: Logical link type key (see above).
        label:     Optional label shown on the link.

    Returns:
        The new edge's ID on success, or an error message prefixed 'ERROR:'.
    """
    import styles as _styles
    resolved_style = _styles.resolve_edge_style(link_type)
    return insert_edge(path, source_id, target_id, label, resolved_style)


# ==============================================================================
# PHASE 2 — TOPOLOGY BUILDER: SPINE-LEAF FABRIC
# ==============================================================================

def build_spine_leaf_fabric(
    path: str,
    spine_count: int = 2,
    leaf_count: int = 4,
    compute_per_leaf: int = 2,
    spine_names: list[str] | None = None,
    leaf_names: list[str] | None = None,
    compute_names: list[str] | None = None,
    site: str = "DC1",
    vendor: str = "generic",
    platform: str = "",
    style_profile: str = "minimal",
    node_width: int = 78,
    node_height: int = 78,
    layer_spacing: int = 200,
    node_spacing: int = 60,
    start_x: int = 80,
    start_y: int = 80,
) -> str:
    """
    Build a complete spine-leaf fabric topology diagram from scratch.

    Layout
    ------
    The fabric is arranged on a three-row grid::

        Row 0 (Y = start_y)                  — Spine switches
        Row 1 (Y = start_y + layer_spacing)  — Leaf switches
        Row 2 (Y = start_y + 2*layer_spacing)— Compute / GPU nodes

    Within each row nodes are evenly spaced along the X axis, centred
    relative to whichever row has the most nodes.

    Connectivity
    ------------
    * Every spine is connected to every leaf  (full-mesh fabric links).
    * Every compute node is connected to its parent leaf  (uplinks).

    All created node IDs are returned in the summary so they can be
    referenced by subsequent ``add_device`` / ``add_link`` calls.

    Args:
        path:             Full path to the .drawio file. The file is
                          created (blank) if it does not exist.
        spine_count:      Number of spine switches (default 2).
        leaf_count:       Number of leaf switches  (default 4).
        compute_per_leaf: Compute nodes per leaf   (default 2).
        spine_names:      Optional explicit hostnames for spines.
                          Auto-generated as spine01, spine02 … if omitted.
        leaf_names:       Optional explicit hostnames for leaves.
        compute_names:    Optional explicit hostnames for compute nodes.
                          Must have exactly leaf_count × compute_per_leaf
                          entries if supplied.
        site:             Site label embedded in each device's metadata.
        vendor:           Vendor string applied to all devices.
        platform:         Platform string applied to all devices.
        style_profile:    Style profile name (default 'minimal').
        node_width:       Node width in pixels  (default 78).
        node_height:      Node height in pixels (default 78).
        layer_spacing:    Vertical gap between rows in pixels (default 200).
        node_spacing:     Horizontal gap between sibling nodes (default 60).
        start_x:          Left margin for the canvas grid (default 80).
        start_y:          Top margin for the canvas grid  (default 80).

    Returns:
        A JSON summary string containing counts and all created cell IDs,
        or an error message prefixed 'ERROR:'.
    """
    try:
        import styles as _styles
        # ── ensure the file exists ─────────────────────────────────────────
        p = Path(path)
        if not p.exists():
            write_file(path, blank_template("Spine-Leaf Fabric"))

        # ── generate default names if not provided ─────────────────────────
        total_compute = leaf_count * compute_per_leaf

        if spine_names is None:
            spine_names = [f"spine{i+1:02d}" for i in range(spine_count)]
        if leaf_names is None:
            leaf_names = [f"leaf{i+1:02d}" for i in range(leaf_count)]
        if compute_names is None:
            compute_names = [
                f"compute{i+1:02d}" for i in range(total_compute)
            ]

        # ── validate name counts ───────────────────────────────────────────
        if len(spine_names) != spine_count:
            return f"ERROR: spine_names has {len(spine_names)} entries, expected {spine_count}."
        if len(leaf_names) != leaf_count:
            return f"ERROR: leaf_names has {len(leaf_names)} entries, expected {leaf_count}."
        if len(compute_names) != total_compute:
            return (
                f"ERROR: compute_names has {len(compute_names)} entries, "
                f"expected {leaf_count} × {compute_per_leaf} = {total_compute}."
            )

        # ── grid sizing ────────────────────────────────────────────────────
        # Centre each row relative to the widest row.
        max_nodes    = max(spine_count, leaf_count, total_compute)
        row_width    = max_nodes * node_width + (max_nodes - 1) * node_spacing

        def _row_x(count: int, idx: int) -> int:
            """Return X for the idx-th node in a row of `count` nodes."""
            row_span = count * node_width + (count - 1) * node_spacing
            offset   = (row_width - row_span) // 2
            return start_x + offset + idx * (node_width + node_spacing)

        row_y = [
            start_y,
            start_y + layer_spacing,
            start_y + 2 * layer_spacing,
        ]

        created: dict = {"spines": {}, "leaves": {}, "compute": {}, "links": []}

        # ── add spine nodes ────────────────────────────────────────────────
        for i, name in enumerate(spine_names):
            cid = add_device(
                path=path, hostname=name, role="spine",
                vendor=vendor, platform=platform, site=site,
                x=_row_x(spine_count, i), y=row_y[0],
                width=node_width, height=node_height,
                style=_styles.resolve_node_style("spine", style_profile),
            )
            if cid.startswith("ERROR"):
                return cid
            created["spines"][name] = cid

        # ── add leaf nodes ─────────────────────────────────────────────────
        for i, name in enumerate(leaf_names):
            cid = add_device(
                path=path, hostname=name, role="leaf",
                vendor=vendor, platform=platform, site=site,
                x=_row_x(leaf_count, i), y=row_y[1],
                width=node_width, height=node_height,
                style=_styles.resolve_node_style("leaf", style_profile),
            )
            if cid.startswith("ERROR"):
                return cid
            created["leaves"][name] = cid

        # ── add compute nodes ──────────────────────────────────────────────
        for i, name in enumerate(compute_names):
            cid = add_device(
                path=path, hostname=name, role="compute_node",
                vendor=vendor, platform=platform, site=site,
                x=_row_x(total_compute, i), y=row_y[2],
                width=node_width, height=node_height,
                style=_styles.resolve_node_style("compute_node", style_profile),
            )
            if cid.startswith("ERROR"):
                return cid
            created["compute"][name] = cid

        # ── spine ↔ leaf full-mesh fabric links ───────────────────────────
        for spine_name, spine_id in created["spines"].items():
            for leaf_name, leaf_id in created["leaves"].items():
                eid = add_link(path, spine_id, leaf_id, link_type="fabric")
                if eid.startswith("ERROR"):
                    return eid
                created["links"].append(
                    {"type": "fabric", "from": spine_name, "to": leaf_name, "id": eid}
                )

        # ── leaf ↔ compute uplinks ─────────────────────────────────────────
        leaf_list = list(created["leaves"].items())
        for leaf_idx, (leaf_name, leaf_id) in enumerate(leaf_list):
            start_c = leaf_idx * compute_per_leaf
            for c_offset in range(compute_per_leaf):
                c_name = compute_names[start_c + c_offset]
                c_id   = created["compute"][c_name]
                eid    = add_link(path, leaf_id, c_id, link_type="uplink")
                if eid.startswith("ERROR"):
                    return eid
                created["links"].append(
                    {"type": "uplink", "from": leaf_name, "to": c_name, "id": eid}
                )

        # ── return summary ─────────────────────────────────────────────────
        summary = {
            "status":        "ok",
            "path":          str(p.resolve()),
            "spine_count":   spine_count,
            "leaf_count":    leaf_count,
            "compute_count": total_compute,
            "link_count":    len(created["links"]),
            "nodes":         created,
        }
        return json.dumps(summary, indent=2)

    except Exception as e:
        return f"ERROR: {e}"


# ==============================================================================
# PHASE 3 — DIAGRAM FROM MODEL
# ==============================================================================

def build_diagram_from_model(path: str, yaml_path: str) -> str:
    """
    Build a draw.io diagram from a YAML topology model file.

    Execution order:
        1. Parse YAML into a TopologyModel  (models.py)
        2. Validate the model               (validators.py)
        3. Hard fail with JSON report if any errors found
        4. Resolve style profile            (styles.py)
        5. Dispatch to the correct builder  (this module)
        6. Return JSON summary with warnings embedded

    The ``meta.topology`` key in the YAML selects the builder.
    If missing, defaults to ``spine_leaf`` and emits a W001 warning.

    Args:
        path:      Full path where the .drawio file will be written.
        yaml_path: Full path to the YAML topology model file.

    Returns:
        JSON string — either a build summary (status: ok) or a full
        error report (status: error).
    """
    import json as _json
    import models as _models
    import validators as _validators

    # ── parse ─────────────────────────────────────────────────────────────────
    try:
        model = _models.load_model(yaml_path)
    except FileNotFoundError as e:
        return _json.dumps({
            "status": "error",
            "errors": [{"code": "E099", "field": "yaml_path", "message": str(e)}],
            "warnings": [],
        }, indent=2)
    except Exception as e:
        return _json.dumps({
            "status": "error",
            "errors": [{"code": "E098", "field": "yaml_path", "message": f"YAML parse error: {e}"}],
            "warnings": [],
        }, indent=2)

    # ── validate ──────────────────────────────────────────────────────────────
    result = _validators.validate(model)

    if not result.ok:
        report = result.to_dict()
        return _json.dumps(report, indent=2)

    # ── dispatch to builder ───────────────────────────────────────────────────
    topology = model.meta.topology

    if topology == "spine_leaf":
        # Derive builder parameters from model devices
        spines   = [d.hostname for d in model.devices if d.role == "spine"]
        leaves   = [d.hostname for d in model.devices if d.role == "leaf"]
        computes = [d.hostname for d in model.devices if d.role == "compute_node"]

        # Infer compute_per_leaf — use 0 if no compute nodes declared
        compute_per_leaf = (len(computes) // len(leaves)) if leaves and computes else 0

        # Representative site/vendor/platform from first spine (or first device)
        anchor  = model.devices[0] if model.devices else None
        site     = anchor.site     if anchor else ""
        vendor   = anchor.vendor   if anchor else ""
        platform = anchor.platform if anchor else ""

        build_result_str = build_spine_leaf_fabric(
            path             = path,
            spine_count      = len(spines),
            leaf_count       = len(leaves),
            compute_per_leaf = compute_per_leaf,
            spine_names      = spines   or None,
            leaf_names       = leaves   or None,
            compute_names    = computes or None,
            site             = site,
            vendor           = vendor,
            platform         = platform,
            style_profile    = model.meta.style_profile,
        )

        # build_spine_leaf_fabric returns JSON on success or "ERROR: ..." on fail
        if build_result_str.startswith("ERROR"):
            return _json.dumps({
                "status":   "error",
                "errors":   [{"code": "E097", "field": "build", "message": build_result_str}],
                "warnings": result.to_dict()["warnings"],
            }, indent=2)

        build_summary = _json.loads(build_result_str)
        build_summary["warnings"] = result.to_dict()["warnings"]
        return _json.dumps(build_summary, indent=2)

    # ── unsupported topology (should be caught by validator, safety net) ──────
    return _json.dumps({
        "status": "error",
        "errors": [{"code": "E006", "field": "meta.topology",
                    "message": f"No builder available for topology '{topology}'."}],
        "warnings": result.to_dict()["warnings"],
    }, indent=2)