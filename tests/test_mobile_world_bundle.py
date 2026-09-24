from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "app" / "static"
MOBILE = ROOT / "jiheng_ai_flutter" / "assets" / "world"


def test_flutter_world_bundle_matches_web_game():
    html = (WEB / "procurement-journey.html").read_bytes()
    assert (MOBILE / "index.html").read_bytes() == html

    names = set(re.findall(rb"assets/([a-z0-9-]+\.png)", html))
    assert names
    for encoded_name in names:
        name = encoded_name.decode("ascii")
        assert (MOBILE / "assets" / name).read_bytes() == (WEB / "assets" / name).read_bytes()
