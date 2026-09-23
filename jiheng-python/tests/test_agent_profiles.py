from app.agent.profiles import build_profile


def test_quick_profile_has_bounded_tool_rounds():
    profile = build_profile("quick")

    assert profile.max_tool_rounds == 2
    assert "get_realtime_quote" in profile.tool_names


def test_expert_profile_uses_deep_strategy():
    profile = build_profile("expert", {"name": "研报专家", "systemPrompt": "关注机构观点"})

    assert profile.max_tool_rounds == 6
    assert "研报专家" in profile.system_prompt


def test_expert_profile_falls_back_to_description():
    profile = build_profile("expert", {"name": "研报专家", "description": "专注研报撰写"})

    assert "专注研报撰写" in profile.system_prompt
