# Contributing

Thank you for your interest in contributing.

This project aims to provide a **vendor-neutral MCP server for generating and maintaining network architecture diagrams using draw.io**. Contributions that improve usability, automation, and extensibility are welcome.

## Design Principles

Please keep the following principles in mind when contributing:

* **Vendor neutral** – Avoid assumptions tied to a specific hardware vendor.
* **Deterministic behavior** – Diagrams generated from the same inputs should always be identical.
* **Minimal dependencies** – Prefer the Python standard library when possible.
* **Automation friendly** – The tool should work well in scripts, CI pipelines, and AI-driven workflows.
* **Readable diagrams** – Layouts should favor clarity for infrastructure and architecture documentation.

## Development Setup

1. Clone the repository.
2. Create a Python virtual environment.
3. Install dependencies.

Example:

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Project Structure

The project is organized so that draw.io file handling, layout logic, and MCP tooling can evolve independently.

Typical structure:

```
server.py     # MCP tool definitions
drawio.py     # draw.io XML helpers and primitives
layout.py     # diagram layout logic (introduced as needed)
builders.py   # topology builders (future)
```

Modules are introduced gradually to avoid premature complexity.

## Contribution Ideas

Useful contributions include:

* New network topology builders (spine-leaf, hub-spoke, etc.)
* Improved layout algorithms
* Diagram style presets
* Validation rules for topology models
* Example architecture diagrams
* Documentation improvements

## Pull Requests

When submitting a PR:

* Explain **what problem is being solved**
* Keep changes **focused and minimal**
* Include **examples or screenshots** if diagram behavior changes
* Update documentation if necessary

Small, incremental improvements are preferred over large refactors.

## Reporting Issues

If you encounter a problem:

Please include:

* Python version
* MCP client used
* Example diagram or command
* Error output if available

Clear reproduction steps help resolve issues quickly.

## License

By contributing, you agree that your contributions will be licensed under the project's license.
