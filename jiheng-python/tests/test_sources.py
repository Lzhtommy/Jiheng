from app.agent.sources import add_sources, requires_sources


def test_add_sources_filters_normalizes_and_deduplicates():
    refs: dict[str, dict] = {}

    add_sources(
        refs,
        [
            {"title": " 腾讯行情 ", "url": " u1 ", "retrieved_at": "2026-09-24T08:00:00Z"},
            {"title": "重复来源", "url": "u1"},
            {"title": "无地址"},
            "invalid",
        ],
    )

    assert list(refs) == ["u1"]
    assert refs["u1"] == {
        "title": "腾讯行情",
        "url": "u1",
        "retrieved_at": "2026-09-24T08:00:00Z",
        "tag": "数据",
        "date": "2026-09-24",
    }


def test_requires_sources_distinguishes_factual_and_conceptual_questions():
    assert requires_sources("贵州茅台最新股价是多少？")
    assert requires_sources("解释一下", "该公司营收同比增长 12.5%")
    assert not requires_sources("解释一下什么是市盈率")
