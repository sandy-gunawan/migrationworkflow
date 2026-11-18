import asyncio
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from azure.core.credentials import TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import AzureCliCredential
from pydantic import ValidationError

from demo_common.contracts import DemoRequest, DemoResult
from demo_common.normalization import normalize_specialist_result
from spikes.execution_ui.server import RunFailure
from spikes.execution_ui.sources import (
    definition_snapshot,
    native_definition_sources,
    python_source,
)
from spikes.logicapps_ui.access import AUDIENCE, RESOURCE_ID, SUBSCRIPTION
from tools.azure_job import require_logic_callback

ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)
SOURCE_SHA256 = "8a1b3b54903f26864bf81fad662e847cc97df18a945f536db9ff78b90aa4a8e1"
RUN_NAME = re.compile(r"[A-Za-z0-9_-]{1,120}")


class NativeLogicRuntime:
    def __init__(
        self,
        *,
        credential: TokenCredential | None = None,
        client: httpx.AsyncClient | None = None,
        poll_interval: float = 1.5,
    ):
        fixture = credential is not None or client is not None
        self.credential = credential or AzureCliCredential(subscription=SUBSCRIPTION)
        self.client = client or httpx.AsyncClient(timeout=300, follow_redirects=False)
        self.poll_interval = poll_interval
        self.manifest = json.loads(
            (ROOT / "config" / "logicapps-manifest.json").read_text(encoding="utf-8")
        )
        if self.manifest["id"] != RESOURCE_ID or self.manifest["demo_id"] != "48254cc6":
            raise ValueError("The configured Logic App is not the owned demo.")
        self.callback = require_logic_callback(self.manifest["callback_url"])
        self.workflow_file = ROOT / "targets" / "logicapps" / "workflow.json"
        self.definition = definition_snapshot(self.workflow_file, "json")
        self.expected_definition = json.loads(self.definition["text"])
        self.sources, nodes = native_definition_sources(self.workflow_file)
        self.nodes = {node["id"]: node for node in nodes}
        for key, symbol, label, explanation in (
            (
                "workflow",
                "NativeLogicRuntime.execute",
                "Python menghubungkan UI ke Logic Apps",
                "Python mengirim pertanyaan dan mengamati riwayat. Router dan Switch tetap "
                "dijalankan oleh Logic Apps di Azure, bukan oleh Python atau MAF.",
            ),
            (
                "history",
                "NativeLogicRuntime.actions",
                "Baca status action native",
                "Status dan timestamp dibaca dari API run history untuk run yang sama. "
                "Polling adalah pengamatan berkala, bukan streaming pikiran agent.",
            ),
            (
                "verification",
                "NativeLogicRuntime.verify_result",
                "Periksa hasil dan bukti",
                "Run ID, source hash, action terpilih dan evidence native diperiksa. "
                "HTTP 200 dengan status blocked tidak diubah menjadi retrieval sukses.",
            ),
        ):
            self.sources[key] = {
                "key": key,
                **python_source(
                    Path(__file__),
                    symbol,
                    label,
                    explanation,
                ),
            }
        self.info = {
            "kind": "logicapps",
            "title": "Logic Apps execution bench",
            "service": "local-logicapps-ui",
            "identity_mode": "unit_fixture" if fixture else "azure_cli",
            "engine": "Native Azure Logic Apps / Python gateway",
            "run_label": "Jalankan Logic Apps",
            "description": "Browser mengirim pertanyaan ke Python; workflow native Azure "
            "memanggil router, memilih Switch dan menjalankan specialist.",
            "waiting_note": "Action diamati melalui run history Azure. Jika run ID belum "
            "tersedia, UI hanya menyatakan sedang menunggu. Tool diketahui "
            "setelah response native selesai, bukan saat agent berpikir.",
            "guide_name": "logicapps-ui-walkthrough.html",
            "source_sha256": SOURCE_SHA256,
        }

    async def headers(self) -> dict:
        token = await asyncio.to_thread(self.credential.get_token, AUDIENCE + "/.default")
        return {"Authorization": "Bearer " + token.token}

    async def arm(self, suffix: str = "", *, extra: dict | None = None) -> dict:
        if suffix and not re.fullmatch(
            r"/runs(?:/[A-Za-z0-9_-]+(?:/actions(?:/[A-Za-z0-9_-]+)?)?)?",
            suffix,
        ):
            raise ValueError("Only the owned workflow and its run/action metadata may be read.")
        response = await self.client.get(
            AUDIENCE + RESOURCE_ID + suffix,
            params={"api-version": "2016-06-01", **(extra or {})},
            headers=await self.headers(),
        )
        if response.is_error:
            raise RunFailure(
                f"Riwayat Logic Apps ditolak/gagal: HTTP {response.status_code}.",
                upstream_status=response.status_code,
            )
        return response.json()

    async def verify_workflow(self):
        resource = await self.arm()
        properties = resource["properties"]
        # Azure adds an empty root parameters object when the source omits it.
        expected = {"parameters": {}, **self.expected_definition}
        actual = {"parameters": {}, **properties["definition"]}
        if (
            resource.get("tags", {}).get("demo_id") != "48254cc6"
            or resource["identity"]["principalId"] != self.manifest["principal_id"]
            or properties["state"] != "Enabled"
            or properties["accessControl"]["triggers"]["sasAuthenticationPolicy"]["state"]
            != "Disabled"
            or actual != expected
        ):
            raise RunFailure("Definisi, identitas, status atau guard SAS workflow demo berubah.")

    async def actions(self, native_run: str) -> list[dict]:
        if not RUN_NAME.fullmatch(native_run):
            raise ValueError("Invalid owned native run identifier.")
        suffix = f"/runs/{native_run}/actions"
        page = await self.arm(suffix)
        result, seen = [], set()
        for _ in range(10):
            result.extend(page["value"])
            link = page.get("nextLink")
            if not link:
                return result
            parsed = urlsplit(link)
            if (
                parsed.scheme != "https"
                or parsed.hostname != "management.azure.com"
                or parsed.username
                or parsed.password
                or parsed.fragment
                or parsed.path.lower() != (RESOURCE_ID + suffix).lower()
                or link in seen
            ):
                raise RunFailure("Pagination riwayat keluar dari run demo atau berulang.")
            seen.add(link)
            response = await self.client.get(link, headers=await self.headers())
            if response.is_error:
                raise RunFailure(
                    "Halaman riwayat native tidak dapat dibaca.",
                    upstream_status=response.status_code,
                )
            page = response.json()
        raise RunFailure("Riwayat native melebihi sepuluh halaman.")

    def content_url(self, url: str, native_run: str, action: str) -> str:
        parsed, callback = urlsplit(url), urlsplit(self.callback)
        prefix = callback.path.split("/triggers/", 1)[0]
        if (
            parsed.scheme != "https"
            or parsed.hostname != callback.hostname
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
            or parsed.fragment
            or not RUN_NAME.fullmatch(native_run)
            or action not in self.nodes
            or parsed.path != f"{prefix}/runs/{native_run}/actions/{action}/contents/ActionOutputs"
        ):
            raise ValueError("Content link is not part of the owned workflow/run/action.")
        return url

    async def native_output(self, native_run: str, action: dict) -> dict:
        name = action["name"]
        properties = action["properties"]
        if "outputsLink" not in properties:
            detail = await self.arm(f"/runs/{native_run}/actions/{name}")
            properties = detail["properties"]
        if "outputsLink" not in properties:
            raise RunFailure("Response native action belum tersedia untuk verifikasi.")
        link = self.content_url(properties["outputsLink"]["uri"], native_run, name)
        response = await self.client.get(link)
        if response.is_error:
            # Never include the signed link in errors or browser events.
            raise RunFailure(
                "Isi response native tidak dapat dibaca.", upstream_status=response.status_code
            )
        return response.json()["body"]

    def observe_actions(self, actions: list[dict], seen: dict, emit: Callable[[dict], None]):
        statuses = {
            "Succeeded": "done",
            "Skipped": "skipped",
            "Failed": "failed",
            "TimedOut": "failed",
            "Cancelled": "failed",
            "Aborted": "failed",
            "Running": "running",
            "Waiting": "waiting",
        }
        for action in actions:
            name, properties = action["name"], action["properties"]
            if name not in self.nodes:
                logger.info("Generated native metadata has no source action: %s", name)
                continue
            status = properties["status"]
            if seen.get(name) == status:
                continue
            if status not in statuses:
                raise RunFailure("Status action native belum didukung: " + status)
            seen[name] = status
            node = self.nodes[name]
            reference = node["definition"].get("inputs", {}).get("body", {})
            reference = reference.get("agent_reference") if isinstance(reference, dict) else None
            phase = (
                "router"
                if name == "classify_question"
                else "specialist"
                if name.startswith("invoke_")
                else "normalization"
                if name.startswith("normalize_")
                else "routing"
                if name == "route_question"
                else "outcome"
                if node["branch"] in ("work_iq", "fabric_iq", "clarification", "unsupported")
                else "context"
            )
            emit(
                {
                    "phase": phase,
                    "status": statuses[status],
                    "step_id": name,
                    "code_key": name,
                    "label": name.replace("_", " "),
                    "detail": self.sources[name]["lessons"][0]["explanation"],
                    "agent_name": reference["name"] if reference else None,
                    "agent_version": reference["version"] if reference else None,
                    "route": node["branch"],
                    "cloud_status": status,
                    "native_started": properties.get("startTime"),
                    "native_ended": properties.get("endTime"),
                }
            )

    async def verify_result(
        self,
        request: DemoRequest,
        response: httpx.Response,
        native_run: str,
        actions: list[dict],
        emit: Callable[[dict], None],
    ) -> dict:
        result = DemoResult.model_validate(response.json())
        proof = response.headers
        if (
            proof.get("x-kpp-orchestrator") != "logic_apps"
            or proof.get("x-kpp-source-sha256") != SOURCE_SHA256
            or result.run_id != request.run_id
            or not RUN_NAME.fullmatch(native_run)
        ):
            raise RunFailure("Bukti source, orchestrator atau korelasi run tidak sesuai.")
        completed = {
            item["name"] for item in actions if item["properties"]["status"] == "Succeeded"
        }
        invoked = {name for name in completed if name.startswith("invoke_")}
        native_ids = [
            value for value in proof.get("x-kpp-native-responses", "").split(",") if value
        ]
        if "classify_question" not in completed:
            raise RunFailure("Run history tidak membuktikan router selesai.")
        if result.status == "success":
            expected = "invoke_" + result.route.value
            if invoked != {expected} or len(native_ids) != 2:
                raise RunFailure("Jumlah specialist/response native tidak sesuai.")
            action = next(item for item in actions if item["name"] == expected)
            native = await self.native_output(native_run, action)
            binding = self.nodes[expected]["definition"]["inputs"]["body"]["agent_reference"]
            verified = normalize_specialist_result(native, result.route, request.run_id, binding)
            if verified != result or native.get("id") != native_ids[1]:
                raise RunFailure("Jawaban/sumber berbeda dari evidence native yang dibaca kembali.")
            for item in native.get("output", []):
                if item.get("type") == "mcp_call":
                    emit(
                        {
                            "phase": "tool",
                            "status": "done",
                            "step_id": expected + "_tool",
                            "code_key": expected,
                            "label": "Bukti tool aktual: " + item["name"],
                            "detail": "Tool dibaca setelah respons native selesai.",
                            "agent_name": binding["name"],
                            "agent_version": binding["version"],
                            "tool_name": item["name"],
                            "route": result.route.value,
                            "native_response_id": native["id"],
                        }
                    )
        elif result.status in ("blocked", "clarification", "unsupported"):
            if invoked or len(native_ids) != 1:
                raise RunFailure("Branch non-dispatch tidak boleh menjalankan specialist.")
        return {
            "result": result.model_dump(mode="json"),
            "trace": {
                "orchestrator": "native_logic_apps",
                "native_run_id": native_run,
                "native_response_ids": native_ids,
                "source_sha256": SOURCE_SHA256,
                "native_actions": [
                    {"name": item["name"], "status": item["properties"]["status"]}
                    for item in actions
                ],
                "python_role": "Gateway, native history observer and evidence verifier",
            },
        }

    async def execute(self, request: DemoRequest, emit: Callable[[dict], None]) -> dict:
        emit(
            {
                "phase": "workflow",
                "status": "running",
                "step_id": "submit_native_workflow",
                "code_key": "workflow",
                "label": "Menghubungkan workflow native",
                "detail": "Memeriksa resource lalu mengirim pertanyaan; token tetap di Python.",
            }
        )
        pending = None
        try:
            await self.verify_workflow()
            headers = {**await self.headers(), "x-ms-client-tracking-id": str(request.run_id)}
            pending = asyncio.create_task(
                self.client.post(
                    self.callback,
                    json=request.model_dump(mode="json"),
                    headers=headers,
                )
            )
            seen, observed_run, observations = {}, None, []
            while not pending.done():
                runs = await self.arm("/runs", extra={"$top": "30"})
                matching = [
                    item["name"]
                    for item in runs["value"]
                    if item["properties"].get("correlation", {}).get("clientTrackingId")
                    == str(request.run_id)
                ]
                if len(matching) > 1:
                    raise RunFailure("Tracking ID cocok dengan lebih dari satu run native.")
                if matching:
                    observed_run = matching[0]
                    observations = await self.actions(observed_run)
                    self.observe_actions(observations, seen, emit)
                if not pending.done():
                    await asyncio.sleep(self.poll_interval)
            response = await pending
            if response.status_code not in (200, 502):
                raise RunFailure(
                    f"Request Logic Apps gagal: HTTP {response.status_code}. "
                    "Periksa OAuth caller policy dan az login; tidak ada hasil pengganti.",
                    upstream_status=response.status_code,
                )
            native_run = response.headers.get("x-kpp-logic-run", "")
            if observed_run is not None and observed_run != native_run:
                raise RunFailure("Run yang dipoll berbeda dari run pada response.")
            observations = await self.actions(native_run)
            self.observe_actions(observations, seen, emit)
            output = await self.verify_result(request, response, native_run, observations, emit)
            output["trace"]["live_history_correlated"] = observed_run is not None
            emit(
                {
                    "phase": "workflow",
                    "status": "done",
                    "step_id": "native_result_verified",
                    "code_key": "verification",
                    "label": "Hasil dan run history terverifikasi",
                    "detail": "Run ID dan status bisnis terverifikasi; blocked bukan retrieval.",
                }
            )
            return output
        except (
            ClientAuthenticationError,
            httpx.RequestError,
            ValidationError,
            json.JSONDecodeError,
        ) as error:
            raise RunFailure(
                "Identity, koneksi atau bentuk response gagal; periksa log backend. "
                f"Jenis: {type(error).__name__}.",
            ) from error
        finally:
            if pending is not None and not pending.done():
                await pending

    async def close(self):
        await self.client.aclose()
        self.credential.close()
