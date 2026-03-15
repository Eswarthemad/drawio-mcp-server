# Changelog

All notable changes to this project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

---

## [1.5.0] — 2026-03-15

### Added

- **Tool 19 — `build_multi_site`**
  Generate N-site spine-leaf fabrics connected by a DCI/interconnect band in a single call.

  Features:
  - Configurable spine count, leaf count, and optional compute rows per site
  - Supported interconnect types: `evpn`, `vxlan`, `ospf`, `bgp`, `static`
  - Configurable DCI / Route-Reflector node count per interconnect band
  - Full-mesh spine-to-leaf fabric wiring within each site
  - Automatic cross-site uplink wiring: site spines ↔ DCI nodes ↔ site spines
  - DCI peer link between RR nodes inside each band
  - Auto-centering layout with per-site color coding
  - Optional compute node rows per leaf

- **`topology: multi_site` in YAML model**
  `build_diagram_from_model` dispatches to `build_multi_site` when
  `meta.topology: multi_site` is declared.

  New YAML keys:
  - `sites[].spines` — spine count per site
  - `sites[].leafs` — leaf count per site
  - `sites[].compute_per_leaf` — optional compute nodes per leaf
  - `interconnect.type` — interconnect type
  - `interconnect.dci_nodes` — DCI node count per band
  - `interconnect.label` — optional band label override

- **New dataclasses in `models.py`**
  - `SiteSpec` — site definition for multi-site topology
  - `InterconnectSpec` — DCI/interconnect specification
  - `TopologyModel` gains `site_specs` and `interconnect` fields

- **`multi_site` added to `SUPPORTED_TOPOLOGIES`**

- **`SUPPORTED_INTERCONNECT_TYPES` constant in `drawio.py`**
  `{"evpn", "vxlan", "ospf", "bgp", "static"}`

- **New validation codes**

  Errors (block build):
  - `E011` — duplicate site name
  - `E012` — unsupported interconnect type
  - `E013` — site declares zero spines
  - `E014` — site declares zero leafs

  Warnings (non-blocking):
  - `W007` — interconnect type not declared, defaulted to `evpn`
  - `W008` — fewer than 2 sites declared

- **`examples/multi_site.yaml`** — two-site EVPN fabric example.

- **`tests/test_multisite.py`** — test coverage for `build_multi_site`,
  multi-site model parsing, and E011–E014 / W007–W008 validation codes.

### Fixed

- `models.py`: `SiteSpec` and `InterconnectSpec` dataclasses were defined
  after `TopologyModel` referenced them — corrected ordering.
- `models.py`: `load_model()` used `data` variable (undefined) instead of
  `raw` — corrected throughout.
- `models.py`: `model.site_specs` / `model.interconnect` were assigned
  before the model was constructed — refactored to local variables passed
  into the final `TopologyModel()` constructor.
- `validators.py`: All multi-site `ValidationError` and `ValidationWarning`
  instantiations were missing the required `field=` parameter — added
  correct field paths for all E011–E014 and W007–W008 codes.
- `validators.py`: `W002`, `W003`, `W004` no longer fire for `multi_site`
  topology where devices and links are not declared by design.
- `drawio.py`: `build_diagram_from_model` had no `multi_site` dispatch
  block — fell through to the "unsupported topology" error. Dispatch added.

---

## [1.4.0] — 2026-03-12

### Added

- **Full pytest test suite** — 234 tests covering:
  - `test_drawio.py` — XML engine, all primitives, all builders (real file I/O)
  - `test_models.py` — YAML parsing, dataclasses, edge cases
  - `test_styles.py` — all 17 roles × 4 profiles, edge and container styles
  - `test_validators.py` — every error code E001–E010, every warning W001–W006

- **GitHub Actions CI workflow** (`.github/workflows/ci.yml`)
  - Lint with `ruff`
  - Test with `pytest`
  - Coverage reporting
  - Coverage gate enforcing ≥ 80%
  - Matrix: Python 3.11 and 3.12

- **`requirements-dev.txt`** — `pytest`, `pytest-cov`, `ruff`

### Changed

- Project structure updated to include `tests/` package.

---

## [1.3.0] — 2026-03-12

### Added

- **Tool 15 — `add_container`**
  Create labelled container groups in existing diagrams.
  Returns container cell ID for use as `parent_id` in `add_device`.

- **Tool 16 — `group_nodes`**
  Wrap existing nodes into a container group by re-parenting.
  Bounding box computed automatically with configurable padding.

- **Tool 17 — `build_hub_spoke`**
  Hub-spoke topology builder with two modes:
  - `tenant_fabric` — hub spines full-mesh to spoke leaves, leaves to compute endpoints
  - `wan_branch` — WAN router hub to branch routers via WAN links

- **Tool 18 — `build_security_stack`**
  5-tier security architecture generator:
  - Tier −1: Internet gateway (optional)
  - Tier 0: Firewall HA pair
  - Tier 1: Load balancers (optional)
  - Tier 2: Application servers
  - Tier 3: Database / storage
  - Sidebar: Monitoring nodes

- **New device roles** — styled across all four profiles:
  `internet`, `application_server`, `database_node`, `wan_router`, `branch_router`

- **New link type** — `wan`: dashed grey, thick stroke, for WAN / external links.

- `parent_id` parameter on `add_device` — place devices inside container groups.

- `style_profile` parameter on `add_device` — explicit style resolution at call site.

- **YAML model support** for `hub_spoke` and `security_stack` topologies.

- `topology_mode` field in YAML `meta` block: `tenant_fabric` | `wan_branch`.

- `containers` key in YAML model.

- **New validation codes**:
  - `E009` — unsupported `topology_mode` for hub_spoke
  - `E010` — container member references unknown hostname
  - `W006` — topology_mode not declared for hub_spoke, defaulted

### Changed

- `ROLE_LAYER` expanded to include all five new roles.
- `styles.py` — all four profiles updated with styles for new roles.
- `models.py` — `DiagramMeta` gains `topology_mode`; `TopologyModel` gains `containers`.
- `validators.py` — imports `SUPPORTED_HUB_SPOKE_MODES` from `models.py`.

---

## [1.2.0] — 2026-03-10

### Added

- **Tool 14 — `build_diagram_from_model`**
  Generate a complete diagram from a YAML topology file.

- **`models.py`** — typed dataclasses (`DiagramMeta`, `Site`, `Device`, `Link`,
  `Container`, `TopologyModel`) and `load_model()` YAML parser.

- **`styles.py`** — four visual style profiles:
  `minimal` (default), `enterprise`, `dark`, `vendor-neutral`.
  Resolves node and edge styles by role and profile.

- **`validators.py`** — single-pass schema validation with full JSON error report.
  Error codes `E001`–`E008` + `E097`–`E099`.
  Warning codes `W001`–`W005`.

- `style_profile` parameter on `build_spine_leaf_fabric`.

- `examples/spine_leaf.yaml` example file.

### Changed

- All hardcoded style strings removed from `drawio.py`.
  Style resolution delegates entirely to `styles.py`.
- `requirements.txt` updated to include `pyyaml`.

### Removed

- `ROLE_STYLE` and `LINK_STYLE` dicts from `drawio.py`.

---

## [1.1.0] — 2026-03-07

### Added

- **Tool 11 — `add_device`**
  Add network devices with semantic roles and structured metadata.
  Device metadata stored in draw.io `tooltip` attribute
  (hostname, role, vendor, platform, site, zone, redundancy group, layer).

- **Tool 12 — `add_link`**
  Add typed network links: `fabric`, `uplink`, `management`.

- **Tool 13 — `build_spine_leaf_fabric`**
  Generate a complete spine-leaf fabric.
  Configurable spine count, leaf count, compute nodes per leaf.
  Full-mesh hub-to-spoke wiring applied automatically.

- **`ROLE_LAYER` dict** — maps device roles to diagram layers.

---

## [1.0.0] — 2026-03-07

### Added

- Initial public release.

- **`server.py`** — MCP server exposing 10 tools via stdio transport.

- **`drawio.py`** — draw.io XML helper library.

- Core MCP tools:
  1. `read_diagram`
  2. `write_diagram`
  3. `list_diagrams`
  4. `list_nodes`
  5. `add_node`
  6. `add_edge`
  7. `update_node`
  8. `delete_node`
  9. `create_blank_diagram`
  10. `auto_layout`

- Initial project files: `README.md`, `CONTRIBUTING.md`, `LICENSE`,
  `requirements.txt`, `.gitignore`.

---

[Unreleased]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Eswarthemad/drawio-mcp-server/releases/tag/v1.0.0