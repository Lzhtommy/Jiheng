from app.agent.profiles import build_profile


def test_quick_profile_has_bounded_tool_rounds():
    profile = build_profile("quick")

    assert profile.max_tool_rounds == 3
    assert "get_realtime_quote" in profile.tool_names
    assert "call_financial_mcp" in profile.tool_names
    assert "get_corporate_calendar" in profile.tool_names


def test_expert_profile_uses_deep_strategy():
    profile = build_profile("expert", {"name": "财报分析师", "systemPrompt": "关注财报质量"})

    assert profile.max_tool_rounds == 4
    assert profile.reasoning_effort == "high"
    assert "财报分析师" in profile.system_prompt


def test_deep_profile_keeps_longest_tool_budget():
    assert build_profile("deep").max_tool_rounds == 6


def test_expert_profile_falls_back_to_description():
    profile = build_profile("expert", {"name": "财报分析师", "description": "专注财报解读"})

    assert "专注财报解读" in profile.system_prompt


def test_expert_profile_loads_sop_by_expert_id():
    profile = build_profile(
        "expert", {"name": "个股分析师", "expertId": "expert_stock_research", "description": "专注个股"}
    )

    assert "快速分析 SOP" in profile.system_prompt
    assert "专注个股" not in profile.system_prompt


def test_financial_report_sop_loaded_by_expert_id():
    profile = build_profile(
        "expert",
        {"name": "财报分析师", "expertId": "expert_research_report", "description": "旧描述"},
    )

    assert "财报分析师" in profile.system_prompt
    assert "定期报告" in profile.system_prompt
    assert "旧描述" not in profile.system_prompt
    assert "没有券商研报" in profile.system_prompt
