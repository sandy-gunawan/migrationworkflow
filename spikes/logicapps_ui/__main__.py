from spikes.execution_ui.launch import arguments, serve, stop_ui
from spikes.logicapps_ui.client import NativeLogicRuntime


def main():
    parser = arguments("Start the local native Logic Apps workbench.", 8766)
    args = parser.parse_args()
    if args.stop:
        stop_ui(args.port, "local-logicapps-ui")
        return
    serve(NativeLogicRuntime(), args.port)


if __name__ == "__main__":
    main()
