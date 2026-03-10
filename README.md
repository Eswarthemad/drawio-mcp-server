# Drawio MCP Server

A Python **Model Context Protocol (MCP) server** for generating and maintaining **draw.io architecture diagrams programmatically**.

This project enables AI assistants and automation tools to **read, modify, and generate draw.io diagrams** using structured commands instead of manual editing.

The long-term goal is to provide a **vendor-neutral automation layer for network and infrastructure architecture diagrams**.

---

# Why This Project Exists

Large infrastructure diagrams — especially network architectures — quickly become difficult to maintain manually.

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

Current capabilities include:

* Read existing draw.io diagrams
* List diagram nodes and edges
* Add new nodes
* Create connections between nodes
* Update node properties
* Delete nodes and connected edges
* Create blank diagrams
* Automatic diagram layout

These operations allow AI tools to safely modify diagrams without directly editing raw XML.

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

# Example MCP Capabilities

Examples of actions an AI assistant can perform through the MCP server:

Create a new diagram

```
create_blank_diagram("network.drawio")
```

Add nodes

```
add_node("network.drawio", "Core Switch")
add_node("network.drawio", "Firewall")
```

Connect devices

```
add_edge("network.drawio", source_id, target_id)
```

Auto layout

```
auto_layout("network.drawio")
```

---

# Example Use Cases

This project is especially useful for:

* network architecture diagrams
* data center topologies
* infrastructure documentation
* automated documentation pipelines
* AI-assisted architecture design
* version-controlled diagrams

---

# Project Structure

```
server.py    MCP server and tool definitions
drawio.py    draw.io XML helpers and primitives
```

Additional modules will be introduced gradually as the project evolves.

Planned modules include:

```
layout.py      advanced diagram layouts
builders.py    topology generators
validators.py  diagram validation tools
styles.py      visual style presets
models.py      YAML/JSON topology models
```

---

# Roadmap

Planned improvements include:

* topology builders (spine-leaf, hub-spoke, etc.)
* network-aware layout algorithms
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
