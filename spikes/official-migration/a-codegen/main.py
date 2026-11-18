import argparse
import asyncio
import json
import sys
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trial_support import (  # noqa: E402
    AgentPool,
    check_source,
    verify_native_context,
    verify_run,
)
from workflow import Run, build_workflow  # noqa: E402


async def execute(question: str, *, native_context: bool = True) -> dict:
    digest = check_source(Path(__file__).with_name("source.workflow.yaml"))
    async with AgentPool(question=question if native_context else None) as pool:
        workflow = build_workflow(pool.agents)
        execution = await workflow.run(Run(question))
        outputs = execution.get_outputs()
        report = verify_run(question, outputs, pool.calls)
        if native_context:
            await verify_native_context(pool, outputs, report)
        report.update(
            {
                "path": "A: Toolkit-guided Copilot code-first generation",
                "source_sha256": digest,
                "core_version": version("agent-framework-core"),
                "connector_version": version("agent-framework-foundry"),
                "generation_origin": "current Copilot session following official Toolkit guidance",
                "ui_chat_handoff": "NOT_SENT: interactive confirmation was unavailable",
            }
        )
        return report


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default="Show work orders for equipment TRK001.")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = await execute(args.question)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
