from app.mail import service
from app.mail.imap import MailError
from app.tools.base import ToolContext, obj, propose, tool


@tool(
    "mails_abfragen",
    "Durchsucht das gemeinsame Postfach (alle Mail-Konten des Nutzers). Liefert Absender, "
    "Betreff, Datum, Vorschau, ID und ob es ein Newsletter/Werbung ist (newsletter=true). "
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
    if compact:
        result["mails"] = [
            {
                "id": m["id"],
                "von": f"{m['von']['name']} <{m['von']['email']}>",
                "betreff": m["betreff"],
                "newsletter": m["newsletter"],
            }
            for m in result["mails"][:150]
        ]
    else:
        result["mails"] = result["mails"][:25]
    return result


@tool(
    "mails_loeschen",
    "Schlägt vor, Mails in den Papierkorb zu verschieben (z. B. Werbung, Spam, alle von einem "
    "Absender). Der Nutzer muss bestätigen. IDs vorher mit mails_abfragen (kompakt) holen.",
    obj(
        {
            "ids": {"type": "array", "items": {"type": "string"}},
            "grund": {
                "type": "string",
                "description": "Kurz, z. B. 'Werbung' oder 'alle von Google'",
            },
        },
        ["ids"],
    ),
)
async def mails_loeschen(ctx: ToolContext, args: dict) -> dict:
    ids = list(dict.fromkeys(args["ids"]))
    if not ids:
        raise ValueError("Keine Mails angegeben")
    # Absender/Betreff für die Bestätigungs-Karte aus dem Zwischenspeicher holen
    known = {m["id"]: m for _, mails in service._cache.values() for m in mails}
    preview = [
        {
            "von": known[i]["von"]["name"] if i in known else "?",
            "betreff": known[i]["betreff"] if i in known else i,
        }
        for i in ids
    ]
    payload = {"ids": ids, "anzahl": len(ids), "grund": args.get("grund"), "vorschau": preview}
    return await propose(
        ctx, "mail.delete", payload, f"{len(ids)} Mail(s) in den Papierkorb verschieben."
    )


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
    "Schreibt eine Mail oder Antwort. Sie wird NICHT sofort gesendet, sondern dem Nutzer zum "
    "Bestätigen vorgelegt. Für Antworten antwort_auf_id angeben (Betreff/Empfänger kommen dann "
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
