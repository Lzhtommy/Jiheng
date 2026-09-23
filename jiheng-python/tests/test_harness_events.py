import json

from app.agent.harness_runtime import _translate


def test_translate_tool_call_and_result_with_refs():
    names: dict[str, str] = {}
    refs: dict[str, dict] = {}
    call = {
        "type": "tool/call",
        "data": {
            "callId": "c1",
            "name": "mcp__jiheng_data__get_realtime_quote",
            "arguments": '{"symbols": ["sh600519"]}',
        },
    }
    result_text = json.dumps({"status": "success", "data": [], "sources": [{"title": "腾讯财经实时行情", "url": "u1"}]})
    result = {
        "type": "tool/result",
        "data": {
            "message": {
                "content": [
                    {"type": "tool-result", "toolCallId": "c1", "content": [{"type": "text", "text": result_text}]}
                ]
            }
        },
    }

    [call_event] = _translate(call, names, refs)
    [result_event] = _translate(result, names, refs)

    assert call_event.type == "tool_call"
    assert call_event.data == {"id": "c1", "name": "get_realtime_quote", "arguments": {"symbols": ["sh600519"]}}
    assert result_event.type == "tool_result"
    assert result_event.data["name"] == "get_realtime_quote"
    assert result_event.data["success"] is True
    assert list(refs) == ["u1"]


def test_translate_ignores_other_events():
    assert _translate({"type": "step/start", "data": {}}, {}, {}) == []
