from app.mail import service
from app.mail.imap import MailError
from app.tools.base import ToolContext, obj, propose, tool


@tool(
    "mails_abfragen",
    "Durchsucht das gemeinsame Postfach (alle Mail-Konten des Nutzers). Liefert Absender, "
    "Betreff, Datum, Vorschau, ID, kategorie (werbung/persoenlich/schule/rechnung/sicherheit/"
    "sonstiges) und antwort_noetig. "
    "Für Aufräumen/Löschen vieler Mails kompakt=true setzen (mehr Mails, ohne Vorschau).",
    obj(
        {
            "tage": {"type": "integer", "description": "Wie viele Tage zurück, Standard 7"},
            "kompakt": {"type": "boolean", "description": "Bis zu 150 Mails ohne Vorschau"},
            "suche": {
                "type": "string",
                "description": "Wort im Absender/Betreff/Text, z. B. 'Tim'",
            },
            "nur_ungelesen": {"type": "boolean"},
            "konto": {
                "type": "string",
                "description": "Nur ein Konto, z. B. 'gmail' oder 'Schule'",
            },
            "kategorie": {
                "type": "string",
                "enum": ["werbung", "persoenlich", "schule", "rechnung", "sicherheit", "sonstiges"],
                "description": "Nur Mails dieser Kategorie",
            },
        }
    ),
)
async def mails_abfragen(ctx: ToolContext, args: dict) -> dict:
    compact = bool(args.get("kompakt"))
    result = await service.inbox(
        ctx.db,
        days=min(int(args.get("tage") or 7), 60),
        limit=150 if compact else 40,
        unseen_only=bool(args.get("nur_ungelesen")),
        search=args.get("suche"),
        konto=args.get("konto"),
    )
    if not result["konten"]:
        return {"hinweis": "Noch kein Mail-Konto verbunden (Einstellungen → Mail-Konten)."}
    if args.get("kategorie"):
        result["mails"] = [m for m in result["mails"] if m.get("kategorie") == args["kategorie"]]
    if compact:
        result["mails"] = [
            {
                "id": m["id"],
                "von": f"{m['von']['name']} <{m['von']['email']}>",
                "betreff": m["betreff"],
                "kategorie": m.get("kategorie"),
            }
            for m in result["mails"][:150]
        ]
    else:
        result["mails"] = result["mails"][:25]
    return result


@tool(
    "mails_loeschen",
    "Verschiebt Mails in den Papierkorb (z. B. Werbung, Spam, alle von einem Absender). "
    "IDs vorher mit mails_abfragen (kompakt) holen und unverändert übernehmen.",
    obj(
        {
            "ids": {"type": "array", "items": {"type": "string"}},
            "grund": {
                "type": "string",
                "description": "Kurz, z. B. 'Werbung' oder 'alle von Google'",
            },
            "ausser_absender": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Absender, die nie gelöscht werden sollen (z. B. ['Digitec', 'Twint'])",
            },
        },
        ["ids"],
    ),
)
async def mails_loeschen(ctx: ToolContext, args: dict) -> dict:
    # Absender/Betreff aus dem Zwischenspeicher – unbekannte (z. B. verstümmelte) IDs fallen weg
    known = {m["id"]: m for _, mails in service._cache.values() for m in mails}
    keep = [k.strip().lower() for k in args.get("ausser_absender") or [] if k.strip()]

    def excluded(m: dict) -> bool:
        sender = f"{m['von']['name']} {m['von']['email']}".lower()
        return any(k in sender for k in keep)

    wanted = list(dict.fromkeys(args["ids"]))
    ids = [i for i in wanted if i in known and not excluded(known[i])]
    if not ids:
        raise ValueError("Keine gültigen Mail-IDs – erst mails_abfragen (kompakt) aufrufen")
    preview = [{"von": known[i]["von"]["name"], "betreff": known[i]["betreff"]} for i in ids]
    payload = {"ids": ids, "anzahl": len(ids), "grund": args.get("grund"), "vorschau": preview}
    result = await propose(
        ctx, "mail.delete", payload, f"{len(ids)} Mail(s) in den Papierkorb verschieben."
    )
    if skipped := len(wanted) - len(ids):
        result["uebersprungen"] = f"{skipped} Mail(s) nicht gelöscht (Ausnahme oder unbekannte ID)"
    return result


@tool(
    "mail_lesen",
    "Liest den kompletten Text einer Mail (ID aus mails_abfragen).",
    obj({"id": {"type": "string"}}, ["id"]),
)
async def mail_lesen(ctx: ToolContext, args: dict) -> dict:
    mail = await service.read(ctx.db, args["id"])
    mail.pop("references", None)
    return mail


@tool(
    "mail_senden",
    "Schreibt und sendet eine Mail oder Antwort (je nach Einstellung erst nach Bestätigung). "
    "Für Antworten antwort_auf_id angeben (Betreff/Empfänger kommen dann "
    "von der Original-Mail).",
    obj(
        {
            "text": {"type": "string", "description": "Der fertige Mailtext mit Anrede und Gruss"},
            "antwort_auf_id": {
                "type": "string",
                "description": "ID der Mail, auf die geantwortet wird",
            },
            "an": {"type": "string", "description": "Empfänger (nur bei neuen Mails nötig)"},
            "betreff": {"type": "string", "description": "Nur bei neuen Mails nötig"},
            "konto": {
                "type": "string",
                "description": "Absender-Konto bei neuen Mails (E-Mail/Label)",
            },
        },
        ["text"],
    ),
)
async def mail_senden(ctx: ToolContext, args: dict) -> dict:
    if args.get("antwort_auf_id"):
        original = await service.read(ctx.db, args["antwort_auf_id"])
        account_id = args["antwort_auf_id"].rpartition(":")[0]
        subject = original["betreff"]
        payload = {
            "konto_id": account_id,
            "von": original["konto"],
            "an": original["antwort_an"],
            "betreff": subject if subject.lower().startswith(("re:", "aw:")) else f"Re: {subject}",
            "text": args["text"],
            "in_reply_to": original["message_id"] or None,
            "references": original["references"] or None,
        }
    else:
        if not args.get("an") or not args.get("betreff"):
            raise ValueError("Für eine neue Mail braucht es Empfänger (an) und Betreff")
        accounts = await service.list_accounts(ctx.db)
        wanted = (args.get("konto") or "").lower()
        account = next(
            (
                a
                for a in accounts
                if wanted
                and (wanted in a["email"].lower() or wanted == (a.get("label") or "").lower())
            ),
            accounts[0] if accounts else None,
        )
        if account is None:
            raise MailError("Kein Mail-Konto verbunden")
        payload = {
            "konto_id": account["id"],
            "von": account["email"],
            "an": args["an"],
            "betreff": args["betreff"],
            "text": args["text"],
        }
    payload = {k: v for k, v in payload.items() if v}
    return await propose(
        ctx, "mail.send", payload, f"Mail an {payload['an']} („{payload['betreff']}“)."
    )
