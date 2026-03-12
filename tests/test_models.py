"""
tests/test_models.py
Unit tests for models.py — YAML parsing, dataclass construction, edge cases.
"""

import sys
import os
import tempfile
import textwrap

import pytest

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import (
    load_model,
    TopologyModel,
    DiagramMeta,
    Device,
    Link,
    Site,
    Container,
    DEFAULT_TOPOLOGY,
    DEFAULT_STYLE_PROFILE,
    SUPPORTED_TOPOLOGIES,
    SUPPORTED_HUB_SPOKE_MODES,
)


# ==============================================================================
# Helpers
# ==============================================================================

def write_yaml(content: str) -> str:
    """Write YAML content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(textwrap.dedent(content))
    f.flush()
    return f.name


def cleanup(path: str) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


# ==============================================================================
# load_model — basic valid YAML
# ==============================================================================

class TestLoadModelBasic:

    def test_minimal_yaml(self):
        path = write_yaml("""
            meta:
              name: "Test Diagram"
              topology: spine_leaf
              style_profile: minimal
            sites:
              - name: DC1
            devices:
              - hostname: spine01
                role: spine
                site: DC1
            links:
              - a: spine01
                b: spine01
                type: fabric
        """)
        try:
            model = load_model(path)
            assert isinstance(model, TopologyModel)
            assert model.meta.name == "Test Diagram"
            assert model.meta.topology == "spine_leaf"
            assert model.meta.style_profile == "minimal"
            assert len(model.sites) == 1
            assert model.sites[0].name == "DC1"
            assert len(model.devices) == 1
            assert model.devices[0].hostname == "spine01"
            assert model.devices[0].role == "spine"
            assert len(model.links) == 1
        finally:
            cleanup(path)

    def test_topology_defaulted_flag(self):
        """When topology is missing, topology_defaulted should be True."""
        path = write_yaml("""
            meta:
              name: "No Topology"
            devices: []
            links: []
        """)
        try:
            model = load_model(path)
            assert model.meta.topology_defaulted is True
            assert model.meta.topology == DEFAULT_TOPOLOGY
        finally:
            cleanup(path)

    def test_topology_declared_flag(self):
        """When topology is present, topology_defaulted should be False."""
        path = write_yaml("""
            meta:
              topology: spine_leaf
        """)
        try:
            model = load_model(path)
            assert model.meta.topology_defaulted is False
        finally:
            cleanup(path)

    def test_style_profile_default(self):
        path = write_yaml("meta:\n  name: x\n")
        try:
            model = load_model(path)
            assert model.meta.style_profile == DEFAULT_STYLE_PROFILE
        finally:
            cleanup(path)

    def test_topology_mode_parsed(self):
        path = write_yaml("""
            meta:
              topology: hub_spoke
              topology_mode: wan_branch
        """)
        try:
            model = load_model(path)
            assert model.meta.topology_mode == "wan_branch"
        finally:
            cleanup(path)

    def test_topology_mode_empty_when_not_set(self):
        path = write_yaml("meta:\n  topology: spine_leaf\n")
        try:
            model = load_model(path)
            assert model.meta.topology_mode == ""
        finally:
            cleanup(path)


# ==============================================================================
# load_model — devices
# ==============================================================================

class TestLoadModelDevices:

    def test_device_fields(self):
        path = write_yaml("""
            meta:
              topology: spine_leaf
            sites:
              - name: DC1
            devices:
              - hostname: fw01
                role: firewall
                site: DC1
                vendor: Fortinet
                platform: FortiGate-4201F
                zone: DMZ
                redundancy_group: HA-1
            links: []
        """)
        try:
            model = load_model(path)
            d = model.devices[0]
            assert d.hostname == "fw01"
            assert d.role == "firewall"
            assert d.site == "DC1"
            assert d.vendor == "Fortinet"
            assert d.platform == "FortiGate-4201F"
            assert d.zone == "DMZ"
            assert d.redundancy_group == "HA-1"
        finally:
            cleanup(path)

    def test_multiple_devices(self):
        path = write_yaml("""
            meta:
              topology: spine_leaf
            devices:
              - hostname: spine01
                role: spine
              - hostname: spine02
                role: spine
              - hostname: leaf01
                role: leaf
            links: []
        """)
        try:
            model = load_model(path)
            assert len(model.devices) == 3
            hostnames = [d.hostname for d in model.devices]
            assert "spine01" in hostnames
            assert "leaf01" in hostnames
        finally:
            cleanup(path)

    def test_empty_devices(self):
        path = write_yaml("meta:\n  topology: spine_leaf\ndevices: []\nlinks: []\n")
        try:
            model = load_model(path)
            assert model.devices == []
        finally:
            cleanup(path)

    def test_missing_devices_key(self):
        path = write_yaml("meta:\n  topology: spine_leaf\n")
        try:
            model = load_model(path)
            assert model.devices == []
        finally:
            cleanup(path)


# ==============================================================================
# load_model — links
# ==============================================================================

class TestLoadModelLinks:

    def test_link_fields(self):
        path = write_yaml("""
            meta:
              topology: spine_leaf
            devices:
              - hostname: spine01
                role: spine
              - hostname: leaf01
                role: leaf
            links:
              - a: spine01
                b: leaf01
                type: fabric
        """)
        try:
            model = load_model(path)
            assert len(model.links) == 1
            lnk = model.links[0]
            assert lnk.a == "spine01"
            assert lnk.b == "leaf01"
            assert lnk.type == "fabric"
        finally:
            cleanup(path)

    def test_link_type_defaults_to_default(self):
        path = write_yaml("""
            meta:
              topology: spine_leaf
            devices:
              - hostname: a
                role: spine
              - hostname: b
                role: leaf
            links:
              - a: a
                b: b
        """)
        try:
            model = load_model(path)
            assert model.links[0].type == "default"
        finally:
            cleanup(path)


# ==============================================================================
# load_model — containers
# ==============================================================================

class TestLoadModelContainers:

    def test_container_parsed(self):
        path = write_yaml("""
            meta:
              topology: spine_leaf
            devices:
              - hostname: spine01
                role: spine
            containers:
              - name: ControlPlane
                label: Control Plane
                members:
                  - spine01
            links: []
        """)
        try:
            model = load_model(path)
            assert len(model.containers) == 1
            c = model.containers[0]
            assert c.name == "ControlPlane"
            assert c.label == "Control Plane"
            assert "spine01" in c.members
        finally:
            cleanup(path)

    def test_container_label_defaults_to_name(self):
        path = write_yaml("""
            meta:
              topology: spine_leaf
            containers:
              - name: Fabric
                members: []
            links: []
        """)
        try:
            model = load_model(path)
            assert model.containers[0].label == "Fabric"
        finally:
            cleanup(path)

    def test_no_containers_key(self):
        path = write_yaml("meta:\n  topology: spine_leaf\n")
        try:
            model = load_model(path)
            assert model.containers == []
        finally:
            cleanup(path)


# ==============================================================================
# load_model — error handling
# ==============================================================================

class TestLoadModelErrors:

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_model("/nonexistent/path/model.yaml")

    def test_invalid_yaml_raises(self):
        path = write_yaml("meta: [\ninvalid yaml }{{\n")
        try:
            with pytest.raises(Exception):
                load_model(path)
        finally:
            cleanup(path)

    def test_empty_yaml(self):
        """Empty YAML should produce a model with all defaults."""
        path = write_yaml("")
        try:
            model = load_model(path)
            assert isinstance(model, TopologyModel)
            assert model.devices == []
        finally:
            cleanup(path)


# ==============================================================================
# Constants
# ==============================================================================

class TestConstants:

    def test_supported_topologies_contains_expected(self):
        assert "spine_leaf" in SUPPORTED_TOPOLOGIES
        assert "hub_spoke" in SUPPORTED_TOPOLOGIES
        assert "security_stack" in SUPPORTED_TOPOLOGIES

    def test_supported_hub_spoke_modes(self):
        assert "tenant_fabric" in SUPPORTED_HUB_SPOKE_MODES
        assert "wan_branch" in SUPPORTED_HUB_SPOKE_MODES