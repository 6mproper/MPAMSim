from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Dict

import pytest
import yaml


@pytest.fixture
def base_config() -> Dict[str, object]:
    return {
        "simulation": {"time_ns": 100_000, "seed": 7, "control_interval_ns": 20_000},
        "soc": {
            "clusters": [{"id": "cluster0", "cores": ["cpu0", "cpu1"], "l3": "slc0"}],
            "core": {"threads_per_core": 1},
            "caches": [
                {
                    "id": "slc0",
                    "level": "L3",
                    "size_bytes": 1_048_576,
                    "line_size": 64,
                    "ways": 4,
                    "shared_by_cores": ["cpu0", "cpu1"],
                    "hit_latency_ns": 10,
                }
            ],
            "noc": {
                "topology": "mesh",
                "routers": 2,
                "link_bandwidth_gbps": 256,
                "router_latency_ns": 2,
                "queue_depth": 128,
                "virtual_channels": 2,
                "average_hops": 1,
            },
            "memory": {
                "controllers": [
                    {
                        "id": "mc0",
                        "channels": 1,
                        "bandwidth_gbps_per_channel": 64,
                        "scheduler": "priority_rr",
                        "queue_depth": 512,
                        "base_latency_ns": 40,
                        "token_bucket_window_ns": 50,
                        "aging_ns": 5000,
                    }
                ]
            },
        },
        "requesters": {
            "auto_expand_cpu_threads": True,
            "defaults": {"max_outstanding": 64},
            "core_attach_nodes": {"cpu0": "r0", "cpu1": "r1"},
            "explicit": [],
        },
        "mpam": {
            "partid_width": 8,
            "pmg_width": 8,
            "partitions": [
                {"partid": 1, "name": "protected"},
                {"partid": 2, "name": "background"},
            ],
            "msc_controls": [],
        },
        "workloads": [],
        "policies": [{"name": "static_mpam"}],
        "outputs": {
            "dir": "outputs/test",
            "formats": ["json", "csv"],
            "trace_requests": False,
            "visualization": {"generate_report": True, "report_format": "html"},
        },
    }


def write_config(tmp_path: Path, config: Dict[str, object], name: str = "config.yaml") -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture
def config_writer(tmp_path):
    def writer(config: Dict[str, object], name: str = "config.yaml") -> Path:
        return write_config(tmp_path, deepcopy(config), name)

    return writer
