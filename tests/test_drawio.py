"""
tests/test_drawio.py
Unit tests for drawio.py — all tests write real .drawio files to a tmp/ folder.
"""

import sys
import os
import json
import tempfile
import shutil
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import drawio


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def tmp_dir():
    """Create a temporary directory; remove it after the test."""
    d = tempfile.mkdtemp(prefix="drawio_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def blank(tmp_dir):
    """Return path to a fresh blank diagram."""
    path = os.path.join(tmp_dir, "test.drawio")
    drawio.write_file(path, drawio.blank_template("Test"))
    return path


# ==============================================================================
# blank_template / write_file / read_file
# ==============================================================================

class TestBlankTemplate:

    def test_blank_template_is_xml(self):
        xml = drawio.blank_template("TestPage")
        assert xml.strip().startswith("<")
        assert "mxGraph" in xml

    def test_write_and_read_roundtrip(self, tmp_dir):
        path = os.path.join(tmp_dir, "rt.drawio")
        xml  = drawio.blank_template("Roundtrip")
        drawio.write_file(path, xml)
        result = drawio.read_file(path)
        assert "mxGraph" in result

    def test_write_creates_file(self, tmp_dir):
        path = os.path.join(tmp_dir, "new.drawio")
        assert not os.path.exists(path)
        drawio.write_file(path, drawio.blank_template())
        assert os.path.exists(path)


# ==============================================================================
# insert_node
# ==============================================================================

class TestInsertNode:

    def test_insert_node_returns_id(self, blank):
        cell_id = drawio.insert_node(blank, "Router01", 100, 100, 120, 60)
        assert isinstance(cell_id, str)
        assert len(cell_id) > 0

    def test_insert_node_appears_in_list(self, blank):
        cell_id = drawio.insert_node(blank, "MyNode", 100, 100, 120, 60)
        nodes_json = drawio.get_nodes(blank)
        nodes = json.loads(nodes_json)
        ids = [n["id"] for n in nodes]
        assert cell_id in ids

    def test_insert_node_label_correct(self, blank):
        drawio.insert_node(blank, "LabeledNode", 100, 100, 120, 60)
        nodes = json.loads(drawio.get_nodes(blank))
        labels = [n["label"] for n in nodes]
        assert "LabeledNode" in labels

    def test_multiple_nodes_unique_ids(self, blank):
        id1 = drawio.insert_node(blank, "A", 100, 100, 120, 60)
        id2 = drawio.insert_node(blank, "B", 300, 100, 120, 60)
        assert id1 != id2


# ==============================================================================
# insert_edge
# ==============================================================================

class TestInsertEdge:

    def test_insert_edge_returns_id(self, blank):
        src = drawio.insert_node(blank, "Src", 100, 100, 120, 60)
        tgt = drawio.insert_node(blank, "Tgt", 400, 100, 120, 60)
        edge_id = drawio.insert_edge(blank, src, tgt, "link")
        assert isinstance(edge_id, str)
        assert len(edge_id) > 0

    def test_insert_edge_appears_in_list(self, blank):
        src = drawio.insert_node(blank, "Src", 100, 100, 120, 60)
        tgt = drawio.insert_node(blank, "Tgt", 400, 100, 120, 60)
        edge_id = drawio.insert_edge(blank, src, tgt)
        nodes = json.loads(drawio.get_nodes(blank))
        ids = [n["id"] for n in nodes]
        assert edge_id in ids

    def test_edge_has_correct_source_target(self, blank):
        src = drawio.insert_node(blank, "Src", 100, 100, 120, 60)
        tgt = drawio.insert_node(blank, "Tgt", 400, 100, 120, 60)
        edge_id = drawio.insert_edge(blank, src, tgt)
        nodes = json.loads(drawio.get_nodes(blank))
        edge = next(n for n in nodes if n["id"] == edge_id)
        assert edge["source"] == src
        assert edge["target"] == tgt


# ==============================================================================
# modify_node
# ==============================================================================

class TestModifyNode:

    def test_modify_label(self, blank):
        cell_id = drawio.insert_node(blank, "OldLabel", 100, 100, 120, 60)
        drawio.modify_node(blank, cell_id, label="NewLabel")
        nodes = json.loads(drawio.get_nodes(blank))
        node = next(n for n in nodes if n["id"] == cell_id)
        assert node["label"] == "NewLabel"

    def test_modify_nonexistent_cell_returns_error(self, blank):
        result = drawio.modify_node(blank, "nonexistent_id_xyz", label="X")
        assert "ERROR" in result or "not found" in result.lower()


# ==============================================================================
# remove_node
# ==============================================================================

class TestRemoveNode:

    def test_remove_node_disappears_from_list(self, blank):
        cell_id = drawio.insert_node(blank, "ToDelete", 100, 100, 120, 60)
        drawio.remove_node(blank, cell_id)
        nodes = json.loads(drawio.get_nodes(blank))
        ids = [n["id"] for n in nodes]
        assert cell_id not in ids

    def test_remove_node_also_removes_edges(self, blank):
        src = drawio.insert_node(blank, "Src", 100, 100, 120, 60)
        tgt = drawio.insert_node(blank, "Tgt", 400, 100, 120, 60)
        edge_id = drawio.insert_edge(blank, src, tgt)
        drawio.remove_node(blank, src)
        nodes = json.loads(drawio.get_nodes(blank))
        ids = [n["id"] for n in nodes]
        assert src not in ids
        assert edge_id not in ids

    def test_remove_nonexistent_cell_returns_error(self, blank):
        result = drawio.remove_node(blank, "ghost_id_xyz")
        assert "ERROR" in result or "not found" in result.lower()


# ==============================================================================
# add_device
# ==============================================================================

class TestAddDevice:

    def test_add_device_returns_id(self, blank):
        cid = drawio.add_device(blank, "spine01", "spine",
                                x=100, y=100, width=120, height=60)
        assert isinstance(cid, str)
        assert not cid.startswith("ERROR")

    def test_add_device_appears_in_list(self, blank):
        cid = drawio.add_device(blank, "leaf01", "leaf",
                                x=100, y=100, width=120, height=60)
        nodes = json.loads(drawio.get_nodes(blank))
        ids = [n["id"] for n in nodes]
        assert cid in ids

    def test_add_device_unknown_role_returns_error(self, blank):
        result = drawio.add_device(blank, "x", "superswitch",
                                   x=100, y=100, width=120, height=60)
        assert result.startswith("ERROR")

    def test_add_device_tooltip_contains_metadata(self, blank):
        cid = drawio.add_device(
            blank, "fw01", "firewall",
            vendor="Fortinet", platform="FG-4201F",
            x=100, y=100, width=120, height=60,
        )
        tree    = drawio.load_diagram(blank)
        root_el = drawio.get_root_cell(tree)
        cell    = root_el.find(f".//mxCell[@id='{cid}']")
        tooltip = json.loads(cell.get("tooltip", "{}"))
        assert tooltip["vendor"] == "Fortinet"
        assert tooltip["role"]   == "firewall"

    def test_add_device_with_parent_id(self, blank):
        """Device placed inside a container should have correct parent."""
        container_id = drawio.add_container(blank, "Zone A")
        cid = drawio.add_device(
            blank, "app01", "application_server",
            x=10, y=10, width=120, height=60,
            parent_id=container_id,
        )
        tree    = drawio.load_diagram(blank)
        root_el = drawio.get_root_cell(tree)
        cell    = root_el.find(f".//mxCell[@id='{cid}']")
        assert cell.get("parent") == container_id

    @pytest.mark.parametrize("role", list(drawio.ROLE_LAYER.keys()))
    def test_all_roles_accepted(self, blank, role):
        cid = drawio.add_device(blank, f"dev_{role}", role,
                                x=100, y=100, width=120, height=60)
        assert not cid.startswith("ERROR"), f"Role {role!r} rejected"


# ==============================================================================
# add_link
# ==============================================================================

class TestAddLink:

    def test_add_link_fabric(self, blank):
        src = drawio.add_device(blank, "spine01", "spine", x=100, y=100, width=120, height=60)
        tgt = drawio.add_device(blank, "leaf01",  "leaf",  x=400, y=100, width=120, height=60)
        eid = drawio.add_link(blank, src, tgt, "fabric")
        assert not eid.startswith("ERROR")

    @pytest.mark.parametrize("link_type", ["fabric", "uplink", "management", "wan", "default"])
    def test_all_link_types_accepted(self, blank, link_type):
        src = drawio.add_device(blank, "a", "spine", x=100, y=100, width=120, height=60)
        tgt = drawio.add_device(blank, "b", "leaf",  x=400, y=100, width=120, height=60)
        eid = drawio.add_link(blank, src, tgt, link_type)
        assert not eid.startswith("ERROR")


# ==============================================================================
# add_container
# ==============================================================================

class TestAddContainer:

    def test_add_container_returns_id(self, blank):
        cid = drawio.add_container(blank, "Control Plane")
        assert isinstance(cid, str)
        assert not cid.startswith("ERROR")

    def test_add_container_appears_in_diagram(self, blank):
        cid = drawio.add_container(blank, "Security Zone")
        tree    = drawio.load_diagram(blank)
        root_el = drawio.get_root_cell(tree)
        cell    = root_el.find(f".//mxCell[@id='{cid}']")
        assert cell is not None
        assert cell.get("container") == "1"

    def test_add_container_label_set(self, blank):
        cid = drawio.add_container(blank, "My Zone")
        tree    = drawio.load_diagram(blank)
        root_el = drawio.get_root_cell(tree)
        cell    = root_el.find(f".//mxCell[@id='{cid}']")
        assert cell.get("value") == "My Zone"

    def test_add_container_dark_profile(self, blank):
        cid = drawio.add_container(blank, "Dark Zone", style_profile="dark")
        assert not cid.startswith("ERROR")


# ==============================================================================
# group_nodes
# ==============================================================================

class TestGroupNodes:

    def test_group_nodes_returns_container_id(self, blank):
        id1 = drawio.insert_node(blank, "A", 100, 100, 120, 60)
        id2 = drawio.insert_node(blank, "B", 300, 100, 120, 60)
        cid = drawio.group_nodes(blank, [id1, id2], label="MyGroup")
        assert isinstance(cid, str)
        assert not cid.startswith("ERROR")

    def test_group_nodes_reparents_cells(self, blank):
        id1 = drawio.insert_node(blank, "A", 100, 100, 120, 60)
        cid = drawio.group_nodes(blank, [id1], label="Zone")
        tree    = drawio.load_diagram(blank)
        root_el = drawio.get_root_cell(tree)
        cell    = root_el.find(f".//mxCell[@id='{id1}']")
        assert cell.get("parent") == cid

    def test_group_nodes_unknown_cell_returns_error(self, blank):
        result = drawio.group_nodes(blank, ["ghost_id_xyz"], label="Zone")
        assert result.startswith("ERROR")


# ==============================================================================
# build_spine_leaf_fabric
# ==============================================================================

class TestBuildSpineLeaf:

    def test_basic_build_returns_json(self, tmp_dir):
        path = os.path.join(tmp_dir, "sl.drawio")
        result = drawio.build_spine_leaf_fabric(path, spine_count=2, leaf_count=2, compute_per_leaf=2)
        data = json.loads(result)
        assert data["status"] == "ok"

    def test_node_count_correct(self, tmp_dir):
        path = os.path.join(tmp_dir, "sl.drawio")
        result = json.loads(
            drawio.build_spine_leaf_fabric(path, spine_count=2, leaf_count=4, compute_per_leaf=2)
        )
        nodes = json.loads(drawio.get_nodes(path))
        vertices = [n for n in nodes if n["type"] == "vertex"]
        # 2 spines + 4 leaves + 8 computes = 14
        assert len(vertices) == 14

    def test_output_file_exists(self, tmp_dir):
        path = os.path.join(tmp_dir, "sl.drawio")
        drawio.build_spine_leaf_fabric(path, spine_count=2, leaf_count=2)
        assert os.path.exists(path)

    def test_style_profile_param_accepted(self, tmp_dir):
        path = os.path.join(tmp_dir, "sl_dark.drawio")
        result = json.loads(
            drawio.build_spine_leaf_fabric(path, spine_count=2, leaf_count=2, style_profile="dark")
        )
        assert result["status"] == "ok"


# ==============================================================================
# build_hub_spoke
# ==============================================================================

class TestBuildHubSpoke:

    def test_tenant_fabric_mode(self, tmp_dir):
        path = os.path.join(tmp_dir, "hs_tenant.drawio")
        result = json.loads(
            drawio.build_hub_spoke(path, mode="tenant_fabric", hub_count=2,
                                   spoke_count=3, endpoint_per_spoke=2)
        )
        assert result["status"] == "ok"
        assert result["mode"] == "tenant_fabric"
        assert result["hub_count"] == 2
        assert result["spoke_count"] == 3

    def test_wan_branch_mode(self, tmp_dir):
        path = os.path.join(tmp_dir, "hs_wan.drawio")
        result = json.loads(
            drawio.build_hub_spoke(path, mode="wan_branch", hub_count=1,
                                   spoke_count=3, endpoint_per_spoke=2)
        )
        assert result["status"] == "ok"
        assert result["mode"] == "wan_branch"

    def test_bad_mode_returns_error(self, tmp_dir):
        path = os.path.join(tmp_dir, "hs_bad.drawio")
        result = drawio.build_hub_spoke(path, mode="warp_drive")
        assert result.startswith("ERROR")

    def test_output_file_exists(self, tmp_dir):
        path = os.path.join(tmp_dir, "hs.drawio")
        drawio.build_hub_spoke(path, mode="tenant_fabric")
        assert os.path.exists(path)


# ==============================================================================
# build_security_stack
# ==============================================================================

class TestBuildSecurityStack:

    def test_basic_security_stack(self, tmp_dir):
        path = os.path.join(tmp_dir, "sec.drawio")
        result = json.loads(
            drawio.build_security_stack(path, firewall_count=2, lb_count=2,
                                        app_count=4, db_count=2)
        )
        assert result["status"] == "ok"
        assert result["firewall_count"] == 2

    def test_without_internet_tier(self, tmp_dir):
        path = os.path.join(tmp_dir, "sec_noint.drawio")
        result = json.loads(
            drawio.build_security_stack(path, include_internet=False)
        )
        assert result["status"] == "ok"
        assert result["include_internet"] is False

    def test_without_lb_tier(self, tmp_dir):
        path = os.path.join(tmp_dir, "sec_nolb.drawio")
        result = json.loads(
            drawio.build_security_stack(path, include_lb=False)
        )
        assert result["status"] == "ok"
        assert result["include_lb"] is False

    def test_custom_names(self, tmp_dir):
        path = os.path.join(tmp_dir, "sec_custom.drawio")
        result = json.loads(
            drawio.build_security_stack(
                path,
                firewall_names=["fw-primary", "fw-standby"],
                app_names=["web01", "web02"],
                lb_count=1,
                lb_names=["lb-main"],
                db_count=1,
                db_names=["db-primary"],
            )
        )
        assert result["status"] == "ok"
        nodes = json.loads(drawio.get_nodes(path))
        labels = [n["label"] for n in nodes if n["type"] == "vertex"]
        assert "fw-primary" in labels
        assert "fw-standby" in labels
        assert "web01" in labels

    def test_output_file_exists(self, tmp_dir):
        path = os.path.join(tmp_dir, "sec.drawio")
        drawio.build_security_stack(path)
        assert os.path.exists(path)