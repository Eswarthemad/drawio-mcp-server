"""
tests/test_multisite.py
Unit tests for Phase 5 — multi-site topology.
Covers: build_multi_site(), models, validators.
"""

import sys
import os
import json
import tempfile
import shutil
import pytest
from models import DiagramMeta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import drawio
from models import load_model, TopologyModel, SiteSpec, InterconnectSpec
from validators import validate


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="ms_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def path(tmp_dir, name="ms.drawio"):
    return os.path.join(tmp_dir, name)


# ═══════════════════════════════════════════════════════════════
# build_multi_site — basic behaviour
# ═══════════════════════════════════════════════════════════════

class TestBuildMultiSiteBasic:

    def test_default_call_creates_file(self, tmp_dir):
        p = path(tmp_dir)
        result = json.loads(drawio.build_multi_site(p))
        assert result["status"] == "ok"
        assert os.path.exists(p)

    def test_returns_correct_site_names(self, tmp_dir):
        p = path(tmp_dir)
        sites = [
            {"name": "dc1", "spines": 2, "leafs": 4},
            {"name": "dc2", "spines": 2, "leafs": 4},
        ]
        result = json.loads(drawio.build_multi_site(p, sites=sites))
        assert result["sites"] == ["dc1", "dc2"]

    def test_three_site_topology(self, tmp_dir):
        p = path(tmp_dir)
        sites = [
            {"name": "dc1", "spines": 2, "leafs": 4},
            {"name": "dc2", "spines": 2, "leafs": 4},
            {"name": "dc3", "spines": 2, "leafs": 2},
        ]
        result = json.loads(drawio.build_multi_site(p, sites=sites))
        assert result["status"] == "ok"
        assert len(result["sites"]) == 3

    def test_bad_interconnect_type_returns_error(self, tmp_dir):
        p = path(tmp_dir)
        result = drawio.build_multi_site(p, interconnect_type="warp_drive")
        assert result.startswith("ERROR")

    def test_all_interconnect_types_accepted(self, tmp_dir):
        for ic in ("evpn", "vxlan", "ospf", "bgp", "static"):
            p = path(tmp_dir, f"ms_{ic}.drawio")
            result = json.loads(drawio.build_multi_site(p, interconnect_type=ic))
            assert result["status"] == "ok", f"Failed for interconnect type: {ic}"

    def test_xml_is_valid_drawio(self, tmp_dir):
        import xml.etree.ElementTree as ET
        p = path(tmp_dir)
        drawio.build_multi_site(p)
        tree = ET.parse(p)
        root = tree.getroot()
        assert root.tag == "mxGraphModel"


# ═══════════════════════════════════════════════════════════════
# Node counts
# ═══════════════════════════════════════════════════════════════

class TestNodeCounts:

    def test_node_count_2site_no_compute(self, tmp_dir):
        """2 sites × (2 spines + 4 leafs) = 12 device nodes + 2 DCI + 2 site containers + 1 band = 17 total.
        We just check devices only (vertices that are not containers).
        """
        p = path(tmp_dir)
        sites = [
            {"name": "dc1", "spines": 2, "leafs": 4, "compute_per_leaf": 0},
            {"name": "dc2", "spines": 2, "leafs": 4, "compute_per_leaf": 0},
        ]
        drawio.build_multi_site(p, sites=sites, dci_nodes=2)
        nodes = json.loads(drawio.get_nodes(p))
        vertices = [n for n in nodes if n["type"] == "vertex"]
        # 2 sites + 1 band + 4 spines + 8 leafs + 2 DCI = 17
        assert len(vertices) == 17

    def test_compute_nodes_added(self, tmp_dir):
        p = path(tmp_dir)
        sites = [
            {"name": "dc1", "spines": 2, "leafs": 2, "compute_per_leaf": 2},
            {"name": "dc2", "spines": 2, "leafs": 2, "compute_per_leaf": 0},
        ]
        drawio.build_multi_site(p, sites=sites, dci_nodes=0)
        nodes = json.loads(drawio.get_nodes(p))
        labels = [n["label"] for n in nodes if n["type"] == "vertex"]
        compute_labels = [label for label in labels if "compute" in label.lower()]
        # dc1: 2 leafs × 2 compute = 4 compute nodes
        assert len(compute_labels) == 4

    def test_edge_count_spine_leaf_fullmesh(self, tmp_dir):
        """Each site: 2 spines × 4 leafs = 8 fabric edges. 2 sites = 16 fabric edges."""
        p = path(tmp_dir)
        sites = [
            {"name": "dc1", "spines": 2, "leafs": 4},
            {"name": "dc2", "spines": 2, "leafs": 4},
        ]
        drawio.build_multi_site(p, sites=sites, dci_nodes=2)
        nodes = json.loads(drawio.get_nodes(p))
        edges = [n for n in nodes if n["type"] == "edge"]
        # 16 fabric + 4 cross-site (2 up + 2 down) + 1 DCI peer = 21
        assert len(edges) >= 20


# ═══════════════════════════════════════════════════════════════
# models.py — SiteSpec + InterconnectSpec
# ═══════════════════════════════════════════════════════════════

class TestMultiSiteModel:

    def _yaml(self, content):
        import textwrap
        import tempfile
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        f.write(textwrap.dedent(content))
        f.flush()
        return f.name

    def test_site_specs_parsed(self):
        p = self._yaml("""
            meta:
              topology: multi_site
            sites:
              - name: dc1
                spines: 2
                leafs: 4
              - name: dc2
                spines: 3
                leafs: 6
            interconnect:
              type: evpn
              dci_nodes: 2
        """)
        model = load_model(p)
        os.unlink(p)
        assert len(model.site_specs) == 2
        assert model.site_specs[0].name == "dc1"
        assert model.site_specs[1].spines == 3
        assert model.site_specs[1].leafs == 6

    def test_interconnect_parsed(self):
        p = self._yaml("""
            meta:
              topology: multi_site
            sites:
              - name: dc1
                spines: 2
                leafs: 4
            interconnect:
              type: vxlan
              dci_nodes: 4
        """)
        model = load_model(p)
        os.unlink(p)
        assert model.interconnect.type == "vxlan"
        assert model.interconnect.dci_nodes == 4

    def test_interconnect_defaults(self):
        p = self._yaml("meta:\n  topology: multi_site\n")
        model = load_model(p)
        os.unlink(p)
        assert model.interconnect.type == "evpn"
        assert model.interconnect.dci_nodes == 2


# ═══════════════════════════════════════════════════════════════
# validators.py — multi_site error/warning codes
# ═══════════════════════════════════════════════════════════════


def _make_ms_model(sites=None, interconnect_type="evpn", dci_nodes=2):
    meta = DiagramMeta(name="MS", topology="multi_site", style_profile="minimal")
    model = TopologyModel(meta=meta, devices=[], links=[], sites=[], containers=[])
    model.site_specs = sites or [
        SiteSpec("dc1", spines=2, leafs=4),
        SiteSpec("dc2", spines=2, leafs=4),
    ]
    model.interconnect = InterconnectSpec(type=interconnect_type, dci_nodes=dci_nodes)
    return model


class TestMultiSiteValidation:

    def test_valid_model_passes(self):
        result = validate(_make_ms_model())
        assert result.ok is True

    def test_e011_duplicate_site_name(self):
        model = _make_ms_model(sites=[SiteSpec("dc1"), SiteSpec("dc1")])
        result = validate(model)
        codes = [e.code for e in result.errors]
        assert "E011" in codes

    def test_e012_bad_interconnect_type(self):
        model = _make_ms_model(interconnect_type="warp_tunnel")
        result = validate(model)
        codes = [e.code for e in result.errors]
        assert "E012" in codes

    def test_e013_zero_spines(self):
        model = _make_ms_model(sites=[SiteSpec("dc1", spines=0, leafs=4), SiteSpec("dc2")])
        result = validate(model)
        codes = [e.code for e in result.errors]
        assert "E013" in codes

    def test_e014_zero_leafs(self):
        model = _make_ms_model(sites=[SiteSpec("dc1", spines=2, leafs=0), SiteSpec("dc2")])
        result = validate(model)
        codes = [e.code for e in result.errors]
        assert "E014" in codes

    def test_w008_single_site_warns(self):
        model = _make_ms_model(sites=[SiteSpec("dc1", spines=2, leafs=4)])
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W008" in codes

    def test_all_interconnect_types_valid(self):
        for ic in ("evpn", "vxlan", "ospf", "bgp", "static"):
            model = _make_ms_model(interconnect_type=ic)
            result = validate(model)
            codes = [e.code for e in result.errors]
            assert "E012" not in codes, f"E012 wrongly triggered for type: {ic}"