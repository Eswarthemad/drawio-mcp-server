# drawio-mcp-server

A Python **Model Context Protocol (MCP) server** for generating and maintaining **draw.io architecture diagrams programmatically**.

This project enables AI assistants and automation tools to **read, modify, and generate draw.io diagrams** using structured commands instead of manual editing.

The long-term goal is to provide a **vendor-neutral, network-aware automation layer for infrastructure architecture diagrams**.

---

# Why This Project Exists

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

# What's New in v1.3.0

**Architecture containers**

Diagrams can now include **logical containers** for grouping infrastructure components such as racks, clusters, or availability zones.

**Hub-Spoke topology support**

In addition to spine-leaf fabrics, the model now supports **hub-spoke network layouts**.

**Improved validation**

Validation now checks:

* declared sites
* link endpoints
* topology compatibility
* device roles and style profiles

Errors and warnings are returned as **structured JSON reports**.

**New modules**

```
models.py
styles.py
validators.py
```

---

# Features

## Core Diagram Operations (v1.0.0)

* Read and write raw draw.io XML
* List diagram nodes and edges
* Add, update, and delete nodes
* Create connections between nodes
* Create blank diagrams
* Auto-layout (TB / BT / LR / RL)

---

## Network-Aware Primitives (v1.1.0)

* `add_device()` — add devices with semantic roles (spine, leaf, firewall, gpu_node, etc.)
* `add_link()` — add typed links (fabric, uplink, management)
* `build_spine_leaf_fabric()` — generate a full spine-leaf topology

---

## Diagram-as-Data / YAML Model (v1.2.0)

* `build_diagram_from_model()` — build a complete diagram from YAML
* Style profiles: `minimal`, `enterprise`, `dark`, `vendor-neutral`
* Full validation with structured JSON error reporting

---

## Containers and Extended Topologies (v1.3.0)

* Container support for logical grouping of devices
* Hub-spoke topology model
* Improved topology validation
* Expanded role-based styling

---

# Quick Start: YAML → Diagram

Example YAML topology:

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

  - hostname: leaf01
    role: leaf
    site: DC1

  - hostname: compute01
    role: compute_node
    site: DC1

links:
  - a: spine01
    b: leaf01
    type: fabric
  - a: leaf01
    b: compute01
    type: uplink
```

Generate the diagram:

```
build_diagram_from_model(
    path="diagrams/dc1.drawio",
    yaml_path="examples/spine_leaf.yaml"
)
```

---

# Example Output

Example files included in the repository:

```
examples/
 ├─ spine_leaf.yaml
 ├─ spine-leaf-model.drawio
 └─ spine-leaf-sample.drawio
```

These demonstrate **model-driven diagram generation**.

---

# Supported Device Roles

| Role              | Layer   | Description                |
| ----------------- | ------- | -------------------------- |
| spine             | 0       | Spine / core switch        |
| core_switch       | 0       | Core layer switch          |
| router            | 0       | Router                     |
| firewall          | 0       | Firewall                   |
| load_balancer     | 1       | Load balancer              |
| border_leaf       | 1       | Border leaf switch         |
| leaf              | 2       | ToR / leaf switch          |
| gpu_node          | 3       | GPU compute node           |
| compute_node      | 3       | General compute            |
| storage_node      | 3       | Storage node               |
| management_switch | sidebar | Out-of-band management     |
| monitoring_node   | sidebar | Monitoring / observability |

---

# Style Profiles

| Profile        | Description                            |
| -------------- | -------------------------------------- |
| minimal        | Plain color-coded rectangles (default) |
| enterprise     | Cisco-style stencil shapes             |
| dark           | Dark theme diagram                     |
| vendor-neutral | draw.io built-in network shapes        |

---

# All MCP Tools

| Tool                     | Description                   |
| ------------------------ | ----------------------------- |
| read_diagram             | Read raw XML                  |
| write_diagram            | Write raw XML                 |
| list_diagrams            | List .drawio files            |
| list_nodes               | List nodes and edges          |
| create_blank_diagram     | Create new diagram            |
| add_node                 | Add generic shape             |
| add_edge                 | Add generic connector         |
| update_node              | Modify node                   |
| delete_node              | Delete node                   |
| auto_layout              | Arrange diagram               |
| add_device               | Add role-based device         |
| add_link                 | Add typed network link        |
| build_spine_leaf_fabric  | Build spine-leaf fabric       |
| build_diagram_from_model | Build diagram from YAML model |

---

# Installation

```
git clone https://github.com/Eswarthemad/drawio-mcp-server.git
cd drawio-mcp-server

python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

---

# Claude Desktop Configuration

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

Restart Claude Desktop afterward.

---

# Project Structure

```
server.py        MCP tool registration
drawio.py        XML engine and topology builders
models.py        YAML topology model definitions
styles.py        Style profile resolver
validators.py    Model validation
examples/        Sample topology models and diagrams
```

---

# Version History

| Version | Highlights                       |
| ------- | -------------------------------- |
| v1.0.0  | Core diagram manipulation        |
| v1.1.0  | Network-aware primitives         |
| v1.2.0  | YAML topology models             |
| v1.3.0  | Containers and hub-spoke support |

---

# Roadmap

**Phase 5**

* Unit tests
* GitHub Actions CI
* Additional topology builders
* Multi-site architectures
* Diagram screenshots in README

---

# Contributing

Please read:

```
CONTRIBUTING.md
```

---

# License

Released under the MIT License.
