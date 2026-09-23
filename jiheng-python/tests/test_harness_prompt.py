from app.agent.harness_runtime import _build_prompt


def test_single_message_is_sent_as_is():
    assert _build_prompt([{"role": "user", "content": "你好"}]) == "你好"


def test_history_is_included_before_current_question():
    prompt = _build_prompt(
        [
            {"role": "user", "content": "宁德时代怎么样"},
            {"role": "assistant", "content": "宁德时代是动力电池龙头"},
            {"role": "user", "content": "它的估值呢"},
        ]
    )

    assert "用户：宁德时代怎么样" in prompt
    assert "助手：宁德时代是动力电池龙头" in prompt
    assert prompt.endswith("当前问题：它的估值呢")
