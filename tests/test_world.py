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
    assert all(len(node["scene"]["lesson"]["points"]) == 3 for node in scenario["nodes"])
    assert scenario["risk_challenge"]["options"]


def test_other_demo_companies_get_a_clear_world_message():
    scenario = world_scenario("600519")
    assert scenario is not None
    assert scenario["available"] is False


def test_world_map_coordinates_are_renderable():
    """The client places every node straight from x/y, so they must be valid and distinct."""
    nodes = world_scenario("300750")["nodes"]
    positions = set()
    for node in nodes:
        for axis in ("x", "y"):
            assert isinstance(node[axis], (int, float))
            assert 0 < node[axis] < 100
        positions.add((node["x"], node["y"]))
    assert len(positions) == len(nodes)


def test_world_unlock_chain_reaches_every_node():
    """Route lines are derived from unlock_after, so the chain must be one connected tree."""
    nodes = world_scenario("300750")["nodes"]
    roots = [node["id"] for node in nodes if node["initially_unlocked"]]
    assert len(roots) == 1
    reached = set(roots)
    for _ in range(len(nodes)):
        for node in nodes:
            if node["id"] not in reached and set(node["unlock_after"]) <= reached:
                reached.add(node["id"])
    assert reached == {node["id"] for node in nodes}
