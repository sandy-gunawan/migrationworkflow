import json
import logging
import re
from uuid import UUID

from pydantic import ValidationError

from demo_common.contracts import DemoResult, Route, RouterDecision, SourceReference
from demo_common.fabric import US_WORKSPACE

logger = logging.getLogger(__name__)


class ToolEvidenceError(ValueError):
    pass


def _matches_agent(item: dict, response: dict, binding: dict) -> bool:
    reference = item.get("agent_reference", response.get("agent_reference", {}))
    return (
        reference.get("name") == binding["name"]
        and reference.get("version") == binding["version"]
    )


def _agent_text(response: dict, binding: dict) -> str:
    return "\n".join(
        part["text"]
        for item in response["output"]
        if item["type"] == "message" and _matches_agent(item, response, binding)
        for part in item["content"]
        if part["type"] == "output_text"
    )


def _tool_objects(text: str) -> list[dict]:
    decoder = json.JSONDecoder()
    remaining = text.strip()
    objects = []
    while remaining:
        try:
            value, end = decoder.raw_decode(remaining)
        except json.JSONDecodeError as exc:
            raise ToolEvidenceError("The tool returned an error or invalid JSON evidence.") from exc
        if not isinstance(value, dict):
            raise ToolEvidenceError("The tool did not return a structured evidence object.")
        value = value.get("structuredResponse", value)
        if not isinstance(value, dict):
            raise ToolEvidenceError("The structured tool response is invalid.")
        objects.append(value)
        remaining = remaining[end:].lstrip()
    if not objects:
        raise ToolEvidenceError("The tool returned no evidence.")
    return objects


def _fixture_sources(value: dict) -> list[SourceReference]:
    sources = value.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ToolEvidenceError("The tool returned no source references.")
    try:
        references = [SourceReference.model_validate(item) for item in sources]
    except ValidationError as exc:
        raise ToolEvidenceError("The tool returned invalid source references.") from exc
    if any(not item.id.startswith("urn:kppdemo:") for item in references):
        raise ToolEvidenceError("The tool returned a source outside the synthetic demo.")
    return references


def _sources(route: Route, value: dict) -> list[SourceReference]:
    if route in (Route.MCP, Route.REST_API):
        if value.get("demo_id") != "48254cc6" or value.get("synthetic") is not True:
            raise ToolEvidenceError("The tool returned non-demo data.")
        if route == Route.REST_API and (
            value.get("upstream_protocol") != "https_rest"
            or value.get("outbound_auth") != "managed_identity"
        ):
            raise ToolEvidenceError("The protected HTTPS REST hop is not verified.")
        return _fixture_sources(value)
    if route in (Route.KNOWLEDGE, Route.FOUNDRY_IQ):
        if value.get("outbound_auth") != "managed_identity":
            raise ToolEvidenceError("The retrieval hop did not use Managed Identity.")
        if route == Route.KNOWLEDGE:
            documents = value.get("documents")
            if (
                value.get("upstream_protocol") != "azure_ai_search_rest"
                or not isinstance(documents, list)
                or not documents
                or any(
                    not isinstance(item, dict)
                    or item.get("demo_id") != "48254cc6"
                    or item.get("synthetic") is not True
                    for item in documents
                )
            ):
                raise ToolEvidenceError("Search returned missing or out-of-scope documents.")
            return _fixture_sources(value)
        if (
            value.get("upstream_protocol") != "native_knowledge_base_rest"
            or value.get("knowledge_base") != "kppdemo-mining-knowledge"
        ):
            raise ToolEvidenceError("The result is not the native demo knowledge base.")
        result = value.get("result")
        references = result.get("references") if isinstance(result, dict) else None
        if not isinstance(references, list) or not references:
            raise ToolEvidenceError("The native knowledge base returned no references.")
        sources = []
        for item in references:
            key = item.get("docKey") if isinstance(item, dict) else None
            if not isinstance(key, str) or not re.fullmatch(r"DMO-DOC-\d{2}", key):
                raise ToolEvidenceError("The native knowledge reference is outside the demo.")
            sources.append(SourceReference(kind="knowledge_base_document", id=key))
        return sources
    if route == Route.FABRIC_DATA:
        answer = value.get("response")
        if not isinstance(answer, str):
            raise ToolEvidenceError("The native Fabric result has no structured production answer.")
        try:
            # Fabric appends prose and citation metadata after the required JSON record.
            record, _ = json.JSONDecoder().raw_decode(answer.lstrip())
        except json.JSONDecodeError as exc:
            raise ToolEvidenceError("The native Fabric production JSON record is missing.") from exc
        if not isinstance(record, dict) or record.get("status") != "success":
            raise ToolEvidenceError("The native Fabric data agent returned no production rows.")
        tonnes = record.get("tonnes")
        if (
            record.get("source_table") != "dbo.production"
            or record.get("site_id") not in ("MS01", "MS02")
            or not isinstance(record.get("date"), str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["date"])
            or record.get("shift") not in ("day", "night")
            or isinstance(tonnes, bool)
            or not isinstance(tonnes, (int, float))
            or not 0 <= tonnes < float("inf")
        ):
            raise ToolEvidenceError("The native Fabric production record is invalid.")
        documents = value.get("documents")
        if not isinstance(documents, list) or not documents:
            raise ToolEvidenceError("The native Fabric tool returned no source documents.")
        prefix = f"https://app.fabric.microsoft.com/groups/{US_WORKSPACE}/aiskills/"
        sources = []
        for item in documents:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("url"), str)
                or not item["url"].startswith(prefix)
                or not isinstance(item.get("title"), str)
                or not item["title"]
            ):
                raise ToolEvidenceError("The native Fabric source is outside the owned workspace.")
            sources.append(SourceReference(kind="fabric_data_agent", id=item["title"]))
        return sources
    raise ToolEvidenceError("This route must not dispatch a specialist.")


def normalize_specialist_result(
    response: dict, route: Route, run_id: UUID, binding: dict
) -> DemoResult:
    def failed(detail: str) -> DemoResult:
        logger.warning("Specialist evidence rejected: route=%s reason=%s", route, detail)
        return DemoResult(run_id=run_id, route=route, status="failed", error=detail)

    if response.get("status") != "completed" or response.get("error"):
        return failed("The native agent did not complete successfully.")

    calls = [item for item in response["output"] if item["type"] == "mcp_call"]
    if not calls:
        return failed("The agent supplied no actual tool execution evidence.")
    references = []
    try:
        for item in calls:
            if not _matches_agent(item, response, binding):
                raise ToolEvidenceError("An unexpected agent version executed the tool.")
            if item.get("status") != "completed" or item.get("error"):
                raise ToolEvidenceError("A native tool call failed.")
            output = item.get("output")
            if not isinstance(output, str):
                raise ToolEvidenceError("The native tool output is missing.")
            for value in _tool_objects(output):
                references.extend(_sources(route, value))
    except ToolEvidenceError as exc:
        return failed(str(exc))
    answer = _agent_text(response, binding)
    if not answer or not references:
        return failed("A grounded answer and actual source references are required.")
    unique = {(item.kind, item.id): item for item in references}
    return DemoResult(
        run_id=run_id,
        route=route,
        status="success",
        answer=answer,
        sources=list(unique.values()),
    )


def normalize_source_result(response: dict, run_id: UUID, source: dict) -> DemoResult:
    if response.get("status") != "completed" or response.get("error"):
        raise ToolEvidenceError("The native source workflow did not complete successfully.")
    actions = [item for item in response["output"] if item["type"] == "workflow_action"]
    if not actions or any(
        item.get("status") != "completed" or not _matches_agent(item, response, source)
        for item in actions
    ):
        raise ToolEvidenceError("The native source action/version evidence is invalid.")
    try:
        decision = RouterDecision.model_validate_json(
            _agent_text(response, source["agent_versions"]["router"])
        )
    except ValidationError as exc:
        raise ToolEvidenceError("The native router did not return a valid decision.") from exc
    route = decision.route
    activity = _agent_text(response, source)
    if f"KPP_ROUTE:{route.value}" not in activity.splitlines():
        raise ToolEvidenceError("The native route activity does not match the router.")
    invocations = [item for item in actions if item["kind"] == "InvokeAzureAgent"]
    calls = [item for item in response["output"] if item["type"] == "mcp_call"]
    if route.value in source["agent_versions"]:
        if len(invocations) != 2:
            raise ToolEvidenceError("The native source did not dispatch exactly one specialist.")
        return normalize_specialist_result(
            response, route, run_id, source["agent_versions"][route.value]
        )
    if len(invocations) != 1 or calls:
        raise ToolEvidenceError("A non-dispatch route dispatched an unexpected specialist/tool.")
    statuses = [
        line.removeprefix("KPP_STATUS:")
        for line in activity.splitlines()
        if line.startswith("KPP_STATUS:")
    ]
    if len(statuses) != 1 or statuses[0] not in (
        "blocked", "failed", "clarification", "unsupported"
    ):
        raise ToolEvidenceError("The native non-dispatch status is invalid.")
    text = "\n".join(
        line for line in activity.splitlines() if not line.startswith(("KPP_ROUTE:", "KPP_STATUS:"))
    ).strip()
    if not text:
        raise ToolEvidenceError("The native non-dispatch outcome has no explanation.")
    return DemoResult(
        run_id=run_id,
        route=route,
        status=statuses[0],
        answer=text if statuses[0] in ("clarification", "unsupported") else None,
        error=text if statuses[0] in ("blocked", "failed") else None,
    )
