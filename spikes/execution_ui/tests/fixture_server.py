import argparse

from spikes.execution_ui.launch import serve
from spikes.execution_ui.tests.test_server import FixtureRuntime


class BrowserFixture(FixtureRuntime):
    def __init__(self):
        super().__init__()
        self.info = {
            **self.info,
            "title": "Browser contract fixture",
            "description": "Fixture only; no Azure service is called.",
        }

    async def execute(self, request, emit):
        self.fail = request.question == "Fixture authorization failure."
        try:
            return await super().execute(request, emit)
        finally:
            self.fail = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    serve(BrowserFixture(), parser.parse_args().port)
