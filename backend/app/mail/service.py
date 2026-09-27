"""Gemeinsames Postfach über alle Mail-Konten eines Nutzers."""

import asyncio

from app.db import Db
from app.mail import classify, imap
from app.mail.crypto import decrypt, encrypt

# Zwischenspeicher pro Konto: (Konto, Tage, Limit, nur ungelesen) → (Fingerabdruck, Mails)
_cache: dict[tuple, tuple[str, list[dict]]] = {}

PUBLIC_FIELDS = "id,provider,email,label,color,imap_host,imap_port,smtp_host,smtp_port,created_at"


def _to_imap(row: dict) -> imap.ImapAccount:
    return imap.ImapAccount(
        id=row["id"],
        email=row["email"],
        password=decrypt(row["secret_enc"]),
        imap_host=row["imap_host"],
        imap_port=row["imap_port"],
        smtp_host=row["smtp_host"],
        smtp_port=row["smtp_port"],
        label=row.get("label"),
    )


async def list_accounts(db: Db) -> list[dict]:
    return await db.select("mail_accounts", select=PUBLIC_FIELDS, order="created_at")


async def _accounts(db: Db, konto: str | None = None) -> list[imap.ImapAccount]:
    rows = await db.select("mail_accounts", order="created_at")
    rows = [r for r in rows if r["provider"] == "imap"]
    if konto:
        wanted = konto.strip().lower()
        rows = [
            r
            for r in rows
            if wanted in r["email"].lower() or wanted == (r.get("label") or "").lower()
        ]
    return [_to_imap(r) for r in rows]


async def add_account(db: Db, data: dict) -> dict:
    """Prüft die Anmeldung und speichert das Konto (Passwort verschlüsselt)."""
    preset = imap.PRESETS.get(data.get("preset") or "", {})
    settings = {
        k: data.get(k) or preset.get(k)
        for k in ("imap_host", "imap_port", "smtp_host", "smtp_port")
    }
    if not all(settings.values()):
        raise imap.MailError("Server-Angaben fehlen (IMAP/SMTP)")
    password = data["password"]
    if data.get("preset") == "gmail" or "gmail" in (settings["imap_host"] or ""):
        # Google zeigt App-Passwörter mit Leerzeichen an ("abcd efgh ijkl mnop")
        password = "".join(password.split())
    account = imap.ImapAccount(
        id="neu",
        email=data["email"].strip(),
        password=password,
        label=data.get("label"),
        **settings,
    )
    await asyncio.to_thread(imap.test_login, account)
    row = await db.insert(
        "mail_accounts",
        {
            "user_id": db.user.id,
            "provider": "imap",
            "email": account.email,
            "label": data.get("label") or None,
            "color": data.get("color") or None,
            **settings,
            "secret_enc": encrypt(password),
        },
    )
    return {k: row[k] for k in PUBLIC_FIELDS.split(",")}


async def inbox(
    db: Db,
    days: int = 7,
    limit: int = 30,
    unseen_only: bool = False,
    search: str | None = None,
    konto: str | None = None,
) -> dict:
    """Mails aller Konten, neueste zuerst. Fehler einzelner Konten werden mitgeliefert.

    Pro Konto wird nur neu geladen, wenn sich der Posteingang seit dem letzten Abruf
    geändert hat (neue, gelöschte oder gelesene Mails).
    """
    accounts = await _accounts(db, konto)

    async def load(a: imap.ImapAccount) -> list[dict]:
        key = (a.id, days, limit, unseen_only)
        cached = _cache.get(key)
        fp, mails = await asyncio.to_thread(
            imap.list_messages, a, days, limit, unseen_only, cached[0] if cached else None
        )
        if mails is None and cached:
            return cached[1]
        _cache[key] = (fp, mails or [])
        return mails or []

    results = await asyncio.gather(*(load(a) for a in accounts), return_exceptions=True)
    mails, errors = [], []
    for account, result in zip(accounts, results, strict=True):
        if isinstance(result, Exception):
            errors.append({"konto": account.email, "fehler": str(result)})
        else:
            mails.extend(result)
    if search:
        needle = search.lower()
        mails = [
            m
            for m in mails
            if needle
            in f"{m['betreff']} {m['von']['name']} {m['von']['email']} {m['vorschau']}".lower()
        ]
    mails.sort(key=lambda m: m["datum"] or "", reverse=True)
    await classify.annotate(mails)
    return {"mails": mails, "fehler": errors, "konten": [a.email for a in accounts]}


def _split_id(mail_id: str) -> tuple[str, str]:
    account_id, _, uid = mail_id.rpartition(":")
    if not account_id or not uid:
        raise imap.MailError("Ungültige Mail-ID")
    return account_id, uid


async def _account_by_id(db: Db, account_id: str) -> imap.ImapAccount:
    rows = await db.select("mail_accounts", id=f"eq.{account_id}")
    if not rows:
        raise imap.MailError("Mail-Konto nicht gefunden")
    return _to_imap(rows[0])


async def read(db: Db, mail_id: str) -> dict:
    account_id, uid = _split_id(mail_id)
    return await asyncio.to_thread(imap.get_message, await _account_by_id(db, account_id), uid)


async def trash(db: Db, mail_ids: list[str]) -> dict:
    """Verschiebt Mails (auch aus mehreren Konten) in den jeweiligen Papierkorb."""
    by_account: dict[str, list[str]] = {}
    for mail_id in mail_ids:
        account_id, uid = _split_id(mail_id)
        by_account.setdefault(account_id, []).append(uid)
    moved = 0
    for account_id, uids in by_account.items():
        account = await _account_by_id(db, account_id)
        moved += await asyncio.to_thread(imap.move_to_trash, account, uids)
    return {"in_papierkorb": moved}


async def send(db: Db, payload: dict) -> dict:
    account = await _account_by_id(db, payload["konto_id"])
    return await asyncio.to_thread(
        imap.send_message,
        account,
        payload["an"],
        payload["betreff"],
        payload["text"],
        payload.get("in_reply_to"),
        payload.get("references"),
    )
