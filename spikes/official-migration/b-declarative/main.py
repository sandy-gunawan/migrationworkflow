import argparse
import asyncio
import json
import sys
from importlib.metadata import version
from pathlib import Path

from agent_framework.declarative import WorkflowFactory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trial_support import (  # noqa: E402
    AgentPool,
    check_source,
    verify_native_context,
    verify_run,
)


async def execute(question: str, *, native_context: bool = False) -> dict:
    source = Path(__file__).with_name("source.workflow.yaml")
    digest = check_source(source)
    async with AgentPool(question=question if native_context else None) as pool:
        factory = WorkflowFactory(
            agents=pool.agents,
            env_file=str(Path(__file__).resolve().parents[1] / ".env.example"),
        )
        workflow = factory.create_workflow_from_yaml_path(source)
        execution = await workflow.run(question)
        outputs = execution.get_outputs()
        if not all(isinstance(item, str) for item in outputs):
            raise TypeError("Unexpected output shape from the copied native workflow.")
        report = verify_run(question, outputs, pool.calls)
        if native_context:
            await verify_native_context(pool, outputs, report)
        report.update(
            {
                "path": "B: official WorkflowFactory",
                "source_sha256": digest,
                "source_modified": False,
                "core_version": version("agent-framework-core"),
                "declarative_version": version("agent-framework-declarative"),
                "manual_adapter": "PreserveNativeContext" if native_context else None,
            }
        )
        return report


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default="Show work orders for equipment TRK001.")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--native-context", action="store_true")
    args = parser.parse_args()
    report = await execute(args.question, native_context=args.native_context)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
