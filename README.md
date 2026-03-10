# Drawio MCP Server

A Python **Model Context Protocol (MCP) server** for generating and maintaining **draw.io architecture diagrams programmatically**.

This project enables AI assistants and automation tools to **read, modify, and generate draw.io diagrams** using structured commands instead of manual editing.

The long-term goal is to provide a **vendor-neutral automation layer for network and infrastructure architecture diagrams**.

---

# Why This Project Exists

Large infrastructure diagrams — especially **network architecture diagrams** — quickly become difficult to maintain manually.

This MCP server allows diagrams to be:

* generated programmatically
* updated through automation
* modified by AI assistants
* version controlled like code

Instead of manually editing XML or dragging shapes in the UI, diagrams can be updated through repeatable operations.

Example workflow:

```
AI Assistant
     │
     │ MCP
     ▼
drawio-mcp-server
     │
     ▼
.drawio diagram files
```

---

# Features

## Core Diagram Operations

The server provides tools to safely manipulate draw.io diagrams:

* Read existing draw.io diagrams
* List diagram nodes and edges
* Add new nodes
* Create connections between nodes
* Update node properties
* Delete nodes and connected edges
* Create blank diagrams
* Automatic diagram layout

These operations allow AI tools to modify diagrams **without directly editing raw XML**.

---

# Network-Aware Diagram Tools (v1.1.0)

Version **1.1.0** introduces **network-aware primitives** designed for infrastructure diagrams.

New capabilities include:

* **add_device()** – create devices with semantic roles (spine, leaf, firewall, etc.)
* **add_link()** – create styled links between devices
* **build_spine_leaf_fabric()** – automatically generate a spine-leaf topology

These primitives make it easier to build common network architectures programmatically.

---

# Example MCP Capabilities

Create a new diagram:

```
create_blank_diagram("network.drawio")
```

Add devices with semantic roles:

```
add_device("fabric.drawio", "spine01", role="spine")
add_device("fabric.drawio", "leaf01", role="leaf")
```

Connect devices:

```
add_link("fabric.drawio", spine_id, leaf_id)
```

Generate a complete topology:

```
build_spine_leaf_fabric(
    "fabric.drawio",
    spine_count=2,
    leaf_count=4
)
```

Auto layout the diagram:

```
auto_layout("fabric.drawio")
```

---

# Example Output

An example generated topology is included:

```
examples/spine-leaf-sample.drawio
```

This demonstrates the **spine-leaf fabric builder** and network-aware styling.

---

# Installation

Clone the repository:

```
git clone https://github.com/<your-repo>/drawio-mcp-server.git
cd drawio-mcp-server
```

Create a virtual environment:

```
python -m venv venv
```

Activate it:

Linux / macOS:

```
source venv/bin/activate
```

Windows:

```
venv\Scripts\activate
```

Install dependencies:

```
pip install -r requirements.txt
```

---

# Running the MCP Server

Start the server:

```
python server.py
```

The server exposes MCP tools that allow AI assistants to manipulate draw.io diagrams.

---

# Example Use Cases

This project is particularly useful for:

* network architecture diagrams
* data center topology diagrams
* GPU cluster networking
* infrastructure documentation
* automated documentation pipelines
* AI-assisted architecture design
* version-controlled diagrams

---

# Project Structure

```
server.py        MCP server and tool definitions
drawio.py        draw.io XML helpers and diagram primitives
examples/        example generated diagrams
```

Additional modules may be introduced as the project evolves.

Possible future modules:

```
layout.py        advanced diagram layouts
builders.py      topology generators
validators.py    diagram validation tools
styles.py        visual style presets
models.py        YAML/JSON topology models
```

---

# Roadmap

Future improvements may include:

* hub-spoke topology builder
* multi-site network layouts
* YAML / JSON architecture models
* diagram validation tools
* style profiles for architecture diagrams

The goal is to evolve this project into a **general-purpose architecture diagram automation toolkit**.

---

# Contributing

Contributions are welcome.

Please read:

```
CONTRIBUTING.md
```

for design principles and development guidelines.

---

# License

This project is released under the repository's license.
