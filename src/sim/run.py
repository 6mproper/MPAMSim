from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from src.config.loader import load_config
from src.config.schema import PolicyConfig

from .simulation import Simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SoC flow-control / MPAM simulator")
    parser.add_argument("--config")
    parser.add_argument("--scenario")
    parser.add_argument("--output")
    parser.add_argument("--until-ns", type=float)
    parser.add_argument("--policy")
    args = parser.parse_args()

    config_path = args.config
    scenario = {}
    if args.scenario:
        scenario_path = Path(args.scenario)
        scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8")) or {}
        if not config_path:
            base = scenario.get("base_config")
            if not base:
                raise SystemExit("Scenario does not define base_config; pass --config")
            config_path = str(Path.cwd() / base)
    if not config_path:
        raise SystemExit("Pass --config or a scenario with base_config")

    config = load_config(config_path)
    if args.policy:
        config.policies = [PolicyConfig(name=args.policy)]
    elif scenario.get("policies") and len(scenario["policies"]) == 1:
        config.policies = [PolicyConfig(name=str(scenario["policies"][0]))]

    result = Simulation.from_config(config).run(args.until_ns)
    output = result.export(args.output)
    print(
        "Completed {} of {} issued requests; output: {}".format(
            result.completed_requests,
            result.issued_requests,
            output,
        )
    )


if __name__ == "__main__":
    main()
