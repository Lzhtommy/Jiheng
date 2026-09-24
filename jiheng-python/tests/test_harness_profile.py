from pathlib import Path

from app.agent.runtime import AgentRunContext


def test_harness_profile_only_registers_mcp_tools():
    profile = Path("harness/jiheng.cordis.patch.yml").read_text(encoding="utf-8")

    assert "@deepseek-ai/dsh-mcp-client" in profile
    assert "@deepseek-ai/dsh-tool-bash-persistent" not in profile
    assert "@deepseek-ai/dsh-tool-pwsh-persistent" not in profile
    assert "@deepseek-ai/dsh-subprocess-local" not in profile
    assert "@deepseek-ai/dsh-fs-local" not in profile
    assert "@deepseek-ai/dsh-jobs-local" not in profile
    assert "transport: stdio" in profile
    assert "python\n" in profile


def test_agent_run_context_isolates_user_and_conversation_paths(tmp_path):
    context = AgentRunContext(user_id="user/a", conversation_id="conv:b")
    root = context.root(str(tmp_path))

    assert root == tmp_path.resolve() / "usera" / "convb"
    assert context.session_key() == "usera-convb"
