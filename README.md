# drawio-mcp-server

[![CI](https://github.com/Eswarthemad/drawio-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/Eswarthemad/drawio-mcp-server/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Eswarthemad/drawio-mcp-server)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Eswarthemad/drawio-mcp-server)](https://github.com/Eswarthemad/drawio-mcp-server/releases)

A Python **Model Context Protocol (MCP) server** for generating and maintaining **draw.io architecture diagrams programmatically**.

This project enables AI assistants and automation tools to **read, modify, and generate draw.io diagrams** using structured commands — no manual XML editing required.

The long-term goal is a **vendor-neutral, network-aware automation layer** for infrastructure architecture diagrams.

---

## Why This Project Exists

Large infrastructure diagrams — especially **network architecture diagrams** — quickly become difficult to maintain manually.

This MCP server allows diagrams to be:

- generated programmatically from YAML topology models
- updated through automation
- modified by AI assistants
- version controlled like code

Instead of manually editing XML or dragging shapes in a GUI, diagrams are described as data and generated repeatably.

```
YAML topology model
       │
       ▼
AI Assistant (Claude)
       │  MCP
       ▼
drawio-mcp-server
       │
       ▼
.drawio diagram files
```

---

## What's New in v1.5.0

**Multi-site architecture support**

The new `build_multi_site` tool generates N-site spine-leaf fabrics connected by a DCI/interconnect band in a single call.

- Configurable spine count, leaf count, and optional compute rows per site
- Supported interconnect types: `evpn`, `vxlan`, `ospf`, `bgp`, `static`
- Configurable DCI / Route-Reflector node count per band
- Full-mesh spine-to-leaf wiring within each site
- Automatic cross-site uplink wiring between spines and DCI nodes
- YAML-driven via `topology: multi_site`

**New validation codes**

`E011` duplicate site name · `E012` unsupported interconnect type · `E013` zero spines · `E014` zero leafs · `W007` interconnect not declared · `W008` fewer than 2 sites

---

## Features

### Core Diagram Operations (v1.0.0)

- Read and write raw draw.io XML
- List diagram nodes and edges
- Add, update, and delete nodes
- Create connections between nodes
- Create blank diagrams
- Auto-layout (TB / BT / LR / RL)

---

### Network-Aware Primitives (v1.1.0)

- `add_device()` — add devices with semantic roles (spine, leaf, firewall, gpu_node, etc.)
- `add_link()` — add typed links (fabric, uplink, management)
- `build_spine_leaf_fabric()` — generate a full spine-leaf topology

---

### Diagram-as-Data / YAML Model (v1.2.0)

- `build_diagram_from_model()` — build a complete diagram from a YAML file
- Style profiles: `minimal`, `enterprise`, `dark`, `vendor-neutral`
- Full validation with structured JSON error reporting

---

### Containers and Extended Topologies (v1.3.0)

- `add_container()` — logical container groups (racks, zones, clusters)
- `group_nodes()` — wrap existing nodes into a container by bounding box
- `build_hub_spoke()` — hub-spoke topology (tenant fabric or WAN branch mode)
- `build_security_stack()` — 5-tier security zone architecture

---

### Test Suite and CI (v1.4.0)

- 234-test pytest suite covering all modules
- GitHub Actions CI on Python 3.11 and 3.12
- Coverage gate enforcing ≥ 80%

---

### Multi-Site Architecture (v1.5.0)

- `build_multi_site()` — N-site spine-leaf fabrics with DCI interconnect bands
- YAML support for `topology: multi_site`
- New validation codes E011–E014, W007–W008

---

## Quick Start: YAML → Diagram

### Single-site spine-leaf

```yaml
meta:
  name: "DC1 Fabric"
  topology: spine_leaf
  style_profile: minimal

sites:
  - name: dc1

devices:
  - hostname: spine01
    role: spine
    site: dc1
  - hostname: leaf01
    role: leaf
    site: dc1
  - hostname: compute01
    role: compute_node
    site: dc1

links:
  - a: spine01
    b: leaf01
    type: fabric
  - a: leaf01
    b: compute01
    type: uplink
```

### Multi-site EVPN fabric

```yaml
meta:
  name: "Multi-Site Fabric"
  topology: multi_site
  style_profile: minimal

sites:
  - name: dc1
    spines: 2
    leafs: 4
    compute_per_leaf: 2
  - name: dc2
    spines: 2
    leafs: 4

interconnect:
  type: evpn
  dci_nodes: 2
```

Generate either diagram:

```
build_diagram_from_model(
    path="diagrams/fabric.drawio",
    yaml_path="examples/multi_site.yaml"
)
```

---

## All MCP Tools — v1.5.0 (19 tools)

### High-Level Builders

| Tool                       | Description                                      |
|----------------------------|--------------------------------------------------|
| `build_multi_site`         | Multi-site spine-leaf with EVPN/DCI interconnect |
| `build_spine_leaf_fabric`  | Single-site spine-leaf fabric                    |
| `build_hub_spoke`          | Hub-spoke (tenant fabric or WAN branch mode)     |
| `build_security_stack`     | 5-tier security zone architecture                |
| `build_diagram_from_model` | Build from YAML topology model file              |

### Node and Link Primitives

| Tool            | Description                                       |
|-----------------|---------------------------------------------------|
| `add_device`    | Add typed network device with role/vendor/site    |
| `add_node`      | Add generic shape                                 |
| `add_edge`      | Add directed connector                            |
| `add_link`      | Add typed network link (fabric/uplink/management) |
| `add_container` | Add labelled container / swimlane group           |
| `update_node`   | Modify label, style, or geometry                  |
| `delete_node`   | Delete node and its connected edges               |

### Diagram Management

| Tool                   | Description                         |
|------------------------|-------------------------------------|
| `create_blank_diagram` | Create new blank .drawio file       |
| `read_diagram`         | Read raw XML content                |
| `write_diagram`        | Write / overwrite diagram XML       |
| `list_diagrams`        | List .drawio files in a folder      |
| `list_nodes`           | List all nodes and edges with IDs   |
| `auto_layout`          | Auto-arrange (TB / BT / LR / RL)   |
| `group_nodes`          | Wrap nodes into a container by bbox |

---

## Supported Device Roles

| Role                | Layer   | Description                |
|---------------------|---------|----------------------------|
| `spine`             | 0       | Spine / core switch        |
| `core_switch`       | 0       | Core layer switch          |
| `router`            | 0       | Router                     |
| `wan_router`        | 0       | WAN / edge router          |
| `internet`          | −1      | Internet gateway           |
| `firewall`          | 0       | Firewall                   |
| `load_balancer`     | 1       | Load balancer              |
| `border_leaf`       | 1       | Border leaf switch         |
| `branch_router`     | 1       | WAN branch router          |
| `leaf`              | 2       | ToR / leaf switch          |
| `application_server`| 3       | Application / web server   |
| `gpu_node`          | 3       | GPU compute node           |
| `compute_node`      | 3       | General compute            |
| `storage_node`      | 3       | Storage node               |
| `database_node`     | 4       | Database / persistence     |
| `management_switch` | sidebar | Out-of-band management     |
| `monitoring_node`   | sidebar | Monitoring / observability |

---

## Supported Link Types

| Type         | Style                       |
|--------------|-----------------------------|
| `fabric`     | Solid, strokeWidth=2        |
| `uplink`     | Solid, strokeWidth=1        |
| `management` | Dashed, grey                |
| `wan`        | Dashed, grey, strokeWidth=2 |
| `default`    | Plain connector             |

---

## Style Profiles

| Profile          | Description                            |
|------------------|----------------------------------------|
| `minimal`        | Plain color-coded rectangles (default) |
| `enterprise`     | Cisco-style stencil shapes             |
| `dark`           | Dark theme                             |
| `vendor-neutral` | draw.io built-in network shapes        |

---

## Validation Codes

| Code | Type    | Description                                  |
|------|---------|----------------------------------------------|
| E001 | Error   | Unknown device role                          |
| E002 | Error   | Duplicate device hostname                    |
| E003 | Error   | Empty device hostname                        |
| E004 | Error   | Link endpoint references unknown hostname    |
| E005 | Error   | Empty link endpoint                          |
| E006 | Error   | Unsupported topology type                    |
| E007 | Error   | Unsupported style profile                    |
| E008 | Error   | Device references undeclared site            |
| E009 | Error   | Unsupported hub_spoke mode                   |
| E010 | Error   | Container member references unknown hostname |
| E011 | Error   | Duplicate site name (multi_site)             |
| E012 | Error   | Unsupported interconnect type (multi_site)   |
| E013 | Error   | Site declares zero spines (multi_site)       |
| E014 | Error   | Site declares zero leafs (multi_site)        |
| W001 | Warning | topology not declared — defaulted            |
| W002 | Warning | No sites declared                            |
| W003 | Warning | No devices declared                          |
| W004 | Warning | No links declared                            |
| W005 | Warning | Device has no site assigned                  |
| W006 | Warning | hub_spoke topology_mode not declared         |
| W007 | Warning | interconnect type not declared (multi_site)  |
| W008 | Warning | Fewer than 2 sites declared (multi_site)     |

---

## Installation

```bash
git clone https://github.com/Eswarthemad/drawio-mcp-server.git
cd drawio-mcp-server

python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

For development (tests + linting):

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "drawio-mcp": {
      "command": "C:\\path\\to\\drawio-mcp-server\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\drawio-mcp-server\\server.py"]
    }
  }
}
```

Restart Claude Desktop after saving.

---

## Project Structure

```
drawio-mcp-server/
├── server.py             MCP tool registration (19 tools)
├── drawio.py             XML engine and topology builders
├── models.py             YAML topology model dataclasses
├── styles.py             Style profile resolver
├── validators.py         Model validation (E001–E014, W001–W008)
├── requirements.txt      Runtime dependencies
├── requirements-dev.txt  Dev dependencies (pytest, ruff)
├── examples/
│   ├── spine_leaf.yaml
│   └── multi_site.yaml
└── tests/
    ├── test_drawio.py
    ├── test_models.py
    ├── test_styles.py
    ├── test_validators.py
    └── test_multisite.py
```

---

## Version History

| Version | Highlights                                        |
|---------|---------------------------------------------------|
| v1.0.0  | 10 core tools — read/write/list/add/delete/layout |
| v1.1.0  | Network-aware primitives, spine-leaf builder      |
| v1.2.0  | YAML topology model, style profiles, validation   |
| v1.3.0  | Containers, hub-spoke, security stack             |
| v1.4.0  | 234-test suite, GitHub Actions CI, coverage gate  |
| v1.5.0  | Multi-site EVPN/DCI builder, E011–E014, W007–W008 |

---

## Roadmap

- Multi-page diagram support (logical / physical / traffic-flow views)
- VDOM architecture builder
- Additional topology examples

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

Released under the MIT License.