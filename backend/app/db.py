from typing import Any, Self

import httpx

from app.auth import CurrentUser
from app.config import Settings


class DbError(Exception):
    pass


class Db:
    """Schlanker Client für die Supabase-REST-API im Namen eines Nutzers.

    Weil das Token des Nutzers mitgeschickt wird, greift Row Level Security:
    Das Backend sieht und ändert nur, was der Nutzer selbst darf.
    """

    def __init__(self, user: CurrentUser, settings: Settings):
        self.user = user
        self._http = httpx.AsyncClient(
            base_url=f"{settings.supabase_url.rstrip('/')}/rest/v1",
            headers={
                "apikey": settings.supabase_publishable_key,
                "Authorization": f"Bearer {user.token}",
            },
            timeout=10,
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

    async def update(self, table: str, values: dict, **filters: str) -> list[dict]:
        res = await self._http.patch(
            f"/{table}", json=values, params=filters, headers={"Prefer": "return=representation"}
        )
        return self._check(res)

    async def delete(self, table: str, **filters: str) -> None:
        self._check(await self._http.delete(f"/{table}", params=filters))
