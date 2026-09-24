from pydantic import BaseModel, Field, field_validator, model_validator

REQUIRED_TOPIC_IDS = {"claim", "proof", "risk"}
ALLOWED_KINDS = {"battery", "auto", "fab", "equip", "tech"}


class GenerateCompanyRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=24)


class WorldScroll(BaseModel):
    id: str
    title: str
    body: str
    kind: str = "剧情单据"


class WorldTopic(BaseModel):
    id: str
    label: str
    prompt: str
    keys: list[str] = Field(..., min_length=1)
    reply: str
    repeat: str
    scroll: WorldScroll | None = None


class WorldScene(BaseModel):
    place: str
    region: str
    npc: str
    role: str
    atmosphere: str
    arrival: str
    opening: str
    generic: str
    topics: list[WorldTopic]
    offerPrompt: str
    early: str
    offerStrong: str
    offerWeak: str
    termsStrong: str
    termsWeak: str
    risk: str
    lead: str
    cross: dict[str, str] = Field(default_factory=dict)

    @field_validator("topics")
    @classmethod
    def _topics_cover_required_ids(cls, topics: list[WorldTopic]) -> list[WorldTopic]:
        ids = {topic.id for topic in topics}
        if ids != REQUIRED_TOPIC_IDS:
            raise ValueError(f"topics 的 id 必须恰好是 {sorted(REQUIRED_TOPIC_IDS)}，实际为 {sorted(ids)}")
        return topics


class WorldCompanyMeta(BaseModel):
    name: str
    code: str = ""
    tag: str
    kind: str

    @field_validator("kind")
    @classmethod
    def _kind_allowed(cls, kind: str) -> str:
        if kind not in ALLOWED_KINDS:
            raise ValueError(f"kind 必须是 {sorted(ALLOWED_KINDS)} 之一，实际为 {kind!r}")
        return kind


class GeneratedScenario(BaseModel):
    company: WorldCompanyMeta
    scenes: list[WorldScene] = Field(..., min_length=4, max_length=4)

    @model_validator(mode="after")
    def _sanitize_cross_refs(self) -> "GeneratedScenario":
        seen_scroll_ids: set[str] = set()
        for scene in self.scenes:
            scene.cross = {key: value for key, value in scene.cross.items() if key in seen_scroll_ids}
            for topic in scene.topics:
                if topic.scroll:
                    seen_scroll_ids.add(topic.scroll.id)
        return self
