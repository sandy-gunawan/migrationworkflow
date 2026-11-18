import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT = ROOT / "spikes" / "official-migration" / ".env.example"


@dataclass(frozen=True)
class WorkflowFile:
    path: Path
    text: str
    sha256: str
    loaded_at: str

    @classmethod
    def load(cls, path: Path) -> "WorkflowFile":
        path = path.resolve(strict=True)
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        baseline = json.loads(
            (ROOT / "src" / "maf_service" / "resources" / "baseline.json").read_text(
                encoding="utf-8"
            )
        )
        if digest != baseline["source_sha256"]:
            raise ValueError(
                "YAML integrity check failed: this demo accepts only the approved frozen source. "
                "This is a demo guard, not a WorkflowFactory limitation."
            )
        return cls(path, raw.decode("utf-8"), digest, datetime.now(timezone.utc).isoformat())

    def create(self, agents: dict):
        from agent_framework.declarative import WorkflowFactory

        factory = WorkflowFactory(
            agents=agents, env_file=str(ENVIRONMENT) if ENVIRONMENT.is_file() else None,
        )
        return factory.create_workflow_from_yaml(self.text, base_path=self.path.parent)

    def definition(self) -> dict:
        return {
            "path": self.path.relative_to(ROOT).as_posix()
            if self.path.is_relative_to(ROOT)
            else str(self.path),
            "language": "yaml",
            "text": self.text,
            "sha256": self.sha256,
            "loaded_at": self.loaded_at,
        }
