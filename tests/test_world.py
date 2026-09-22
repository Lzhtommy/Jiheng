from app.world import world_scenario


def test_catl_world_has_a_playable_mission():
    scenario = world_scenario("300750")
    assert scenario is not None
    assert scenario["available"] is True
    assert len(scenario["nodes"]) == 5
    assert scenario["mission"]["goal"] == 4
    assert [chapter["title"] for chapter in scenario["chapters"]] == ["盐湖矿区", "材料工坊", "电芯城", "车企港 · 储能灯塔"]
    assert scenario["chapters"][-1]["node_ids"] == ["automaker", "storage"]
    assert all("scene" in node for node in scenario["nodes"])
    assert all(len(node["scene"]["objects"]) == 3 for node in scenario["nodes"])
    assert scenario["risk_challenge"]["options"]


def test_other_demo_companies_get_a_clear_world_message():
    scenario = world_scenario("600519")
    assert scenario is not None
    assert scenario["available"] is False
