import itertools
import uuid
from dataclasses import dataclass


@dataclass
class FakeUser:
    id: str = "user-1"
    email: str = "levin@example.com"
    token: str = "t"


class FakeDb:
    """In-Memory-Ersatz für Db. Versteht nur `eq.`-Filter, andere werden ignoriert."""

    def __init__(self):
        self.user = FakeUser()
        self.tables: dict[str, list[dict]] = {}
        self._ids = itertools.count(1)

    def _match(self, row: dict, filters: dict) -> bool:
        for key, value in filters.items():
            if key in ("select", "order", "limit", "and"):
                continue
            op, _, expected = value.partition(".")
            if op == "eq" and str(row.get(key)) != expected:
                return False
            if op == "ilike" and str(row.get(key, "")).lower() != expected.lower():
                return False
        return True

    async def select(self, table: str, **params: str) -> list[dict]:
        rows = [r for r in self.tables.get(table, []) if self._match(r, params)]
        if table == "subjects" and "grades(" in params.get("select", ""):
            grades = self.tables.get("grades", [])
            rows = [r | {"grades": [g for g in grades if g["subject_id"] == r["id"]]} for r in rows]
        return [dict(r) for r in rows]

    async def insert(self, table: str, row: dict) -> dict:
        row = {"id": str(uuid.uuid4()), "status": "open", "weight": 1} | row
        if table not in ("pending_actions",):
            row.pop("status")
        self.tables.setdefault(table, []).append(row)
        return dict(row)

    async def update(self, table: str, values: dict, **filters: str) -> list[dict]:
        rows = [r for r in self.tables.get(table, []) if self._match(r, filters)]
        for r in rows:
            r.update(values)
        return rows

    async def delete(self, table: str, **filters: str) -> None:
        self.tables[table] = [r for r in self.tables.get(table, []) if not self._match(r, filters)]


class FakeLlm:
    """Gibt vorher festgelegte Antworten zurück und merkt sich die Anfragen."""

    def __init__(self, *responses: dict):
        self.responses = list(responses)
        self.requests: list[list[dict]] = []

    async def generate(self, system, contents, tools):
        self.requests.append(list(contents))
        return self.responses.pop(0)


def calls(*items: tuple[str, dict]) -> dict:
    return {"role": "model", "parts": [{"functionCall": {"name": n, "args": a}} for n, a in items]}


def text(t: str) -> dict:
    return {"role": "model", "parts": [{"text": t}]}
