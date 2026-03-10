# -*- coding: utf-8 -*-
"""
styles.py — Style profile resolver for network diagram nodes and edges.

This module is the single source of truth for all draw.io style strings.
It replaces the hardcoded ROLE_STYLE dict that previously lived in drawio.py.

Callers supply a role name and a profile name; this module returns the
correct draw.io style string. drawio.py and builders never construct or
hardcode style strings directly — they always go through resolve_node_style()
and resolve_edge_style().

Public API
----------
    resolve_node_style(role, profile)  -> str
    resolve_edge_style(link_type)      -> str
    list_profiles()                    -> list[str]
    list_roles()                       -> list[str]

Profiles
--------
    minimal        Plain rounded rectangles. No external stencil dependencies.
                   Works in any draw.io installation. This is the default.

    enterprise     Cisco network stencil shapes with colour coding by role.
                   Requires the Cisco shape library to be enabled in draw.io.

    dark           Dark background variant of minimal — white text on
                   dark fills. Suitable for dark-mode presentations.

    vendor-neutral Functional icon set using draw.io built-in network shapes.
                   No Cisco dependency. More visual than minimal.
"""

from __future__ import annotations

# ==============================================================================
# NODE STYLE TABLES
# ==============================================================================

#: role → draw.io style string, keyed by profile name.
#: Each profile must define every role that appears in drawio.ROLE_LAYER,
#: or fall back to _DEFAULT_STYLE for that profile.

_MINIMAL: dict[str, str] = {
    # All roles use plain rounded rectangles, differentiated only by fill colour.
    "spine":              "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;",
    "core_switch":        "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;",
    "router":             "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "firewall":           "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontStyle=1;",
    "load_balancer":      "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
    "border_leaf":        "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "leaf":               "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "gpu_node":           "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;",
    "storage_node":       "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;",
    "compute_node":       "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;",
    "management_switch":  "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;",
    "monitoring_node":    "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;",
}

_ENTERPRISE: dict[str, str] = {
    # Cisco stencil shapes — requires Cisco shape library in draw.io.
    "spine":              "shape=mxgraph.cisco.switches.layer_3_switch;sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#036897;strokeColor=#ffffff;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;",
    "core_switch":        "shape=mxgraph.cisco.switches.layer_3_switch;sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#036897;strokeColor=#ffffff;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;",
    "router":             "shape=mxgraph.cisco.routers.router;sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#036897;strokeColor=#ffffff;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;",
    "firewall":           "shape=mxgraph.cisco.firewalls.firewall;sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#ae4132;strokeColor=#ffffff;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;",
    "load_balancer":      "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
    "border_leaf":        "shape=mxgraph.cisco.switches.workgroup_switch;sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#0e7ad1;strokeColor=#ffffff;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;",
    "leaf":               "shape=mxgraph.cisco.switches.workgroup_switch;sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#0e7ad1;strokeColor=#ffffff;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;",
    "gpu_node":           "shape=mxgraph.cisco.servers.standard_server;sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#647687;strokeColor=#314354;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;",
    "storage_node":       "shape=mxgraph.cisco.storage.generic_disk_array;sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#647687;strokeColor=#314354;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;",
    "compute_node":       "shape=mxgraph.cisco.servers.standard_server;sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#647687;strokeColor=#314354;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;",
    "management_switch":  "shape=mxgraph.cisco.switches.workgroup_switch;sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#f0a30a;strokeColor=#BD7000;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;",
    "monitoring_node":    "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;",
}

_DARK: dict[str, str] = {
    # Dark fills with white/light text — suitable for dark-mode presentations.
    "spine":              "rounded=1;whiteSpace=wrap;html=1;fillColor=#1e4d78;strokeColor=#5ba4cf;fontColor=#ffffff;fontStyle=1;",
    "core_switch":        "rounded=1;whiteSpace=wrap;html=1;fillColor=#1e4d78;strokeColor=#5ba4cf;fontColor=#ffffff;fontStyle=1;",
    "router":             "rounded=1;whiteSpace=wrap;html=1;fillColor=#1e4d78;strokeColor=#5ba4cf;fontColor=#ffffff;",
    "firewall":           "rounded=1;whiteSpace=wrap;html=1;fillColor=#7a1e1e;strokeColor=#cf5b5b;fontColor=#ffffff;fontStyle=1;",
    "load_balancer":      "rounded=1;whiteSpace=wrap;html=1;fillColor=#1e5c3a;strokeColor=#4caf80;fontColor=#ffffff;",
    "border_leaf":        "rounded=1;whiteSpace=wrap;html=1;fillColor=#1a3a5c;strokeColor=#4a8fc4;fontColor=#ffffff;",
    "leaf":               "rounded=1;whiteSpace=wrap;html=1;fillColor=#1a3a5c;strokeColor=#4a8fc4;fontColor=#ffffff;",
    "gpu_node":           "rounded=1;whiteSpace=wrap;html=1;fillColor=#2d2d2d;strokeColor=#888888;fontColor=#cccccc;",
    "storage_node":       "rounded=1;whiteSpace=wrap;html=1;fillColor=#2d2d2d;strokeColor=#888888;fontColor=#cccccc;",
    "compute_node":       "rounded=1;whiteSpace=wrap;html=1;fillColor=#2d2d2d;strokeColor=#888888;fontColor=#cccccc;",
    "management_switch":  "rounded=1;whiteSpace=wrap;html=1;fillColor=#5c4a00;strokeColor=#c4a000;fontColor=#ffffff;",
    "monitoring_node":    "rounded=1;whiteSpace=wrap;html=1;fillColor=#5c4a00;strokeColor=#c4a000;fontColor=#ffffff;",
}

_VENDOR_NEUTRAL: dict[str, str] = {
    # draw.io built-in network shapes — no Cisco dependency, more visual than minimal.
    "spine":              "shape=mxgraph.network.switch;sketch=0;html=1;pointerEvents=1;fillColor=#dae8fc;strokeColor=#6c8ebf;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "core_switch":        "shape=mxgraph.network.switch;sketch=0;html=1;pointerEvents=1;fillColor=#dae8fc;strokeColor=#6c8ebf;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "router":             "shape=mxgraph.network.router;sketch=0;html=1;pointerEvents=1;fillColor=#dae8fc;strokeColor=#6c8ebf;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "firewall":           "shape=mxgraph.network.firewall;sketch=0;html=1;pointerEvents=1;fillColor=#f8cecc;strokeColor=#b85450;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "load_balancer":      "shape=mxgraph.network.server;sketch=0;html=1;pointerEvents=1;fillColor=#d5e8d4;strokeColor=#82b366;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "border_leaf":        "shape=mxgraph.network.switch;sketch=0;html=1;pointerEvents=1;fillColor=#dae8fc;strokeColor=#6c8ebf;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "leaf":               "shape=mxgraph.network.switch;sketch=0;html=1;pointerEvents=1;fillColor=#dae8fc;strokeColor=#6c8ebf;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "gpu_node":           "shape=mxgraph.network.server;sketch=0;html=1;pointerEvents=1;fillColor=#f5f5f5;strokeColor=#666666;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "storage_node":       "shape=mxgraph.network.server;sketch=0;html=1;pointerEvents=1;fillColor=#f5f5f5;strokeColor=#666666;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "compute_node":       "shape=mxgraph.network.server;sketch=0;html=1;pointerEvents=1;fillColor=#f5f5f5;strokeColor=#666666;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "management_switch":  "shape=mxgraph.network.switch;sketch=0;html=1;pointerEvents=1;fillColor=#fff2cc;strokeColor=#d6b656;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
    "monitoring_node":    "shape=mxgraph.network.server;sketch=0;html=1;pointerEvents=1;fillColor=#fff2cc;strokeColor=#d6b656;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
}

#: Master profile registry — maps profile name to its style table.
_PROFILES: dict[str, dict[str, str]] = {
    "minimal":        _MINIMAL,
    "enterprise":     _ENTERPRISE,
    "dark":           _DARK,
    "vendor-neutral": _VENDOR_NEUTRAL,
}

#: Fallback style used when a role is not found in any profile table.
_FALLBACK_STYLE: str = "rounded=1;whiteSpace=wrap;html=1;"


# ==============================================================================
# EDGE STYLE TABLE
# ==============================================================================

#: Link type → draw.io edge style string.
#: Edge styles are profile-independent — they are consistent across all profiles.
_EDGE_STYLES: dict[str, str] = {
    "fabric":     "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;strokeWidth=2;strokeColor=#0e7ad1;",
    "uplink":     "edgeStyle=orthogonalEdgeStyle;rounded=0;strokeWidth=1;strokeColor=#036897;dashed=0;",
    "management": "edgeStyle=orthogonalEdgeStyle;rounded=0;strokeWidth=1;strokeColor=#d6b656;dashed=1;",
    "default":    "edgeStyle=orthogonalEdgeStyle;rounded=0;strokeWidth=1;",
}


# ==============================================================================
# PUBLIC API
# ==============================================================================

def resolve_node_style(role: str, profile: str = "minimal") -> str:
    """
    Return the draw.io style string for a given device role and profile.

    Falls back to the minimal profile if the requested profile is unknown.
    Falls back to a plain rounded rectangle if the role is not found in
    the profile table.

    Args:
        role:    Device role key (e.g. 'spine', 'leaf', 'firewall').
        profile: Style profile name (e.g. 'minimal', 'enterprise').

    Returns:
        A draw.io style string.
    """
    table = _PROFILES.get(profile) or _PROFILES["minimal"]
    return table.get(role, _FALLBACK_STYLE)


def resolve_edge_style(link_type: str = "default") -> str:
    """
    Return the draw.io edge style string for a given link type.

    Falls back to 'default' style if the link type is unknown.

    Args:
        link_type: Logical link type key (e.g. 'fabric', 'uplink').

    Returns:
        A draw.io edge style string.
    """
    return _EDGE_STYLES.get(link_type, _EDGE_STYLES["default"])


def list_profiles() -> list[str]:
    """Return the names of all registered style profiles."""
    return sorted(_PROFILES.keys())


def list_roles() -> list[str]:
    """Return all role names defined in the minimal profile (canonical set)."""
    return sorted(_MINIMAL.keys())