import io
import json

from handoffbench.prompts import ACTION_SCHEMA
from handoffbench.providers import OpenAICompatibleProvider


class _Response:
    def __enter__(self):
        return io.StringIO(json.dumps({"choices": [{"message": {"content": "ok"}}]}))

    def __exit__(self, *_):
        return False


def test_openai_provider_omits_response_format_by_default(monkeypatch):
    bodies = []

    def urlopen(request, timeout):
        bodies.append(json.loads(request.data))
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    provider = OpenAICompatibleProvider()
    provider.complete([{"role": "user", "content": "summary"}], model="m", temperature=0,
                      seed=17, max_output_tokens=1600)
    provider.complete([{"role": "user", "content": "json"}], model="m", temperature=0,
                      response_schema=ACTION_SCHEMA, schema_name="receiver_action")
    assert "response_format" not in bodies[0]
    assert bodies[0]["seed"] == 17
    assert bodies[0]["max_tokens"] == 1600
    assert bodies[1]["response_format"]["json_schema"]["schema"] == ACTION_SCHEMA
    assert bodies[1]["response_format"]["json_schema"]["name"] == "receiver_action"
