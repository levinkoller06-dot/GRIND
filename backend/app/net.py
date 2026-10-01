"""Abrufen fremder Links (Rezepte, Kalender) – nur echte Webseiten, nichts im eigenen Netz."""

import ipaddress
import socket
from urllib.parse import urlsplit

import httpx


def public_url(url: str) -> str:
    """Erlaubt nur http/https-Adressen im Internet (kein localhost, 192.168…, file:)."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("Bitte einen normalen Link (http/https) angeben")
    try:
        infos = socket.getaddrinfo(parts.hostname, None)
    except socket.gaierror as e:
        raise ValueError(f"{parts.hostname} nicht gefunden") from e
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError("Dieser Link ist nicht erlaubt")
    return url.strip()


async def fetch(url: str, timeout: float = 10) -> httpx.Response:
    """GET mit selbst verfolgten Weiterleitungen, damit auch jedes Ziel geprüft wird."""
    url = public_url(url)
    async with httpx.AsyncClient(
        timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (GRIND Privatprojekt)"}
    ) as http:
        for _ in range(4):
            res = await http.get(url)
            if not res.is_redirect:
                break
            url = public_url(str(res.next_request.url))
    res.raise_for_status()
    return res
