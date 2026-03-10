# drawio-mcp-server

A Python **Model Context Protocol (MCP) server** for generating and maintaining **draw.io architecture diagrams programmatically**.

This project enables AI assistants and automation tools to **read, modify, and generate draw.io diagrams** using structured commands instead of manual editing.

The long-term goal is to provide a **vendor-neutral, network-aware automation layer for infrastructure architecture diagrams**.

---

## Why This Project Exists

Large infrastructure diagrams — especially **network architecture diagrams** — quickly become difficult to maintain manually.

This MCP server allows diagrams to be:

* generated programmatically from YAML topology models
* updated through automation
* modified by AI assistants
* version controlled like code

Instead of manually editing XML or dragging shapes in the UI, diagrams can be described as data and generated repeatably.

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

## What's New in v1.2.0

**Diagram-as-data** — describe your topology in YAML and generate a complete diagram in one call.

**Style profiles** — choose how your diagram looks independently of what it represents. Four profiles ship out of the box: `minimal`, `enterprise`, `dark`, and `vendor-neutral`.

**Validation** — the server validates your YAML before touching any file. If there are errors, you get a complete JSON report listing every problem — not just the first one.

**New modules:** `models.py`, `styles.py`, `validators.py`

---

## Features

### Core Diagram Operations (v1.0.0)

* Read and write raw draw.io XML
* List diagram nodes and edges
* Add, update, and delete nodes
* Create connections between nodes
* Create blank diagrams
* Auto-layout (TB / BT / LR / RL)

### Network-Aware Primitives (v1.1.0)

* `add_device()` — add devices with semantic roles (spine, leaf, firewall, gpu\_node, etc.) and structured metadata
* `add_link()` — add typed links (fabric, uplink, management)
* `build_spine_leaf_fabric()` — generate a complete spine-leaf topology in one call

### Diagram-as-Data / YAML Model (v1.2.0)

* `build_diagram_from_model()` — build a complete diagram from a YAML topology file
* Style profiles: `minimal` (default), `enterprise`, `dark`, `vendor-neutral`
* Full validation with structured JSON error reporting
* Topology defaulting with explicit warnings

---

## Quick Start: YAML to Diagram

Describe your topology in a YAML file:

```yaml
meta:
  name: "DC1 Spine-Leaf Fabric"
  topology: spine_leaf
  style_profile: minimal

sites:
  - name: DC1

devices:
  - hostname: spine01
    role: spine
    site: DC1
    vendor: NVIDIA
    platform: Spectrum-X

  - hostname: leaf01
    role: leaf
    site: DC1

  - hostname: compute01
    role: compute_node
    site: DC1
    vendor: NVIDIA
    platform: H200

links:
  - a: spine01
    b: leaf01
    type: fabric
  - a: leaf01
    b: compute01
    type: uplink
```

Then ask Claude to build it:

```
build_diagram_from_model(
    path="diagrams/dc1.drawio",
    yaml_path="examples/spine_leaf.yaml"
)
```

On success:

```json
{
  "status": "ok",
  "warnings": [],
  "spine_count": 2,
  "leaf_count": 4,
  "compute_count": 8,
  "link_count": 16
}
```

On failure, a full error report is returned — every issue, not just the first:

```json
{
  "status": "error",
  "errors": [
    {
      "code": "E001",
      "field": "devices[2].role",
      "message": "Unknown role 'superswitch'. Valid roles: spine, leaf, ..."
    },
    {
      "code": "E004",
      "field": "links[0].b",
      "message": "Link endpoint 'leaf99' does not match any declared device hostname."
    }
  ],
  "warnings": []
}
```

---

## Supported Device Roles

| Role | Layer | Description |
|---|---|---|
| `spine` | 0 | Spine / core switch |
| `core_switch` | 0 | Core layer switch |
| `router` | 0 | Router |
| `firewall` | 0 | Firewall |
| `load_balancer` | 1 | Load balancer |
| `border_leaf` | 1 | Border leaf / distribution switch |
| `leaf` | 2 | ToR / leaf switch |
| `gpu_node` | 3 | GPU compute node |
| `compute_node` | 3 | General compute node |
| `storage_node` | 3 | Storage node |
| `management_switch` | sidebar | Out-of-band management switch |
| `monitoring_node` | sidebar | Monitoring / observability node |

---

## Style Profiles

| Profile | Description | Dependencies |
|---|---|---|
| `minimal` | Plain colour-coded rectangles. **Default.** | None |
| `enterprise` | Cisco stencil shapes | Cisco shape library in draw.io |
| `dark` | Dark fills with light text | None |
| `vendor-neutral` | draw.io built-in network shapes | None |

---

## All 14 Tools

| Tool | Description |
|---|---|
| `read_diagram` | Read raw XML from a .drawio file |
| `write_diagram` | Write raw XML to a .drawio file |
| `list_diagrams` | List .drawio files in a folder |
| `list_nodes` | List all nodes and edges in a diagram |
| `create_blank_diagram` | Create a new empty .drawio file |
| `add_node` | Add a generic shape |
| `add_edge` | Add a generic connector |
| `update_node` | Update label, style, or position of a node |
| `delete_node` | Delete a node and its connected edges |
| `auto_layout` | Auto-arrange nodes (TB/BT/LR/RL) |
| `add_device` | Add a network device with role metadata |
| `add_link` | Add a typed network link |
| `build_spine_leaf_fabric` | Build a full spine-leaf topology |
| `build_diagram_from_model` | Build a diagram from a YAML topology file |

---

## Installation

Clone the repository:

```
git clone https://github.com/Eswarthemad/drawio-mcp-server.git
cd drawio-mcp-server
```

Create and activate a virtual environment:

```
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

Install dependencies:

```
pip install -r requirements.txt
```

---

## Claude Desktop Configuration

Add this to your `claude_desktop_config.json`:

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

Config file location:

* **Windows (Store):** `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude_desktop_config.json`
* **Windows (Standard):** `%APPDATA%\Claude\claude_desktop_config.json`
* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Restart Claude Desktop after updating the config. Open a new chat — Claude will pick up all 14 tools.

---

## Project Structure

```
server.py         MCP tool registration (14 tools)
drawio.py         XML I/O, diagram primitives, topology builders
models.py         Typed dataclasses + YAML parser (TopologyModel)
styles.py         Style profile resolver (4 profiles × 12 roles)
validators.py     Schema validation with structured JSON error reporting
requirements.txt  Python dependencies
examples/         Example YAML models and generated diagrams
```

### Module emergence rules

New modules are only introduced when there is real content to justify them:

| Module | Appears when |
|---|---|
| `layout.py` | Layout logic grows beyond one or two functions |
| `builders.py` | More than one topology builder needs orchestration |

---

## Example Files

| File | Description |
|---|---|
| `examples/spine_leaf.yaml` | 2-spine / 4-leaf / 8-compute YAML model |
| `examples/spine-leaf-sample.drawio` | Pre-built output for reference |

---

## Roadmap

**Phase 4 (upcoming)**

* Unit tests (`tests/`)
* GitHub Actions lint and test workflow
* Additional topology builders: hub-spoke, multi-site
* Screenshots in README

---

## Contributing

Contributions are welcome. Please read `CONTRIBUTING.md` for design principles and development guidelines.

---

## License

Released under the repository license. See `LICENSE`.