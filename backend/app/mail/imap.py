"""IMAP/SMTP-Zugriff (synchron, wird im Thread ausgeführt).

Funktioniert mit allen Anbietern, die IMAP + SMTP mit Passwort erlauben
(z. B. hispeed/Sunrise, Gmail mit App-Passwort, GMX).
"""

import imaplib
import re
import smtplib
import ssl
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email import message_from_bytes, policy
from email.message import EmailMessage, Message
from email.utils import formataddr, make_msgid, parseaddr, parsedate_to_datetime
from html import unescape

PRESETS = {
    "hispeed": {
        "imap_host": "imap.hispeed.ch",
        "imap_port": 993,
        "smtp_host": "smtp.hispeed.ch",
        "smtp_port": 587,
    },
    "gmail": {
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
    },
    "gmx": {
        "imap_host": "imap.gmx.net",
        "imap_port": 993,
        "smtp_host": "mail.gmx.net",
        "smtp_port": 587,
    },
}

TIMEOUT = 20


@dataclass
class ImapAccount:
    id: str
    email: str
    password: str
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    label: str | None = None


class MailError(Exception):
    pass


def _connect(acc: ImapAccount) -> imaplib.IMAP4_SSL:
    try:
        conn = imaplib.IMAP4_SSL(
            acc.imap_host, acc.imap_port, timeout=TIMEOUT, ssl_context=ssl.create_default_context()
        )
        conn.login(acc.email, acc.password)
        return conn
    except imaplib.IMAP4.error as e:
        raise MailError(f"Anmeldung bei {acc.imap_host} fehlgeschlagen: {e}") from e
    except OSError as e:
        raise MailError(f"{acc.imap_host} nicht erreichbar: {e}") from e


def test_login(acc: ImapAccount) -> None:
    conn = _connect(acc)
    conn.logout()
    with _smtp(acc):
        pass


def _smtp(acc: ImapAccount) -> smtplib.SMTP:
    try:
        if acc.smtp_port == 465:
            server = smtplib.SMTP_SSL(acc.smtp_host, 465, timeout=TIMEOUT)
        else:
            server = smtplib.SMTP(acc.smtp_host, acc.smtp_port, timeout=TIMEOUT)
            server.starttls(context=ssl.create_default_context())
        server.login(acc.email, acc.password)
        return server
    except smtplib.SMTPAuthenticationError as e:
        raise MailError(f"SMTP-Anmeldung bei {acc.smtp_host} fehlgeschlagen") from e
    except (smtplib.SMTPException, OSError) as e:
        raise MailError(f"SMTP-Server {acc.smtp_host}: {e}") from e


def _header(msg: Message, name: str) -> str:
    return str(msg.get(name, "") or "").strip()


def _address(value: str) -> dict:
    name, addr = parseaddr(value)
    return {"name": name or addr, "email": addr}


def _date(msg: Message) -> str | None:
    try:
        return parsedate_to_datetime(_header(msg, "Date")).astimezone(UTC).isoformat()
    except (TypeError, ValueError):
        return None


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|head).*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</li>|</h\d>", "\n", html)
    text = unescape(re.sub(r"<[^>]+>", "", html))
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t\xa0]+", " ", text)).strip()


def body_text(msg: Message) -> str:
    """Textinhalt einer Mail (text/plain bevorzugt, sonst HTML ohne Tags)."""
    plain, html = None, None
    for part in msg.walk() if msg.is_multipart() else [msg]:
        if part.get_content_maintype() == "multipart" or part.get_filename():
            continue
        try:
            content = part.get_content()
        except (LookupError, KeyError, ValueError):
            payload = part.get_payload(decode=True) or b""
            content = payload.decode("utf-8", errors="replace")
        if part.get_content_type() == "text/plain" and plain is None:
            plain = content
        elif part.get_content_type() == "text/html" and html is None:
            html = content
    if plain and plain.strip():
        return plain.strip()
    return html_to_text(html) if html else ""


def _summary(
    acc: ImapAccount, uid: str, flags: bytes, raw: bytes, with_preview: bool = True
) -> dict:
    msg = message_from_bytes(raw, policy=policy.default)
    text = body_text(msg) if with_preview else ""
    return {
        "id": f"{acc.id}:{uid}",
        "konto": acc.email,
        "konto_label": acc.label,
        "von": _address(_header(msg, "From")),
        "an": _header(msg, "To"),
        "betreff": _header(msg, "Subject") or "(kein Betreff)",
        "datum": _date(msg),
        "gelesen": b"\\Seen" in flags,
        "vorschau": " ".join(text.split())[:200],
    }


PREVIEW_MAX_BYTES = 150_000


def _fetch(conn: imaplib.IMAP4_SSL, uids: list[bytes], what: str) -> dict[str, tuple[bytes, bytes]]:
    """UID → (Metadaten, Inhalt)"""
    typ, data = conn.uid("FETCH", b",".join(uids).decode(), what)
    if typ != "OK":
        raise MailError(f"Abruf fehlgeschlagen: {data}")
    out = {}
    for item in data:
        if isinstance(item, tuple):
            uid = re.search(rb"UID (\d+)", item[0])
            if uid:
                out[uid.group(1).decode()] = (item[0], item[1])
    return out


def list_messages(
    acc: ImapAccount, days: int = 7, limit: int = 30, unseen_only: bool = False
) -> list[dict]:
    """Neueste Mails aus dem Posteingang (ohne sie als gelesen zu markieren)."""
    conn = _connect(acc)
    try:
        conn.select("INBOX", readonly=True)
        since = (datetime.now(UTC) - timedelta(days=days)).strftime("%d-%b-%Y")
        criteria = ["SINCE", since] + (["UNSEEN"] if unseen_only else [])
        typ, data = conn.uid("SEARCH", *criteria)
        if typ != "OK":
            raise MailError(f"Suche fehlgeschlagen: {data}")
        uids = data[0].split()[-limit:]
        if not uids:
            return []
        heads = _fetch(conn, uids, "(FLAGS RFC822.SIZE BODY.PEEK[HEADER])")

        def size(meta: bytes) -> int:
            m = re.search(rb"RFC822.SIZE (\d+)", meta)
            return int(m.group(1)) if m else 0

        # Kleine Mails ganz laden (für die Vorschau), große mit Anhängen erst beim Öffnen
        small = [u.encode() for u, (meta, _) in heads.items() if size(meta) <= PREVIEW_MAX_BYTES]
        full = _fetch(conn, small, "(BODY.PEEK[])") if small else {}
        result = []
        for uid, (meta, header) in heads.items():
            flags = re.search(rb"FLAGS \(([^)]*)\)", meta)
            raw = full[uid][1] if uid in full else header
            result.append(_summary(acc, uid, flags.group(1) if flags else b"", raw, uid in full))
        return result
    finally:
        conn.logout()


def get_message(acc: ImapAccount, uid: str) -> dict:
    conn = _connect(acc)
    try:
        conn.select("INBOX", readonly=True)
        typ, data = conn.uid("FETCH", uid, "(FLAGS BODY.PEEK[])")
        item = next((d for d in data if isinstance(d, tuple)), None)
        if typ != "OK" or item is None:
            raise MailError("Mail nicht gefunden")
        msg = message_from_bytes(item[1], policy=policy.default)
        flags = re.search(rb"FLAGS \(([^)]*)\)", item[0])
        summary = _summary(acc, uid, flags.group(1) if flags else b"", item[1])
        return summary | {
            "text": body_text(msg)[:20000],
            "message_id": _header(msg, "Message-ID"),
            "references": _header(msg, "References"),
            "antwort_an": _header(msg, "Reply-To") or _header(msg, "From"),
        }
    finally:
        conn.logout()


def _sent_folder(conn: imaplib.IMAP4_SSL) -> str | None:
    typ, folders = conn.list()
    if typ != "OK":
        return None
    for line in folders:
        text = line.decode(errors="replace") if isinstance(line, bytes) else str(line)
        if "\\Sent" in text:
            return text.rsplit(' "/" ', 1)[-1].rsplit(' "." ', 1)[-1].strip()
    return None


def send_message(
    acc: ImapAccount,
    to: str,
    subject: str,
    text: str,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> dict:
    msg = EmailMessage()
    msg["From"] = formataddr((acc.label or "", acc.email)) if acc.label else acc.email
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=acc.email.split("@")[-1])
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = f"{references} {in_reply_to}".strip() if references else in_reply_to
    msg.set_content(text)

    with _smtp(acc) as server:
        server.send_message(msg)

    # Kopie in "Gesendet" ablegen (Gmail macht das selbst)
    if "gmail.com" not in acc.imap_host:
        try:
            conn = _connect(acc)
            folder = _sent_folder(conn)
            if folder:
                conn.append(
                    folder, "\\Seen", imaplib.Time2Internaldate(time.time()), msg.as_bytes()
                )
            conn.logout()
        except (MailError, imaplib.IMAP4.error, OSError):
            pass
    return {"gesendet": True, "an": to, "betreff": subject}
