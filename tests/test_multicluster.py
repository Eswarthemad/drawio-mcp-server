"""
tests/test_multicluster.py
Unit tests for Phase 6 — multi-cluster (Rancher / K8s / OpenShift) topology.
Covers: build_multi_cluster(), models parsing, and validators E015-E019, W009-W010.
"""

import sys, os, json, tempfile, shutil
import pytest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import drawio
from models import (
    load_model, TopologyModel, DiagramMeta,
    ClusterSpec, NamespaceSpec, WorkloadSpec, RancherSpec,
)
from validators import validate


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="mc_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def path(tmp_dir, name="mc.drawio"):
    return os.path.join(tmp_dir, name)


# ═══════════════════════════════════════════════════════════════
# build_multi_cluster — basic behaviour
# ═══════════════════════════════════════════════════════════════

class TestBuildMultiClusterBasic:

    def test_default_call_creates_file(self, tmp_dir):
        p = path(tmp_dir)
        result = json.loads(drawio.build_multi_cluster(p))
        assert result["status"] == "ok"
        assert os.path.exists(p)

    def test_default_clusters_names(self, tmp_dir):
        p = path(tmp_dir)
        result = json.loads(drawio.build_multi_cluster(p))
        names = [c["name"] for c in result["clusters"]]
        assert names == ["cluster-a", "cluster-b"]

    def test_default_platforms(self, tmp_dir):
        p = path(tmp_dir)
        result = json.loads(drawio.build_multi_cluster(p))
        platforms = [c["platform"] for c in result["clusters"]]
        assert platforms == ["k8s", "openshift"]

    def test_rancher_disabled(self, tmp_dir):
        p = path(tmp_dir)
        result = json.loads(drawio.build_multi_cluster(p, rancher_enabled=False))
        assert result["rancher_enabled"] is False

    def test_bad_platform_returns_error(self, tmp_dir):
        p = path(tmp_dir)
        result = drawio.build_multi_cluster(p, clusters=[
            {"name": "x", "platform": "nomad"}
        ])
        assert result.startswith("ERROR")

    def test_bad_workload_type_returns_error(self, tmp_dir):
        p = path(tmp_dir)
        result = drawio.build_multi_cluster(p, clusters=[
            {"name": "x", "platform": "k8s", "namespaces": [
                {"name": "ns1", "workloads": [{"type": "cronjob", "name": "y"}]}
            ]}
        ])
        assert result.startswith("ERROR")

    def test_xml_is_valid(self, tmp_dir):
        p = path(tmp_dir)
        drawio.build_multi_cluster(p)
        tree = ET.parse(p)
        assert tree.getroot().tag == "mxGraphModel"

    def test_single_cluster_no_rancher(self, tmp_dir):
        p = path(tmp_dir)
        result = json.loads(drawio.build_multi_cluster(
            p, clusters=[{"name": "solo", "platform": "k8s"}],
            rancher_enabled=False,
        ))
        assert result["status"] == "ok"
        assert len(result["clusters"]) == 1


# ═══════════════════════════════════════════════════════════════
# Node / structure counts
# ═══════════════════════════════════════════════════════════════

class TestNodeCounts:

    def test_k8s_cluster_has_etcd_nodes(self, tmp_dir):
        """k8s platform should generate etcd nodes matching control_plane_nodes."""
        p = path(tmp_dir)
        drawio.build_multi_cluster(p, clusters=[
            {"name": "ca", "platform": "k8s", "control_plane_nodes": 3, "worker_nodes": 2}
        ], rancher_enabled=False)
        tree = ET.parse(p)
        labels = [c.get("value", "") for c in tree.getroot().findall(".//mxCell[@vertex='1']")]
        etcd_labels = [l for l in labels if "etcd" in l]
        assert len(etcd_labels) == 3

    def test_openshift_cluster_has_no_etcd_nodes(self, tmp_dir):
        """openshift platform should NOT generate separate etcd nodes."""
        p = path(tmp_dir)
        drawio.build_multi_cluster(p, clusters=[
            {"name": "cb", "platform": "openshift", "control_plane_nodes": 3, "worker_nodes": 2}
        ], rancher_enabled=False)
        tree = ET.parse(p)
        labels = [c.get("value", "") for c in tree.getroot().findall(".//mxCell[@vertex='1']")]
        etcd_labels = [l for l in labels if "etcd" in l]
        assert len(etcd_labels) == 0

    def test_master_and_worker_node_counts(self, tmp_dir):
        p = path(tmp_dir)
        drawio.build_multi_cluster(p, clusters=[
            {"name": "ca", "platform": "k8s", "control_plane_nodes": 3, "worker_nodes": 4}
        ], rancher_enabled=False)
        tree = ET.parse(p)
        labels = [c.get("value", "") for c in tree.getroot().findall(".//mxCell[@vertex='1']")]
        assert len([l for l in labels if "-master-" in l]) == 3
        assert len([l for l in labels if "-worker-" in l]) == 4

    def test_namespace_workload_chain(self, tmp_dir):
        p = path(tmp_dir)
        drawio.build_multi_cluster(p, clusters=[
            {"name": "ca", "platform": "k8s", "control_plane_nodes": 1, "worker_nodes": 1,
             "namespaces": [
                 {"name": "prod", "workloads": [
                     {"type": "ingress", "name": "ing1"},
                     {"type": "service", "name": "svc1"},
                     {"type": "deployment", "name": "dep1", "replicas": 2},
                 ]},
             ]},
        ], rancher_enabled=False)
        tree = ET.parse(p)
        labels = [c.get("value", "") for c in tree.getroot().findall(".//mxCell[@vertex='1']")]
        assert any("ingress: ing1" in l for l in labels)
        assert any("service: svc1" in l for l in labels)
        assert any("deployment: dep1 (x2)" in l for l in labels)

    def test_openshift_uses_project_label(self, tmp_dir):
        p = path(tmp_dir)
        drawio.build_multi_cluster(p, clusters=[
            {"name": "cb", "platform": "openshift", "control_plane_nodes": 1, "worker_nodes": 1,
             "namespaces": [{"name": "payments", "workloads": []}]},
        ], rancher_enabled=False)
        tree = ET.parse(p)
        labels = [c.get("value", "") for c in tree.getroot().findall(".//mxCell[@vertex='1']")]
        assert any(l.startswith("project: payments") for l in labels)

    def test_k8s_uses_namespace_label(self, tmp_dir):
        p = path(tmp_dir)
        drawio.build_multi_cluster(p, clusters=[
            {"name": "ca", "platform": "k8s", "control_plane_nodes": 1, "worker_nodes": 1,
             "namespaces": [{"name": "default", "workloads": []}]},
        ], rancher_enabled=False)
        tree = ET.parse(p)
        labels = [c.get("value", "") for c in tree.getroot().findall(".//mxCell[@vertex='1']")]
        assert any(l.startswith("namespace: default") for l in labels)

    def test_rancher_manage_links_to_each_cluster(self, tmp_dir):
        p = path(tmp_dir)
        drawio.build_multi_cluster(p, clusters=[
            {"name": "ca", "platform": "k8s"},
            {"name": "cb", "platform": "openshift"},
            {"name": "cc", "platform": "k8s"},
        ], rancher_enabled=True)
        tree = ET.parse(p)
        manage_edges = [
            c for c in tree.getroot().findall(".//mxCell[@edge='1']")
            if c.get("value") == "manage"
        ]
        assert len(manage_edges) == 3


# ═══════════════════════════════════════════════════════════════
# models.py — ClusterSpec / NamespaceSpec / WorkloadSpec / RancherSpec
# ═══════════════════════════════════════════════════════════════

class TestMultiClusterModel:

    def _yaml(self, content):
        import textwrap
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        f.write(textwrap.dedent(content))
        f.flush()
        return f.name

    def test_cluster_specs_parsed(self):
        p = self._yaml("""
            meta:
              topology: multi_cluster
            clusters:
              - name: cluster-a
                platform: k8s
                control_plane_nodes: 3
                worker_nodes: 3
              - name: cluster-b
                platform: openshift
                control_plane_nodes: 2
                worker_nodes: 5
        """)
        model = load_model(p)
        os.unlink(p)
        assert len(model.cluster_specs) == 2
        assert model.cluster_specs[0].name == "cluster-a"
        assert model.cluster_specs[0].platform == "k8s"
        assert model.cluster_specs[1].worker_nodes == 5

    def test_namespaces_and_workloads_parsed(self):
        p = self._yaml("""
            meta:
              topology: multi_cluster
            clusters:
              - name: ca
                platform: k8s
                namespaces:
                  - name: production
                    workloads:
                      - type: ingress
                        name: web-ingress
                      - type: deployment
                        name: web-app
                        replicas: 3
        """)
        model = load_model(p)
        os.unlink(p)
        ns = model.cluster_specs[0].namespaces[0]
        assert ns.name == "production"
        assert len(ns.workloads) == 2
        assert ns.workloads[1].type == "deployment"
        assert ns.workloads[1].replicas == 3

    def test_rancher_parsed(self):
        p = self._yaml("""
            meta:
              topology: multi_cluster
            rancher:
              enabled: false
              name: my-rancher
            clusters:
              - name: ca
                platform: k8s
        """)
        model = load_model(p)
        os.unlink(p)
        assert model.rancher.enabled is False
        assert model.rancher.name == "my-rancher"

    def test_rancher_defaults(self):
        p = self._yaml("meta:\n  topology: multi_cluster\n")
        model = load_model(p)
        os.unlink(p)
        assert model.rancher.enabled is True
        assert model.rancher.name == "rancher-server"

    def test_cluster_defaults(self):
        p = self._yaml("""
            meta:
              topology: multi_cluster
            clusters:
              - name: ca
        """)
        model = load_model(p)
        os.unlink(p)
        cl = model.cluster_specs[0]
        assert cl.platform == "k8s"
        assert cl.control_plane_nodes == 3
        assert cl.worker_nodes == 3
        assert cl.namespaces == []


# ═══════════════════════════════════════════════════════════════
# validators.py — E015-E019, W009-W010
# ═══════════════════════════════════════════════════════════════

def _make_mc_model(clusters=None, rancher_enabled=True):
    meta = DiagramMeta(name="MC", topology="multi_cluster", style_profile="minimal")
    model = TopologyModel(meta=meta, devices=[], links=[], sites=[], containers=[])
    model.cluster_specs = clusters if clusters is not None else [
        ClusterSpec("cluster-a", platform="k8s"),
        ClusterSpec("cluster-b", platform="openshift"),
    ]
    model.rancher = RancherSpec(enabled=rancher_enabled)
    return model


class TestMultiClusterValidation:

    def test_valid_model_passes(self):
        result = validate(_make_mc_model())
        assert result.ok is True

    def test_e015_bad_platform(self):
        model = _make_mc_model(clusters=[ClusterSpec("x", platform="nomad")])
        result = validate(model)
        codes = [e.code for e in result.errors]
        assert "E015" in codes

    def test_e016_zero_control_plane(self):
        model = _make_mc_model(clusters=[
            ClusterSpec("x", platform="k8s", control_plane_nodes=0, worker_nodes=3)
        ])
        result = validate(model)
        codes = [e.code for e in result.errors]
        assert "E016" in codes

    def test_e017_zero_workers(self):
        model = _make_mc_model(clusters=[
            ClusterSpec("x", platform="k8s", control_plane_nodes=3, worker_nodes=0)
        ])
        result = validate(model)
        codes = [e.code for e in result.errors]
        assert "E017" in codes

    def test_e018_duplicate_cluster_name(self):
        model = _make_mc_model(clusters=[
            ClusterSpec("dup", platform="k8s"),
            ClusterSpec("dup", platform="openshift"),
        ])
        result = validate(model)
        codes = [e.code for e in result.errors]
        assert "E018" in codes

    def test_e019_bad_workload_type(self):
        model = _make_mc_model(clusters=[
            ClusterSpec("x", platform="k8s", namespaces=[
                NamespaceSpec("ns1", workloads=[
                    WorkloadSpec(type="cronjob", name="bad")
                ])
            ])
        ])
        result = validate(model)
        codes = [e.code for e in result.errors]
        assert "E019" in codes

    def test_w009_rancher_disabled_multi_cluster(self):
        model = _make_mc_model(rancher_enabled=False)
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W009" in codes

    def test_w009_not_triggered_single_cluster(self):
        model = _make_mc_model(
            clusters=[ClusterSpec("solo", platform="k8s")],
            rancher_enabled=False,
        )
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W009" not in codes

    def test_w010_no_clusters(self):
        model = _make_mc_model(clusters=[])
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W010" in codes

    def test_all_valid_platforms_no_e015(self):
        for plat in ("k8s", "openshift"):
            model = _make_mc_model(clusters=[ClusterSpec("x", platform=plat)])
            result = validate(model)
            codes = [e.code for e in result.errors]
            assert "E015" not in codes

    def test_all_valid_workload_types_no_e019(self):
        for wtype in drawio.SUPPORTED_WORKLOAD_TYPES:
            model = _make_mc_model(clusters=[
                ClusterSpec("x", platform="k8s", namespaces=[
                    NamespaceSpec("ns1", workloads=[WorkloadSpec(type=wtype, name="w")])
                ])
            ])
            result = validate(model)
            codes = [e.code for e in result.errors]
            assert "E019" not in codes, f"E019 wrongly triggered for type: {wtype}"


# ═══════════════════════════════════════════════════════════════
# Full pipeline — YAML → validate → build
# ═══════════════════════════════════════════════════════════════

class TestFullPipeline:

    def test_yaml_to_diagram_pipeline(self, tmp_dir):
        import textwrap
        yaml_content = textwrap.dedent("""
            meta:
              name: "Test Multi-Cluster"
              topology: multi_cluster
              style_profile: minimal
            rancher:
              enabled: true
            clusters:
              - name: cluster-a
                platform: k8s
                control_plane_nodes: 2
                worker_nodes: 2
                namespaces:
                  - name: default
                    workloads:
                      - type: service
                        name: svc1
        """)
        yaml_path = path(tmp_dir, "test.yaml")
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        out_path = path(tmp_dir, "out.drawio")
        result = json.loads(drawio.build_diagram_from_model(out_path, yaml_path))
        assert result["status"] == "ok"
        assert os.path.exists(out_path)

    def test_yaml_with_bad_platform_fails_before_build(self, tmp_dir):
        import textwrap
        yaml_content = textwrap.dedent("""
            meta:
              topology: multi_cluster
            clusters:
              - name: cluster-a
                platform: nomad
        """)
        yaml_path = path(tmp_dir, "bad.yaml")
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        out_path = path(tmp_dir, "out.drawio")
        result = json.loads(drawio.build_diagram_from_model(out_path, yaml_path))
        assert result["status"] == "error"
        codes = [e["code"] for e in result["errors"]]
        assert "E015" in codes
        # file should NOT have been created — validation blocks the build
        assert not os.path.exists(out_path)
