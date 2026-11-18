import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Site(Record):
    site_id: str
    name: str


class Equipment(Record):
    equipment_id: str
    site_id: str
    category: str
    status: str


class ProductionShift(Record):
    site_id: str
    date: str
    shift: Literal["day", "night"]
    tonnes: int = Field(ge=0)


class WorkOrder(Record):
    order_id: str
    equipment_id: str
    priority: str
    status: str


class Stock(Record):
    site_id: str
    item_id: str
    quantity: int = Field(ge=0)
    unit: str


class MiningSeed(Record):
    demo_id: Literal["48254cc6"]
    synthetic: Literal[True]
    version: str
    sites: list[Site]
    equipment: list[Equipment]
    production: list[ProductionShift]
    work_orders: list[WorkOrder]
    stock: list[Stock]

    @model_validator(mode="after")
    def validate_relations(self) -> "MiningSeed":
        sites = {site.site_id for site in self.sites}
        equipment = {item.equipment_id for item in self.equipment}
        if len(sites) != len(self.sites) or len(equipment) != len(self.equipment):
            raise ValueError("Duplicate demo entity identifiers.")
        if any(item.site_id not in sites for item in self.equipment + self.production + self.stock):
            raise ValueError("Demo record references an unknown site.")
        if any(item.equipment_id not in equipment for item in self.work_orders):
            raise ValueError("Demo work order references unknown equipment.")
        return self

    @classmethod
    def load(cls) -> "MiningSeed":
        path = Path.cwd() / "data" / "seed" / "mining.json"
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))


def result(data: object, source_id: str) -> dict[str, object]:
    return {
        "demo_id": "48254cc6",
        "synthetic": True,
        "data": data,
        "sources": [{"kind": "demo_fixture", "id": f"urn:kppdemo:{source_id}"}],
    }
