"""Gemeinsames Postfach über alle Mail-Konten eines Nutzers."""

import asyncio

from app.db import Db
from app.mail import imap
from app.mail.crypto import decrypt, encrypt

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
    account = imap.ImapAccount(
        id="neu",
        email=data["email"].strip(),
        password=data["password"],
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
            "secret_enc": encrypt(data["password"]),
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
    """Mails aller Konten, neueste zuerst. Fehler einzelner Konten werden mitgeliefert."""
    accounts = await _accounts(db, konto)
    results = await asyncio.gather(
        *(asyncio.to_thread(imap.list_messages, a, days, limit, unseen_only) for a in accounts),
        return_exceptions=True,
    )
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
