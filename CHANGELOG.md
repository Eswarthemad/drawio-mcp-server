# Changelog

All notable changes to this project are documented in this file.

The format follows Keep a Changelog:
https://keepachangelog.com/en/1.0.0/

This project adheres to Semantic Versioning:
https://semver.org/

---

## [Unreleased]

---

## [1.4.0] — 2026-03-12

### Added
- Full **pytest test suite** covering:
  - drawio engine
  - YAML model parser
  - style resolution
  - topology validation
- **GitHub Actions CI pipeline** running:
  - `ruff` lint
  - `pytest`
  - coverage reporting
- **Coverage gate** enforcing ≥ 80% coverage.
- Development dependency file `requirements-dev.txt`.

### Changed
- Project structure updated to include `tests/`.
- CI now runs tests on **Python 3.11 and 3.12**.

---

## [1.3.0] — 2026-03-12

### Added
- **Tool 15 — `add_container`**  
  Create labelled container groups in existing diagrams.  
  Returns container cell ID for use as `parent_id` in `add_device`.

- **Tool 16 — `group_nodes`**  
  Wrap existing nodes into a container group by re-parenting them.  
  Bounding box computed automatically with configurable padding.

- **Tool 17 — `build_hub_spoke`**  
  Hub-spoke topology builder supporting two modes:
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

- **New device roles**
  - `internet`
  - `application_server`
  - `database_node`
  - `wan_router`
  - `branch_router`

  Styled across all four style profiles.

- **New link type**
  - `wan` — dashed grey thick connector for WAN / external links.

- `parent_id` parameter on `add_device` to place devices inside containers.

- `style_profile` parameter on `add_device` for explicit style resolution.

- **YAML model support for additional topologies**
  - `hub_spoke`
  - `security_stack`

- `topology_mode` field in YAML `meta` block:
  - `tenant_fabric`
  - `wan_branch`

- YAML support for `containers`.

- **New validation codes**
  - `E009` — unsupported `topology_mode` for hub_spoke
  - `E010` — container member references unknown hostname
  - `W006` — topology_mode not declared for hub_spoke

### Changed
- `ROLE_LAYER` expanded to include new device roles.
- `styles.py` profiles updated to support new roles.
- `models.py`
  - `DiagramMeta` gains `topology_mode`
  - `TopologyModel` gains `containers`
- `validators.py` imports `SUPPORTED_HUB_SPOKE_MODES`.

---

## [1.2.0] — 2026-03-10

### Added
- **Tool 14 — `build_diagram_from_model`**  
  Generate diagrams from YAML topology definitions.

- **models.py**
  - Dataclasses for `DiagramMeta`, `Site`, `Device`, `Link`, `TopologyModel`
  - `load_model()` YAML parser.

- **styles.py**
  Style profile system:
  - `minimal`
  - `enterprise`
  - `dark`
  - `vendor-neutral`

- **validators.py**
  Full validation layer with structured JSON report.

  Error codes:
  - `E001`–`E008`
  - `E097`–`E099`

  Warning codes:
  - `W001`–`W005`

- `style_profile` parameter added to `build_spine_leaf_fabric`.

- Example YAML model `examples/spine_leaf.yaml`.

### Changed
- Style resolution moved out of `drawio.py` into `styles.py`.
- `requirements.txt` updated to include `pyyaml`.

### Removed
- `ROLE_STYLE` dictionary from `drawio.py`.
- `LINK_STYLE` dictionary from `drawio.py`.

---

## [1.1.0] — 2026-03-07

### Added
- **Tool 11 — `add_device`**  
  Add network devices using semantic roles.

  Metadata stored in draw.io `tooltip`:
  - hostname
  - role
  - vendor
  - platform
  - site
  - zone
  - redundancy group
  - layer

- **Tool 12 — `add_link`**  
  Add typed network links:
  - `fabric`
  - `uplink`
  - `management`

- **Tool 13 — `build_spine_leaf_fabric`**  
  Generate a full spine-leaf topology with configurable spine/leaf/compute counts.

- **ROLE_LAYER** mapping roles to diagram layers.

---

## [1.0.0] — 2026-03-07

### Added
- Initial public release.

- **server.py**  
  MCP server exposing 10 tools via stdio transport.

- **drawio.py**  
  draw.io XML helper library.

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

- Initial project files:
  - README.md
  - CONTRIBUTING.md
  - LICENSE
  - requirements.txt
  - .gitignore

---

## Version Comparison Links

[Unreleased]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.4.0...HEAD  
[1.4.0]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.3.0...v1.4.0  
[1.3.0]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.2.0...v1.3.0  
[1.2.0]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.1.0...v1.2.0  
[1.1.0]: https://github.com/Eswarthemad/drawio-mcp-server/compare/v1.0.0...v1.1.0  
[1.0.0]: https://github.com/Eswarthemad/drawio-mcp-server/releases/tag/v1.0.0