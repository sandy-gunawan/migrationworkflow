import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from spikes.execution_ui.launch import arguments, serve, stop_ui  # noqa: E402


def main():
    parser = arguments("Start Cara 1 with an external YAML file.", 8767)
    parser.add_argument("--workflow", type=Path)
    args = parser.parse_args()
    if args.stop:
        stop_ui(args.port, "local-maf-declarative-ui")
        return
    if args.workflow is None:
        parser.error("--workflow must identify the approved external YAML file.")
    from spikes.declarative_ui.runtime import DeclarativeRuntime

    serve(DeclarativeRuntime(args.workflow), args.port)


if __name__ == "__main__":
    main()
