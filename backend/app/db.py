import httpx

from app.auth import CurrentUser
from app.config import Settings


def user_client(user: CurrentUser, settings: Settings) -> httpx.AsyncClient:
    """HTTP-Client für die Supabase-REST-API im Namen des Nutzers.

    Weil das Token des Nutzers mitgeschickt wird, greift Row Level Security:
    Das Backend sieht nur, was der Nutzer selbst sehen darf.
    """
    return httpx.AsyncClient(
        base_url=f"{settings.supabase_url.rstrip('/')}/rest/v1",
        headers={
            "apikey": settings.supabase_publishable_key,
            "Authorization": f"Bearer {user.token}",
        },
        timeout=10,
    )
