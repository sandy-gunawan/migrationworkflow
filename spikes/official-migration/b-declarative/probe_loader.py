import argparse
import asyncio
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from agent_framework.declarative import WorkflowFactory


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("yaml", type=Path)
    parser.add_argument("--input-json", default='{"name": "TRK001"}')
    parser.add_argument("--load-only", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "declarative_version": version("agent-framework-declarative"),
                "core_version": version("agent-framework-core"),
                "source": str(args.yaml.resolve()),
                "source_sha256": hashlib.sha256(args.yaml.read_bytes()).hexdigest(),
            },
            indent=2,
        ),
        flush=True,
    )

    factory = WorkflowFactory()
    workflow = factory.create_workflow_from_yaml_path(args.yaml)
    print(f"LOADED: {workflow.name}", flush=True)
    if args.load_only:
        return
    result = await workflow.run(json.loads(args.input_json))
    print(
        json.dumps(
            {
                "outputs": [str(value) for value in result.get_outputs()],
                "intermediate": [str(value) for value in result.get_intermediate_outputs()],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
