import argparse
import hashlib
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import yaml

from demo_common.migration import compile_source

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("maf", "logicapps"), default="maf")
    args = parser.parse_args()
    baseline = json.loads(
        (ROOT / "source" / "foundry" / "baseline-manifest.json").read_text(encoding="utf-8")
    )
    source_path = ROOT / baseline["source"]["canonical_export"]
    source = source_path.read_bytes()
    if baseline["core_status"] != "PASS" or baseline["demo_id"] != "48254cc6":
        raise RuntimeError("The actual native source core baseline must pass first.")
    if hashlib.sha256(source).hexdigest() != baseline["source"]["sha256"]:
        raise RuntimeError("The source differs from the frozen native migration input.")
    normalization = ROOT / "src" / "demo_common" / "normalization.py"
    if hashlib.sha256(normalization.read_bytes()).hexdigest() != baseline["normalization_sha256"]:
        raise RuntimeError("Result normalization differs from the tested source baseline.")
    mapping = compile_source(source.decode("utf-8"))
    if args.target == "logicapps":
        from demo_common.logicapps import build_logic_workflow

        definition = build_logic_workflow(mapping)
        destination = ROOT / "targets" / "logicapps"
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "workflow.json").write_text(
            json.dumps(definition, indent=2) + "\n", encoding="utf-8",
        )
        report = {
            "demo_id": "48254cc6",
            "runtime": "azure_logic_apps_consumption",
            "source": str(source_path.relative_to(ROOT)),
            "source_sha256": mapping.source_sha256,
            "source_branches": len(mapping.branches),
            "unknown_semantics": "REJECT",
            "specialists_remain_foundry_hosted": True,
            "routing_and_native_invocation": "Logic Apps built-in HTTP and Switch actions",
            "normalization_boundary": "pure API; no routing, workflow execution or provider calls",
            "async_policy": (
                "Pinned synchronous Responses API; queued/incomplete outputs fail closed. "
                "No classic Thread/Run API or hidden agent loop."
            ),
            "lowering": {
                mapping.capture_action_id: "Compose original question/run ID",
                mapping.router_action_id: "MI HTTP named/versioned native prompt call",
                mapping.condition_action_id: "strict JSON route then mutually exclusive Switch",
                mapping.end_action_id: "native Response with comparable DTO and correlated run IDs",
                **{
                    branch.action_id: (
                        f"case {branch.route.value}: native HTTP + pure normalization"
                        if branch.agent else f"case {branch.route.value}: explicit source outcome"
                    )
                    for branch in mapping.branches
                },
            },
            "generic_lossless_converter": False,
            "scope": "verified_demo_source_subset_only",
        }
        migration = ROOT / "migration"
        migration.mkdir(exist_ok=True)
        (migration / "logicapps-mapping.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8",
        )
        print(json.dumps(report, indent=2))
        return
    try:
        declarative = version("agent-framework-declarative")
    except PackageNotFoundError:
        declarative = None
    compatibility = {
        "demo_id": "48254cc6",
        "source_sha256": mapping.source_sha256,
        "core_version": version("agent-framework-core"),
        "declarative_version": declarative,
        "direct_native_yaml_loader": (
            "UNVERIFIED_DEPENDENCY_DOWNLOAD_BLOCKED" if declarative is None else "NOT_SELECTED"
        ),
        "reason": (
            "Official wheel CDN TLS handshakes fail; no TLS bypass was used. "
            "Core 1.11.0 and compiler PyYAML were restored from hash-verified public cache wheels."
        ),
        "runtime": mapping.runtime,
        "official_declarative_yaml": False,
        "orchestration_only_migration": True,
        "specialists_remain_foundry_hosted": True,
        "supported_source_subset": [
            "OnConversationStart",
            "capture original user question",
            "versioned no-tool router with structured route",
            "mutually exclusive route equality conditions",
            "one versioned specialist per data branch",
            "literal route/status outcomes and explicit default failure",
            "shared per-run Foundry conversation and activity order",
            "EndConversation lowered to terminal typed workflow output",
        ],
        "unknown_semantics": "REJECT",
        "source_branches": len(mapping.branches),
        "data_branches": sum(branch.agent is not None for branch in mapping.branches),
        "source_baseline": baseline["source_outcomes"],
    }
    report = {
        **compatibility,
        "source": str(source_path.relative_to(ROOT)),
        "compiled": mapping.model_dump(mode="json"),
        "lowering": {
            mapping.capture_action_id: "RouterExecutor.start_conversation original user item",
            mapping.router_action_id: "RouterExecutor versioned native prompt call",
            mapping.condition_action_id: "WorkflowBuilder.add_switch_case_edge_group",
            mapping.end_action_id: "WorkflowContext.yield_output; no conversation deletion",
        },
    }
    migration = ROOT / "migration"
    migration.mkdir(exist_ok=True)
    (migration / "mapping.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    target = ROOT / "targets" / "maf"
    target.mkdir(parents=True, exist_ok=True)
    (target / "workflow.yaml").write_text(
        yaml.safe_dump(mapping.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )
    resources = ROOT / "src" / "maf_service" / "resources"
    resources.mkdir(exist_ok=True)
    (resources / "mapping.json").write_text(
        mapping.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (resources / "source.workflow.yaml").write_bytes(source)
    (resources / "baseline.json").write_text(
        json.dumps(
            {
                "source_sha256": mapping.source_sha256,
                "normalization_sha256": baseline["normalization_sha256"],
                "corpus_sha256": baseline["corpus_sha256"],
                "fabric_provider_sha256": baseline["fabric_provider_sha256"],
                "core_version": version("agent-framework-core"),
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    evidence = ROOT / "evidence" / "migration"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "maf-compatibility.json").write_text(
        json.dumps(compatibility, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(compatibility, indent=2))


if __name__ == "__main__":
    main()
