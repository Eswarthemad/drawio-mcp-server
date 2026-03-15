# -*- coding: utf-8 -*-
"""
models.py — Typed data models for the network diagram YAML schema.

All YAML input is parsed into these dataclasses before any diagram
manipulation or validation occurs. No raw dicts are passed between
modules — everything flows as typed objects.

Public API
----------
    DiagramMeta         — top-level diagram metadata (name, topology, style)
    Site                — a named site/location
    Device              — a network device with role and metadata
    Link                — a connection between two devices
    Container           — a labelled container group
    SiteSpec            — site spec for multi-site topology
    InterconnectSpec    — DCI/interconnect spec for multi-site topology
    TopologyModel       — the complete parsed topology
    load_model(path)    — parse a YAML file into a TopologyModel
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path


# ==============================================================================
# CONSTANTS
# ==============================================================================

#: Topology key used when the YAML does not specify one.
DEFAULT_TOPOLOGY: str = "spine_leaf"

#: Warning code emitted when topology defaults are applied.
WARN_TOPOLOGY_DEFAULTED: str = "W001"

#: Supported topology identifiers. Extend this as new builders are added.
SUPPORTED_TOPOLOGIES: set[str] = {
    "spine_leaf",
    "hub_spoke",
    "security_stack",
    "multi_site",
}

#: Supported hub-spoke sub-modes.
SUPPORTED_HUB_SPOKE_MODES: set[str] = {"tenant_fabric", "wan_branch"}

#: Default style profile when none is specified.
DEFAULT_STYLE_PROFILE: str = "minimal"

#: Supported style profile identifiers.
SUPPORTED_STYLE_PROFILES: set[str] = {
    "minimal",
    "enterprise",
    "dark",
    "vendor-neutral",
}


# ==============================================================================
# DATACLASSES
# ==============================================================================

@dataclass
class DiagramMeta:
    """
    Top-level metadata block from the YAML ``meta:`` section.

    Attributes:
        name:              Human-readable diagram name.
        topology:          Topology type key (e.g. 'spine_leaf', 'hub_spoke').
                           Defaults to DEFAULT_TOPOLOGY if not supplied.
        topology_mode:     Sub-mode for topologies that support it.
                           E.g. 'tenant_fabric' or 'wan_branch' for hub_spoke.
        style_profile:     Visual style profile key.
                           Defaults to DEFAULT_STYLE_PROFILE if not supplied.
        topology_defaulted: True if topology was not declared in the YAML
                            and was defaulted. Triggers a W001 warning.
    """
    name:               str  = "Untitled Diagram"
    topology:           str  = DEFAULT_TOPOLOGY
    topology_mode:      str  = ""
    style_profile:      str  = DEFAULT_STYLE_PROFILE
    topology_defaulted: bool = False


@dataclass
class Site:
    """
    A named physical or logical site.

    Attributes:
        name: Site identifier (e.g. 'DC1', 'DC2', 'HQ').
    """
    name: str


@dataclass
class Device:
    """
    A network device node.

    Attributes:
        hostname:         Device hostname — used as the cell label and
                          as the unique identifier in link references.
        role:             Device role key (must be in drawio.ROLE_LAYER).
        site:             Site name this device belongs to.
        vendor:           Vendor name (e.g. 'NVIDIA', 'Fortinet').
        platform:         Platform / model string.
        zone:             Security or network zone.
        redundancy_group: HA / MLAG / ECMP group identifier.
    """
    hostname:         str
    role:             str
    site:             str = ""
    vendor:           str = ""
    platform:         str = ""
    zone:             str = ""
    redundancy_group: str = ""


@dataclass
class Link:
    """
    A network link between two devices.

    Attributes:
        a:     Hostname of the first endpoint.
        b:     Hostname of the second endpoint.
        type:  Logical link type (e.g. 'fabric', 'uplink', 'management').
        label: Optional label displayed on the edge.
    """
    a:     str
    b:     str
    type:  str = "default"
    label: str = ""


@dataclass
class Container:
    """
    A labelled container group that visually groups devices.

    Attributes:
        name:    Container identifier — used as label and reference key.
        label:   Display label (defaults to name if not set).
        members: List of device hostnames that belong to this container.
        style:   Optional explicit draw.io container style.
    """
    name:    str
    label:   str         = ""
    members: list[str]   = field(default_factory=list)
    style:   str         = ""

    def __post_init__(self) -> None:
        if not self.label:
            self.label = self.name


@dataclass
class SiteSpec:
    """
    Site definition for multi-site topology.

    Attributes:
        name:             Site identifier (e.g. 'dc1', 'dc2').
        spines:           Number of spine nodes (default 2).
        leafs:            Number of leaf nodes (default 4).
        compute_per_leaf: Compute / GPU nodes per leaf (default 0 = omit tier).
    """
    name:             str
    spines:           int = 2
    leafs:            int = 4
    compute_per_leaf: int = 0


@dataclass
class InterconnectSpec:
    """
    DCI / interconnect specification for multi-site topology.

    Attributes:
        type:      Interconnect type: evpn | vxlan | ospf | bgp | static.
        dci_nodes: Number of DCI / Route-Reflector nodes per interconnect band.
        label:     Override the band label. Empty = auto '{TYPE} / DCI Interconnect'.
    """
    type:      str = "evpn"
    dci_nodes: int = 2
    label:     str = ""


@dataclass
class TopologyModel:
    """
    The complete parsed topology — one-to-one with a valid YAML file.

    Attributes:
        meta:         Diagram metadata.
        sites:        List of declared sites.
        devices:      List of network devices.
        links:        List of network links.
        containers:   List of container groups.
        site_specs:   List of site specs for multi-site topology.
        interconnect: DCI/interconnect spec for multi-site topology.
    """
    meta:         DiagramMeta         = field(default_factory=DiagramMeta)
    sites:        list[Site]          = field(default_factory=list)
    devices:      list[Device]        = field(default_factory=list)
    links:        list[Link]          = field(default_factory=list)
    containers:   list[Container]     = field(default_factory=list)
    site_specs:   list[SiteSpec]      = field(default_factory=list)
    interconnect: InterconnectSpec    = field(default_factory=InterconnectSpec)


# ==============================================================================
# YAML LOADER
# ==============================================================================

def load_model(yaml_path: str) -> TopologyModel:
    """
    Parse a YAML topology file into a TopologyModel.

    The loader is intentionally permissive — it parses whatever is
    present and populates sensible defaults for missing fields.
    Semantic validation (unknown roles, broken link references, etc.)
    is the responsibility of validators.py, not this function.

    Args:
        yaml_path: Full path to the YAML topology file.

    Returns:
        A populated TopologyModel.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        yaml.YAMLError:    If the file is not valid YAML.
    """
    p = Path(yaml_path)
    if not p.exists():
        raise FileNotFoundError(f"YAML model file not found: {yaml_path}")

    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # ── meta ──────────────────────────────────────────────────────────────────
    raw_meta           = raw.get("meta", {}) or {}
    topology_declared  = "topology" in raw_meta

    meta = DiagramMeta(
        name               = str(raw_meta.get("name", "Untitled Diagram")),
        topology           = str(raw_meta.get("topology", DEFAULT_TOPOLOGY)).lower().strip(),
        topology_mode      = str(raw_meta.get("topology_mode", "")).lower().strip(),
        style_profile      = str(raw_meta.get("style_profile", DEFAULT_STYLE_PROFILE)).lower().strip(),
        topology_defaulted = not topology_declared,
    )

    # ── sites (generic Site list — used by spine_leaf / hub_spoke / security_stack) ──
    sites = [
        Site(name=str(s.get("name", "")))
        for s in (raw.get("sites") or [])
        if s and s.get("name")
    ]

    # ── devices ───────────────────────────────────────────────────────────────
    devices = [
        Device(
            hostname         = str(d.get("hostname", "")),
            role             = str(d.get("role", "")).lower().strip(),
            site             = str(d.get("site", "")),
            vendor           = str(d.get("vendor", "")),
            platform         = str(d.get("platform", "")),
            zone             = str(d.get("zone", "")),
            redundancy_group = str(d.get("redundancy_group", "")),
        )
        for d in (raw.get("devices") or [])
        if d and d.get("hostname")
    ]

    # ── links ─────────────────────────────────────────────────────────────────
    links = [
        Link(
            a     = str(lnk.get("a", "")),
            b     = str(lnk.get("b", "")),
            type  = str(lnk.get("type", "default")).lower().strip(),
            label = str(lnk.get("label", "")),
        )
        for lnk in (raw.get("links") or [])
        if lnk and lnk.get("a") and lnk.get("b")
    ]

    # ── containers ────────────────────────────────────────────────────────────
    containers = [
        Container(
            name    = str(c.get("name", "")),
            label   = str(c.get("label", c.get("name", ""))),
            members = [str(m) for m in (c.get("members") or [])],
            style   = str(c.get("style", "")),
        )
        for c in (raw.get("containers") or [])
        if c and c.get("name")
    ]

    # ── multi_site: site_specs ─────────────────────────────────────────────────
    # Re-uses the 'sites' YAML key; each entry may also carry spines/leafs/compute.
    site_specs: list[SiteSpec] = []
    for rs in (raw.get("sites") or []):
        if isinstance(rs, dict) and rs.get("name"):
            site_specs.append(SiteSpec(
                name             = str(rs.get("name", "site")),
                spines           = int(rs.get("spines", 2)),
                leafs            = int(rs.get("leafs", 4)),
                compute_per_leaf = int(rs.get("compute_per_leaf", 0)),
            ))

    # ── multi_site: interconnect ───────────────────────────────────────────────
    raw_ic = raw.get("interconnect") or {}
    if isinstance(raw_ic, dict):
        interconnect = InterconnectSpec(
            type      = str(raw_ic.get("type",      "evpn")),
            dci_nodes = int(raw_ic.get("dci_nodes", 2)),
            label     = str(raw_ic.get("label",     "")),
        )
    else:
        interconnect = InterconnectSpec()

    return TopologyModel(
        meta         = meta,
        sites        = sites,
        devices      = devices,
        links        = links,
        containers   = containers,
        site_specs   = site_specs,
        interconnect = interconnect,
    )