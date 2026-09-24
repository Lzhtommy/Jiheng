from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..config import Settings, load_settings
from ..taxonomy.sw import Taxonomy, load_taxonomy


class RoleKind(str, Enum):
    CHIEF = "chief"
    SUPERVISOR = "supervisor"
    RESEARCHER = "researcher"


@dataclass(frozen=True)
class AgentRole:
    kind: RoleKind
    code: str
    name: str
    spec_id: str
    parent_code: str = ""
    parent_name: str = ""
    active: bool = False
    playbook_file: str = ""
    child_codes: tuple[str, ...] = ()


@dataclass
class OrgChart:
    chief: AgentRole
    supervisors: dict[str, AgentRole] = field(default_factory=dict)
    researchers: dict[str, AgentRole] = field(default_factory=dict)

    def supervisor(self, l2_code: str) -> Optional[AgentRole]:
        return self.supervisors.get(l2_code)

    def researcher(self, l3_code: str) -> Optional[AgentRole]:
        return self.researchers.get(l3_code)


def build_org(settings: Optional[Settings] = None, taxonomy: Optional[Taxonomy] = None) -> OrgChart:
    settings = settings or load_settings()
    tax = taxonomy or load_taxonomy()
    books = settings.playbooks
    chief = AgentRole(
        kind=RoleKind.CHIEF,
        code=settings.l1_code,
        name=settings.l1_name,
        spec_id=f"sw1_{settings.l1_code}",
        active=True,
        playbook_file=str(books.get("chief") or "chief_electronics.md"),
        child_codes=tuple(sorted(tax.l2)),
    )
    supervisors: dict[str, AgentRole] = {}
    researchers: dict[str, AgentRole] = {}
    sup_files = books.get("supervisors") or {}
    res_files = books.get("researchers") or {}
    inactive = str(books.get("inactive") or "inactive.md")
    for l2 in tax.children_l2(settings.l1_code):
        l3_nodes = tax.children_l3(l2.code)
        active = l2.code in settings.active_l2
        supervisors[l2.code] = AgentRole(
            kind=RoleKind.SUPERVISOR,
            code=l2.code,
            name=l2.name,
            spec_id=l2.spec_id,
            parent_code=settings.l1_code,
            parent_name=settings.l1_name,
            active=active,
            playbook_file=str(sup_files.get(l2.code) or inactive),
            child_codes=tuple(n.code for n in l3_nodes),
        )
        for l3 in l3_nodes:
            researchers[l3.code] = AgentRole(
                kind=RoleKind.RESEARCHER,
                code=l3.code,
                name=l3.name,
                spec_id=l3.spec_id,
                parent_code=l2.code,
                parent_name=l2.name,
                active=l3.code in settings.active_l3,
                playbook_file=str(res_files.get(l3.code) or inactive),
            )
    return OrgChart(chief=chief, supervisors=supervisors, researchers=researchers)
