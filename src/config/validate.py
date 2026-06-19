from __future__ import annotations

import argparse

from .loader import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a SoC flow/MPAM simulation configuration")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    print(
        f"Configuration valid: {len(config.requesters)} requesters, "
        f"{len(config.caches)} caches, {len(config.memory_controllers)} memory controllers"
    )


if __name__ == "__main__":
    main()
