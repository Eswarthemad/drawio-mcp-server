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
    # Core fabric / WAN
    "spine":              0,
    "core_switch":        0,
    "router":             0,
    "wan_router":         0,
    # Perimeter / security
    "internet":          -1,   # above firewall — topmost tier
    "firewall":           0,
    "load_balancer":      1,
    # Aggregation / distribution / spoke
    "border_leaf":        1,
    "branch_router":      1,
    # Access / ToR
    "leaf":               2,
    # Application / workload
    "application_server": 3,
    "gpu_node":           3,
    "storage_node":       3,
    "compute_node":       3,
    # Database / persistence
    "database_node":      4,
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
    style_profile: str = "minimal",
    parent_id: str = "1",
) -> str:
    """
    Add a network device node to the diagram.

    The device carries structured metadata stored as a JSON string in the
    draw.io ``tooltip`` attribute so that it survives file round-trips and
    is visible in the draw.io UI on hover.

    The ``layer`` field in the metadata is derived automatically from
    ``ROLE_LAYER[role]`` and is stored for reference by layout functions.

    If ``style`` is not supplied the role's default style from
    ``styles.resolve_node_style(role, style_profile)`` is used.

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
                          role default from styles.resolve_node_style() is used.
        style_profile:    Style profile for automatic style resolution (default 'minimal').
        parent_id:        Parent cell ID. Use '1' for root (default).
                          Pass a container cell ID to place this device inside a container.

    Returns:
        The new cell's ID on success, or an error message prefixed 'ERROR:'.
    """
    if role not in ROLE_LAYER:
        known = ", ".join(sorted(ROLE_LAYER.keys()))
        return f"ERROR: Unknown role '{role}'. Known roles: {known}"

    import styles as _styles
    resolved_style = style or _styles.resolve_node_style(role, style_profile)
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
        cell.set("parent",  parent_id)

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

    # ── hub_spoke dispatch ────────────────────────────────────────────────────
    if topology == "hub_spoke":
        mode = model.meta.topology_mode or "tenant_fabric"
        hubs    = [d.hostname for d in model.devices if d.role in ("spine", "wan_router")]
        spokes  = [d.hostname for d in model.devices if d.role in ("leaf", "branch_router")]
        eps     = [d.hostname for d in model.devices if d.role in ("compute_node", "gpu_node", "storage_node")]
        ep_per  = (len(eps) // len(spokes)) if spokes else 2

        build_result_str = build_hub_spoke(
            path=path,
            mode=mode,
            hub_count=len(hubs),
            spoke_count=len(spokes),
            endpoint_per_spoke=ep_per,
            hub_names=hubs or None,
            spoke_names=spokes or None,
            endpoint_names=eps or None,
            site=model.sites[0].name if model.sites else "",
            style_profile=model.meta.style_profile,
        )
        if build_result_str.startswith("ERROR"):
            return _json.dumps({
                "status":   "error",
                "errors":   [{"code": "E097", "field": "build", "message": build_result_str}],
                "warnings": result.to_dict()["warnings"],
            }, indent=2)
        build_summary = _json.loads(build_result_str)
        build_summary["warnings"] = result.to_dict()["warnings"]
        return _json.dumps(build_summary, indent=2)

    # ── security_stack dispatch ───────────────────────────────────────────────
    if topology == "security_stack":
        fws  = [d.hostname for d in model.devices if d.role == "firewall"]
        lbs  = [d.hostname for d in model.devices if d.role == "load_balancer"]
        apps = [d.hostname for d in model.devices if d.role == "application_server"]
        dbs  = [d.hostname for d in model.devices if d.role == "database_node"]
        mons = [d.hostname for d in model.devices if d.role == "monitoring_node"]
        inet = any(d.role == "internet" for d in model.devices)

        build_result_str = build_security_stack(
            path=path,
            firewall_count=len(fws) or 2,
            lb_count=len(lbs) or 2,
            app_count=len(apps) or 4,
            db_count=len(dbs) or 2,
            include_internet=inet,
            include_lb=bool(lbs),
            monitoring_count=len(mons) or 1,
            firewall_names=fws or None,
            lb_names=lbs or None,
            app_names=apps or None,
            db_names=dbs or None,
            monitoring_names=mons or None,
            site=model.sites[0].name if model.sites else "",
            style_profile=model.meta.style_profile,
        )
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

# ==============================================================================
# PHASE 4 — CONTAINERS, HUB-SPOKE, SECURITY STACK
# ==============================================================================

def add_container(
    path:          str,
    label:         str,
    x:             int  = 60,
    y:             int  = 60,
    width:         int  = 400,
    height:        int  = 300,
    style_profile: str  = "minimal",
) -> str:
    """
    Add a labelled container group to an existing diagram.

    The container is an mxCell with container=1.  Child nodes should set their
    parent to this container's returned ID via add_device(..., parent_id=<id>).

    Args:
        path:          Full path to the .drawio file.
        label:         Text label displayed in the container header.
        x:             Top-left X position (default 60).
        y:             Top-left Y position (default 60).
        width:         Container width in pixels (default 400).
        height:        Container height in pixels (default 300).
        style_profile: Style profile for container colour ('minimal' or 'dark').

    Returns:
        The new container cell's ID on success, or "ERROR: ..." on failure.
    """
    try:
        from styles import resolve_container_style
        style   = resolve_container_style(style_profile)
        tree    = load_diagram(path)
        root    = get_root_cell(tree)
        cell_id = next_id(root)
        parent_cell = root.find(".//mxCell[@id='1']")
        parent_id   = "1" if parent_cell is not None else "0"

        cell = ET.SubElement(root, "mxCell", {
            "id":        cell_id,
            "value":     label,
            "style":     style,
            "vertex":    "1",
            "parent":    parent_id,
            "container": "1",
        })
        ET.SubElement(cell, "mxGeometry", {
            "x":      str(x),
            "y":      str(y),
            "width":  str(width),
            "height": str(height),
            "as":     "geometry",
        })
        save_diagram(tree, path)
        return cell_id
    except Exception as exc:
        return f"ERROR: {exc}"


def group_nodes(
    path:          str,
    cell_ids:      list[str],
    label:         str  = "",
    padding:       int  = 40,
    style_profile: str  = "minimal",
) -> str:
    """
    Wrap existing nodes inside a new container group.

    Computes a bounding box around all listed cell IDs, adds a container
    with that bounding box (plus padding), and re-parents all cells into it.

    Args:
        path:          Full path to the .drawio file.
        cell_ids:      List of existing cell IDs to group.
        label:         Label for the container header.
        padding:       Pixel padding around the bounding box (default 40).
        style_profile: Style profile for the container.

    Returns:
        The new container cell's ID on success, or "ERROR: ..." on failure.
    """
    try:
        from styles import resolve_container_style
        tree = load_diagram(path)
        root = get_root_cell(tree)

        # ── gather geometry of target cells ──────────────────────────────────
        cell_map = {c.get("id"): c for c in root.iter("mxCell")}
        xs, ys, x2s, y2s = [], [], [], []

        for cid in cell_ids:
            cell = cell_map.get(cid)
            if cell is None:
                return f"ERROR: Cell '{cid}' not found in diagram."
            geo = cell.find("mxGeometry")
            if geo is None:
                continue
            cx = float(geo.get("x", 0))
            cy = float(geo.get("y", 0))
            cw = float(geo.get("width",  120))
            ch = float(geo.get("height", 60))
            xs.append(cx);  ys.append(cy)
            x2s.append(cx + cw); y2s.append(cy + ch)

        if not xs:
            return "ERROR: No positioned cells found in provided IDs."

        HEADER = 30   # swimlane header height
        bx = min(xs)  - padding
        by = min(ys)  - padding - HEADER
        bw = max(x2s) - bx - padding + padding * 2
        bh = max(y2s) - (by + HEADER) + padding * 2 + HEADER

        # ── create the container ─────────────────────────────────────────────
        style     = resolve_container_style(style_profile)
        new_id    = next_id(root)
        parent_cell = root.find(".//mxCell[@id='1']")
        parent_id   = "1" if parent_cell is not None else "0"

        cont = ET.SubElement(root, "mxCell", {
            "id":        new_id,
            "value":     label,
            "style":     style,
            "vertex":    "1",
            "parent":    parent_id,
            "container": "1",
        })
        ET.SubElement(cont, "mxGeometry", {
            "x":      str(int(bx)),
            "y":      str(int(by)),
            "width":  str(int(bw)),
            "height": str(int(bh)),
            "as":     "geometry",
        })

        # ── re-parent target cells into the new container ─────────────────────
        for cid in cell_ids:
            cell = cell_map.get(cid)
            if cell is None:
                continue
            cell.set("parent", new_id)
            # Adjust geometry to be relative to container
            geo = cell.find("mxGeometry")
            if geo is not None:
                geo.set("x", str(float(geo.get("x", 0)) - bx))
                geo.set("y", str(float(geo.get("y", 0)) - (by + HEADER)))

        save_diagram(tree, path)
        return new_id
    except Exception as exc:
        return f"ERROR: {exc}"


def build_hub_spoke(
    path:          str,
    mode:          str        = "tenant_fabric",
    hub_count:     int        = 2,
    spoke_count:   int        = 4,
    endpoint_per_spoke: int   = 2,
    hub_names:     list[str]  | None = None,
    spoke_names:   list[str]  | None = None,
    endpoint_names: list[str] | None = None,
    site:          str        = "",
    style_profile: str        = "minimal",
) -> str:
    """
    Build a hub-spoke topology diagram.

    Two modes:
        tenant_fabric — hub spines + spoke leaves + compute endpoints.
                        Full-mesh hub-to-spoke, spoke-to-endpoint wiring.
        wan_branch    — WAN router hub + branch routers + endpoints.
                        Hub connects to all branches via WAN links.

    Args:
        path:               Full path to write the .drawio file.
        mode:               'tenant_fabric' or 'wan_branch'.
        hub_count:          Number of hub nodes (default 2).
        spoke_count:        Number of spoke nodes (default 4).
        endpoint_per_spoke: Endpoints per spoke (default 2).
        hub_names:          Override hub hostnames.
        spoke_names:        Override spoke hostnames.
        endpoint_names:     Override endpoint hostnames (flat list, len = spoke_count × endpoint_per_spoke).
        site:               Site label for all devices.
        style_profile:      Visual style profile.

    Returns:
        JSON summary string on success, or "ERROR: ..." on failure.
    """
    try:
        import json as _j
        from styles import resolve_node_style, resolve_edge_style

        # ── mode config ───────────────────────────────────────────────────────
        mode = (mode or "tenant_fabric").lower().strip()
        if mode not in ("tenant_fabric", "wan_branch"):
            return f"ERROR: Unsupported mode '{mode}'. Use 'tenant_fabric' or 'wan_branch'."

        if mode == "tenant_fabric":
            hub_role      = "spine"
            spoke_role    = "leaf"
            endpoint_role = "compute_node"
            hub_prefix    = "hub"
            spoke_prefix  = "spoke"
            ep_prefix     = "compute"
            hub_link_type = "fabric"
            ep_link_type  = "uplink"
        else:  # wan_branch
            hub_role      = "wan_router"
            spoke_role    = "branch_router"
            endpoint_role = "compute_node"
            hub_prefix    = "wan-hub"
            spoke_prefix  = "branch"
            ep_prefix     = "endpoint"
            hub_link_type = "wan"
            ep_link_type  = "uplink"

        # ── name generation ───────────────────────────────────────────────────
        hubs    = hub_names    or [f"{hub_prefix}{i+1:02d}"   for i in range(hub_count)]
        spokes  = spoke_names  or [f"{spoke_prefix}{i+1:02d}" for i in range(spoke_count)]
        total_ep = spoke_count * endpoint_per_spoke
        eps_flat = endpoint_names or [
            f"{ep_prefix}{i+1:02d}" for i in range(total_ep)
        ]
        # Group endpoints per spoke
        eps = [eps_flat[i * endpoint_per_spoke:(i + 1) * endpoint_per_spoke]
               for i in range(spoke_count)]

        # ── layout constants ──────────────────────────────────────────────────
        NODE_W       = 120;  NODE_H  = 60
        H_GAP        = 160;  V_GAP   = 160
        MARGIN_X     = 100;  MARGIN_Y = 80

        hub_y    = MARGIN_Y
        spoke_y  = hub_y   + NODE_H + V_GAP
        ep_y     = spoke_y + NODE_H + V_GAP

        hub_total_w   = hub_count   * NODE_W + (hub_count   - 1) * H_GAP
        spoke_total_w = spoke_count * NODE_W + (spoke_count - 1) * H_GAP
        canvas_w      = max(hub_total_w, spoke_total_w) + MARGIN_X * 2

        hub_start_x   = (canvas_w - hub_total_w)   // 2
        spoke_start_x = (canvas_w - spoke_total_w) // 2

        # ── create diagram ────────────────────────────────────────────────────
        write_file(path, blank_template("Hub-Spoke"))
        hub_ids   : dict[str, str] = {}
        spoke_ids : dict[str, str] = {}
        ep_ids    : dict[str, str] = {}

        for i, name in enumerate(hubs):
            x = hub_start_x + i * (NODE_W + H_GAP)
            cid = add_device(
                path=path, hostname=name, role=hub_role,
                x=x, y=hub_y, width=NODE_W, height=NODE_H,
                site=site, style_profile=style_profile,
            )
            hub_ids[name] = cid

        for i, name in enumerate(spokes):
            x = spoke_start_x + i * (NODE_W + H_GAP)
            cid = add_device(
                path=path, hostname=name, role=spoke_role,
                x=x, y=spoke_y, width=NODE_W, height=NODE_H,
                site=site, style_profile=style_profile,
            )
            spoke_ids[name] = cid

            ep_total_w = endpoint_per_spoke * NODE_W + (endpoint_per_spoke - 1) * H_GAP
            ep_start_x = x + (NODE_W - ep_total_w) // 2
            for j, ep_name in enumerate(eps[i]):
                ex = ep_start_x + j * (NODE_W + H_GAP)
                ecid = add_device(
                    path=path, hostname=ep_name, role=endpoint_role,
                    x=ex, y=ep_y, width=NODE_W, height=NODE_H,
                    site=site, style_profile=style_profile,
                )
                ep_ids[ep_name] = ecid

        # ── links: hub full-mesh to each spoke ────────────────────────────────
        edge_style = resolve_edge_style(hub_link_type)
        link_count = 0
        for h_name, h_id in hub_ids.items():
            for s_name, s_id in spoke_ids.items():
                insert_edge(path, h_id, s_id, label="", style=edge_style)
                link_count += 1

        # ── links: spoke to its endpoints ─────────────────────────────────────
        ep_style = resolve_edge_style(ep_link_type)
        for i, s_name in enumerate(spokes):
            s_id = spoke_ids[s_name]
            for ep_name in eps[i]:
                insert_edge(path, s_id, ep_ids[ep_name], label="", style=ep_style)
                link_count += 1

        total_nodes = len(hub_ids) + len(spoke_ids) + len(ep_ids)
        return _j.dumps({
            "status":        "ok",
            "warnings":      [],
            "mode":          mode,
            "hub_count":     len(hub_ids),
            "spoke_count":   len(spoke_ids),
            "endpoint_count": len(ep_ids),
            "node_count":    total_nodes,
            "link_count":    link_count,
            "total_cells":   total_nodes + link_count,
        }, indent=2)

    except Exception as exc:
        return f"ERROR: {exc}"


def build_security_stack(
    path:              str,
    firewall_count:    int        = 2,
    lb_count:          int        = 2,
    app_count:         int        = 4,
    db_count:          int        = 2,
    include_internet:  bool       = True,
    include_lb:        bool       = True,
    monitoring_count:  int        = 1,
    firewall_names:    list[str]  | None = None,
    lb_names:          list[str]  | None = None,
    app_names:         list[str]  | None = None,
    db_names:          list[str]  | None = None,
    monitoring_names:  list[str]  | None = None,
    site:              str        = "",
    style_profile:     str        = "minimal",
) -> str:
    """
    Build a security-zone stack diagram with configurable tiers.

    Tiers (top to bottom):
        -1  Internet gateway        (optional — include_internet)
         0  Firewall HA pair
         1  Load balancers          (optional — include_lb)
         2  Application servers
         3  Database / storage
         Sidebar  Monitoring nodes

    Tier -1 to 0 linked with WAN style.
    Tiers 0→1, 1→2 linked with fabric style.
    Tiers 2→3 linked with uplink style.
    Monitoring sidebar connected to firewall with management style.

    Args:
        path:             Full path to write the .drawio file.
        firewall_count:   Number of firewalls (default 2, HA pair).
        lb_count:         Number of load balancers (default 2).
        app_count:        Number of application servers (default 4).
        db_count:         Number of database nodes (default 2).
        include_internet: Add an internet gateway node at top (default True).
        include_lb:       Include the load balancer tier (default True).
        monitoring_count: Number of monitoring nodes in sidebar (default 1).
        firewall_names:   Override firewall hostnames.
        lb_names:         Override load balancer hostnames.
        app_names:        Override application server hostnames.
        db_names:         Override database node hostnames.
        monitoring_names: Override monitoring node hostnames.
        site:             Site label for all devices.
        style_profile:    Visual style profile.

    Returns:
        JSON summary string on success, or "ERROR: ..." on failure.
    """
    try:
        import json as _j
        from styles import resolve_edge_style

        # ── name generation ───────────────────────────────────────────────────
        fw_names  = firewall_names   or [f"fw{i+1:02d}"      for i in range(firewall_count)]
        lbs       = lb_names         or [f"lb{i+1:02d}"      for i in range(lb_count)]
        apps      = app_names        or [f"app{i+1:02d}"     for i in range(app_count)]
        dbs       = db_names         or [f"db{i+1:02d}"      for i in range(db_count)]
        mons      = monitoring_names or [f"monitor{i+1:02d}" for i in range(monitoring_count)]

        # ── layout constants ──────────────────────────────────────────────────
        NODE_W   = 120;  NODE_H  = 60
        H_GAP    = 160;  V_GAP   = 140
        MARGIN_X = 100;  MARGIN_Y = 80
        SIDEBAR_X_OFFSET = 200  # extra gap to sidebar

        def _row_x(count: int, canvas_w: int) -> int:
            total = count * NODE_W + (count - 1) * H_GAP
            return (canvas_w - total) // 2

        # Compute canvas width from widest tier
        all_counts = [firewall_count, app_count, db_count]
        if include_lb:
            all_counts.append(lb_count)
        max_count  = max(all_counts)
        canvas_w   = max_count * NODE_W + (max_count - 1) * H_GAP + MARGIN_X * 2
        sidebar_x  = canvas_w + SIDEBAR_X_OFFSET

        write_file(path, blank_template("Security Stack"))

        all_ids:  dict[str, str] = {}
        tiers:    dict[str, list[str]] = {}   # tier_key → list of hostnames

        def _add_row(names: list[str], role: str, y: int) -> list[str]:
            row_ids = []
            rx = _row_x(len(names), canvas_w)
            for i, name in enumerate(names):
                x = rx + i * (NODE_W + H_GAP)
                cid = add_device(
                    path=path, hostname=name, role=role,
                    x=x, y=y, width=NODE_W, height=NODE_H,
                    site=site, style_profile=style_profile,
                )
                all_ids[name] = cid
                row_ids.append(name)
            return row_ids

        current_y = MARGIN_Y

        # Tier -1: Internet
        if include_internet:
            inet_name = "internet"
            inet_id   = add_device(
                path=path, hostname=inet_name, role="internet",
                x=_row_x(1, canvas_w), y=current_y,
                width=NODE_W, height=NODE_H,
                site=site, style_profile=style_profile,
            )
            all_ids[inet_name] = inet_id
            tiers["internet"] = [inet_name]
            current_y += NODE_H + V_GAP

        # Tier 0: Firewalls
        tiers["firewall"] = _add_row(fw_names, "firewall", current_y)
        current_y += NODE_H + V_GAP

        # Tier 1: Load balancers (optional)
        if include_lb:
            tiers["lb"] = _add_row(lbs, "load_balancer", current_y)
            current_y += NODE_H + V_GAP

        # Tier 2: Application servers
        tiers["app"] = _add_row(apps, "application_server", current_y)
        current_y += NODE_H + V_GAP

        # Tier 3: Databases
        tiers["db"] = _add_row(dbs, "database_node", current_y)

        # Sidebar: Monitoring
        if monitoring_count > 0:
            mon_y = MARGIN_Y + NODE_H + V_GAP   # same height as firewalls
            for i, name in enumerate(mons):
                cid = add_device(
                    path=path, hostname=name, role="monitoring_node",
                    x=sidebar_x, y=mon_y + i * (NODE_H + 40),
                    width=NODE_W, height=NODE_H,
                    site=site, style_profile=style_profile,
                )
                all_ids[name] = cid
            tiers["monitoring"] = mons

        # ── wiring ────────────────────────────────────────────────────────────
        link_count = 0

        def _connect_tiers(a_names: list[str], b_names: list[str], link_type: str):
            nonlocal link_count
            style = resolve_edge_style(link_type)
            for a in a_names:
                for b in b_names:
                    insert_edge(path, all_ids[a], all_ids[b], label="", style=style)
                    link_count += 1

        if include_internet and "internet" in tiers:
            _connect_tiers(tiers["internet"], tiers["firewall"], "wan")

        if include_lb and "lb" in tiers:
            _connect_tiers(tiers["firewall"], tiers["lb"],       "fabric")
            _connect_tiers(tiers["lb"],       tiers["app"],      "fabric")
        else:
            _connect_tiers(tiers["firewall"], tiers["app"],      "fabric")

        _connect_tiers(tiers["app"], tiers["db"], "uplink")

        if monitoring_count > 0 and "monitoring" in tiers:
            _connect_tiers(tiers["monitoring"], tiers["firewall"], "management")

        total_nodes = len(all_ids)
        return _j.dumps({
            "status":         "ok",
            "warnings":       [],
            "include_internet": include_internet,
            "include_lb":     include_lb,
            "firewall_count": len(tiers.get("firewall", [])),
            "lb_count":       len(tiers.get("lb", [])),
            "app_count":      len(tiers.get("app", [])),
            "db_count":       len(tiers.get("db", [])),
            "monitoring_count": len(tiers.get("monitoring", [])),
            "node_count":     total_nodes,
            "link_count":     link_count,
            "total_cells":    total_nodes + link_count,
        }, indent=2)

    except Exception as exc:
        return f"ERROR: {exc}"