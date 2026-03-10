# -*- coding: utf-8 -*-
"""
server.py — MCP server for draw.io diagram editing.

This file owns only MCP tool registration.
All diagram logic lives in drawio.py.

Each tool function here is a thin wrapper that:
  1. Receives arguments from Claude via the MCP protocol.
  2. Delegates to the appropriate drawio.py function.
  3. Returns the result string back to Claude.

Adding a new tool means:
  - Implement the logic in drawio.py.
  - Register a one-liner wrapper here with @mcp.tool().
"""

from mcp.server.fastmcp import FastMCP

import drawio

# ==============================================================================
# SERVER INIT
# ==============================================================================

mcp = FastMCP(
    "drawio-mcp",
    instructions=(
        "You are a draw.io diagram editor. "
        "Use these tools to read, modify, and create draw.io (.drawio / .xml) "
        "diagram files."
    ),
)


# ==============================================================================
# TOOL 1 — read_diagram
# ==============================================================================

@mcp.tool()
def read_diagram(path: str) -> str:
    """
    Read the raw XML content of a draw.io diagram file.

    Args:
        path: Full path to the .drawio or .xml file.

    Returns:
        The raw XML string of the diagram.
    """
    return drawio.read_file(path)


# ==============================================================================
# TOOL 2 — write_diagram
# ==============================================================================

@mcp.tool()
def write_diagram(path: str, content: str) -> str:
    """
    Write (overwrite) a draw.io diagram file with new XML content.
    Creates the file if it does not exist.

    Args:
        path:    Full path to write the .drawio file.
        content: Full XML string to write.

    Returns:
        Confirmation message with absolute path.
    """
    return drawio.write_file(path, content)


# ==============================================================================
# TOOL 3 — list_diagrams
# ==============================================================================

@mcp.tool()
def list_diagrams(folder: str) -> str:
    """
    List all draw.io diagram files (.drawio, .xml) in a folder.

    Args:
        folder: Directory path to scan.

    Returns:
        JSON list of matching file paths.
    """
    import json
    from pathlib import Path

    p = Path(folder)
    if not p.is_dir():
        return f"ERROR: Not a directory -> {folder}"
    files = sorted(
        str(f) for f in p.rglob("*")
        if f.suffix.lower() in {".drawio", ".xml"}
    )
    return json.dumps(files, indent=2)


# ==============================================================================
# TOOL 4 — list_nodes
# ==============================================================================

@mcp.tool()
def list_nodes(path: str) -> str:
    """
    List all nodes (shapes/vertices) and edges in a draw.io diagram.

    Args:
        path: Full path to the .drawio file.

    Returns:
        JSON list of cells with id, label, type (vertex/edge), style,
        source, and target.
    """
    return drawio.get_nodes(path)


# ==============================================================================
# TOOL 5 — add_node
# ==============================================================================

@mcp.tool()
def add_node(
    path: str,
    label: str,
    x: int = 100,
    y: int = 100,
    width: int = 120,
    height: int = 60,
    style: str = "rounded=1;whiteSpace=wrap;html=1;",
) -> str:
    """
    Add a new shape (vertex/node) to a draw.io diagram.

    Args:
        path:   Full path to the .drawio file.
        label:  Text label inside the shape.
        x:      X position in pixels (default 100).
        y:      Y position in pixels (default 100).
        width:  Shape width in pixels (default 120).
        height: Shape height in pixels (default 60).
        style:  draw.io style string (default rounded rectangle).

    Returns:
        The new cell's ID on success.
    """
    return drawio.insert_node(path, label, x, y, width, height, style)


# ==============================================================================
# TOOL 6 — add_edge
# ==============================================================================

@mcp.tool()
def add_edge(
    path: str,
    source_id: str,
    target_id: str,
    label: str = "",
    style: str = "edgeStyle=orthogonalEdgeStyle;",
) -> str:
    """
    Add a directed edge (arrow/connector) between two nodes.

    Args:
        path:      Full path to the .drawio file.
        source_id: Cell ID of the source node.
        target_id: Cell ID of the target node.
        label:     Optional label on the edge.
        style:     draw.io edge style string.

    Returns:
        The new edge's ID on success.
    """
    return drawio.insert_edge(path, source_id, target_id, label, style)


# ==============================================================================
# TOOL 7 — update_node
# ==============================================================================

@mcp.tool()
def update_node(
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
    Update the label, style, or geometry of an existing node.
    Only the fields you provide will be changed.

    Args:
        path:          Full path to the .drawio file.
        cell_id:       ID of the cell to update.
        label:         New label text (optional).
        style:         New style string (optional).
        x, y:          New position (optional).
        width, height: New dimensions (optional).

    Returns:
        Confirmation or error message.
    """
    return drawio.modify_node(path, cell_id, label, style, x, y, width, height)


# ==============================================================================
# TOOL 8 — delete_node
# ==============================================================================

@mcp.tool()
def delete_node(path: str, cell_id: str) -> str:
    """
    Delete a node or edge from the diagram by its cell ID.
    Also removes any edges connected to the deleted node.

    Args:
        path:    Full path to the .drawio file.
        cell_id: ID of the cell to delete.

    Returns:
        Confirmation or error message.
    """
    return drawio.remove_node(path, cell_id)


# ==============================================================================
# TOOL 9 — create_blank_diagram
# ==============================================================================

@mcp.tool()
def create_blank_diagram(path: str, page_name: str = "Page-1") -> str:
    """
    Create a new blank draw.io diagram file.

    Args:
        path:      Full path where the new .drawio file should be created.
        page_name: Name of the first diagram page (default 'Page-1').

    Returns:
        Confirmation with absolute path.
    """
    result = drawio.write_file(path, drawio.blank_template(page_name))
    return result.replace("Saved:", "Created blank diagram:")


# ==============================================================================
# TOOL 10 — auto_layout
# ==============================================================================

@mcp.tool()
def auto_layout(
    path: str,
    direction: str = "TB",
    start_x: int = 80,
    start_y: int = 80,
    layer_spacing: int = 180,
    node_spacing: int = 100,
) -> str:
    """
    Auto-layout the diagram using a layered graph approach.

    Supported directions:
        TB = Top-to-Bottom  (default)
        BT = Bottom-to-Top
        LR = Left-to-Right
        RL = Right-to-Left

    Args:
        path:           Full path to the .drawio file.
        direction:      Layout direction: TB, BT, LR, RL.
        start_x:        Starting X coordinate (default 80).
        start_y:        Starting Y coordinate (default 80).
        layer_spacing:  Pixel gap between layers (default 180).
        node_spacing:   Pixel gap between nodes in the same layer (default 100).

    Returns:
        Confirmation message.
    """
    return drawio.apply_layout(path, direction, start_x, start_y, layer_spacing, node_spacing)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    mcp.run()