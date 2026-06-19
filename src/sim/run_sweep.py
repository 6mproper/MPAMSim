from __future__ import annotations

import argparse
import itertools
import json
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml

from src.config.loader import load_config

from .simulation import Simulation


def _set_dotted(root: Dict[str, object], dotted_path: str, value: object) -> None:
    keys = dotted_path.split(".")
    current = root
    for key in keys[:-1]:
        child = current.setdefault(key, {})
        if not isinstance(child, dict):
            raise ValueError(f"Cannot set {dotted_path}: {key} is not a mapping")
        current = child
    current[keys[-1]] = value


def _apply_alias(raw: Dict[str, object], key: str, value: object) -> None:
    if key == "policy":
        raw["policies"] = [{"name": value}]
        return
    if key in {"mc_count", "num_memory_controllers"}:
        controllers = raw["soc"]["memory"]["controllers"]
        raw["soc"]["memory"]["controllers"] = controllers[: int(value)]
        return
    if key == "background_rate_gbps":
        for workload in raw.get("workloads", []):
            if "background" in str(workload.get("name", "")).lower() or int(workload.get("partid", -1)) == 2:
                workload["injection_rate_gbps"] = float(value)
                workload.pop("injection_rate_mrps", None)
        return
    if key == "cores_active":
        ordered_cores = [
            core
            for cluster in raw["soc"].get("clusters", [])
            for core in cluster.get("cores", [])
        ]
        active = set(ordered_cores[: int(value)])
        for workload in raw.get("workloads", []):
            filtered = [
                requester
                for requester in workload.get("requesters", [])
                if ".t" not in requester or requester.split(".t", 1)[0] in active
            ]
            if filtered:
                workload["requesters"] = filtered
        return
    _set_dotted(raw, key, value)


def _combinations(sweep: Dict[str, List[object]]) -> Iterable[Tuple[Tuple[str, object], ...]]:
    keys = list(sweep)
    for values in itertools.product(*(sweep[key] for key in keys)):
        yield tuple(zip(keys, values))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a parameter sweep")
    parser.add_argument("--config", required=True)
    parser.add_argument("--sweep", required=True)
    parser.add_argument("--output", default="outputs/sweep")
    parser.add_argument("--until-ns", type=float)
    args = parser.parse_args()

    base_path = Path(args.config)
    base_raw = yaml.safe_load(base_path.read_text(encoding="utf-8"))
    sweep_document = yaml.safe_load(Path(args.sweep).read_text(encoding="utf-8")) or {}
    sweep = sweep_document.get("sweep", sweep_document)
    if not isinstance(sweep, dict) or not sweep:
        raise SystemExit("Sweep file must contain a non-empty sweep mapping")

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    index = []
    with tempfile.TemporaryDirectory(prefix="soc-flow-sweep-") as temp_dir:
        for run_index, combination in enumerate(_combinations(sweep)):
            raw = deepcopy(base_raw)
            labels = []
            for key, value in combination:
                _apply_alias(raw, key, value)
                labels.append(f"{key}-{value}")
            config_path = Path(temp_dir) / f"run_{run_index:03d}.yaml"
            config_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
            run_dir = output_root / ("run_{:03d}_{}".format(run_index, "_".join(labels)))
            result = Simulation.from_config(load_config(config_path)).run(args.until_ns)
            result.export(str(run_dir))
            index.append(
                {
                    "run": run_index,
                    "parameters": dict(combination),
                    "output": str(run_dir),
                    "issued": result.issued_requests,
                    "completed": result.completed_requests,
                }
            )
    (output_root / "sweep_index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    print(f"Completed {len(index)} sweep runs; index: {output_root / 'sweep_index.json'}")


if __name__ == "__main__":
    main()
