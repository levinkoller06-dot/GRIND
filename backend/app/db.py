from typing import Any, Self

import httpx

from app.auth import CurrentUser
from app.config import Settings


class DbError(Exception):
    pass


def _client(settings: Settings, headers: dict[str, str]) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=f"{settings.supabase_url.rstrip('/')}/rest/v1", headers=headers, timeout=10
    )


def _secret_headers(key: str) -> dict[str, str]:
    # Neue Keys (sb_secret_...) gehören nur in "apikey", alte service_role-Keys sind JWTs
    if key.startswith("sb_"):
        return {"apikey": key}
    return {"apikey": key, "Authorization": f"Bearer {key}"}


class Db:
    """Schlanker Client für die Supabase-REST-API im Namen eines Nutzers.

    Weil das Token des Nutzers mitgeschickt wird, greift Row Level Security:
    Das Backend sieht und ändert nur, was der Nutzer selbst darf.
    """

    def __init__(self, user: CurrentUser, settings: Settings):
        self.user = user
        self._http = _client(
            settings,
            {"apikey": settings.supabase_publishable_key, "Authorization": f"Bearer {user.token}"},
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc) -> None:
        await self._http.aclose()

    @staticmethod
    def _check(res: httpx.Response) -> Any:
        if not res.is_success:
            raise DbError(f"{res.status_code}: {res.text}")
        return res.json() if res.content else None

    async def select(self, table: str, **params: str) -> list[dict]:
        params.setdefault("select", "*")
        return self._check(await self._http.get(f"/{table}", params=params))

    async def insert(self, table: str, row: dict) -> dict:
        res = await self._http.post(
            f"/{table}", json=row, headers={"Prefer": "return=representation"}
        )
        return self._check(res)[0]

    async def insert_many(self, table: str, rows: list[dict]) -> list[dict]:
        if not rows:
            return []
        res = await self._http.post(
            f"/{table}", json=rows, headers={"Prefer": "return=representation"}
        )
        return self._check(res)

    async def update(self, table: str, values: dict, **filters: str) -> list[dict]:
        res = await self._http.patch(
            f"/{table}", json=values, params=filters, headers={"Prefer": "return=representation"}
        )
        return self._check(res)

    async def delete(self, table: str, **filters: str) -> None:
        self._check(await self._http.delete(f"/{table}", params=filters))


class ServiceDb:
    """Zugriff mit dem Secret Key für Zeitplan-Jobs – ohne Row Level Security!

    Direkt nur für nutzerübergreifende Abfragen (z. B. alle Profile). Alles, was einen
    einzelnen Nutzer betrifft, läuft über `for_user()`.
    """

    def __init__(self, settings: Settings):
        self._http = _client(settings, _secret_headers(settings.supabase_secret_key))

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc) -> None:
        await self._http.aclose()

    async def select(self, table: str, **params: str) -> list[dict]:
        params.setdefault("select", "*")
        return Db._check(await self._http.get(f"/{table}", params=params))

    def for_user(self, user_id: str) -> "UserScopedDb":
        return UserScopedDb(user_id, self._http)


class UserScopedDb(Db):
    """Wie Db, aber mit dem Secret Key. Weil RLS hier nicht greift, beschränkt diese Klasse
    jede Abfrage selbst auf den Nutzer (user_id, bei profiles die id)."""

    def __init__(self, user_id: str, http: httpx.AsyncClient):
        self.user = CurrentUser(id=user_id, email=None, token="")
        self._http = http

    async def __aexit__(self, *exc) -> None:
        pass  # der Client gehört dem ServiceDb

    def _scope(self, table: str, params: dict) -> dict:
        column = "id" if table == "profiles" else "user_id"
        return params | {column: f"eq.{self.user.id}"}

    def _own(self, table: str, row: dict) -> dict:
        return row if table == "profiles" else row | {"user_id": self.user.id}

    async def select(self, table: str, **params: str) -> list[dict]:
        return await super().select(table, **self._scope(table, params))

    async def insert(self, table: str, row: dict) -> dict:
        return await super().insert(table, self._own(table, row))

    async def insert_many(self, table: str, rows: list[dict]) -> list[dict]:
        return await super().insert_many(table, [self._own(table, r) for r in rows])

    async def update(self, table: str, values: dict, **filters: str) -> list[dict]:
        return await super().update(table, values, **self._scope(table, filters))

    async def delete(self, table: str, **filters: str) -> None:
        await super().delete(table, **self._scope(table, filters))
