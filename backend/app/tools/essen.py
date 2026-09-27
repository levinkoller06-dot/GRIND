from datetime import date, datetime, time, timedelta

import httpx

from app.tools.base import ToolContext, obj, tool

MEAL_TYPES = ["fruehstueck", "mittag", "abend", "snack"]

ITEM = obj(
    {
        "name": {"type": "string"},
        "menge": {"type": "string", "description": "z. B. '200 g', '1 Portion', '2 Scheiben'"},
        "kcal": {"type": "number"},
        "protein_g": {"type": "number"},
        "kh_g": {"type": "number", "description": "Kohlenhydrate in g"},
        "fett_g": {"type": "number"},
    },
    ["name", "kcal", "protein_g"],
)


def guess_meal_type(hour: int) -> str:
    if 5 <= hour < 11:
        return "fruehstueck"
    if 11 <= hour < 15:
        return "mittag"
    if 17 <= hour < 22:
        return "abend"
    return "snack"


def totals(items: list[dict]) -> dict:
    keys = {"kcal": "kcal", "protein_g": "protein_g", "carbs_g": "kh_g", "fat_g": "fett_g"}
    return {out: round(sum(float(i.get(k) or 0) for i in items), 1) for k, out in keys.items()}


@tool(
    "mahlzeit_eintragen",
    "Trägt eine Mahlzeit mit geschätzten Nährwerten ein. Schätze Kalorien und Makros pro "
    "Lebensmittel realistisch (übliche Portionsgrößen), auch bei Fotos.",
    obj(
        {
            "lebensmittel": {"type": "array", "items": ITEM},
            "mahlzeit": {"type": "string", "enum": MEAL_TYPES},
            "beschreibung": {"type": "string", "description": "Kurz, z. B. 'Nudeln mit Hähnchen'"},
            "datum": {"type": "string", "description": "YYYY-MM-DD, Standard: heute"},
            "uhrzeit": {"type": "string", "description": "HH:MM, Standard: jetzt"},
            "vom_foto": {"type": "boolean", "description": "true, wenn aus einem Foto geschätzt"},
        },
        ["lebensmittel"],
    ),
)
async def mahlzeit_eintragen(ctx: ToolContext, args: dict) -> dict:
    day = date.fromisoformat(args.get("datum") or ctx.now.date().isoformat())
    at = time.fromisoformat(args["uhrzeit"]) if args.get("uhrzeit") else ctx.now.time()
    eaten_at = datetime.combine(day, at, ctx.tz)
    uid = ctx.db.user.id

    meal = await ctx.db.insert(
        "meals",
        {
            "user_id": uid,
            "eaten_at": eaten_at.isoformat(),
            "meal_type": args.get("mahlzeit") or guess_meal_type(eaten_at.hour),
            "description": args.get("beschreibung"),
            "from_photo": bool(args.get("vom_foto")),
        },
    )
    items = await ctx.db.insert_many(
        "meal_items",
        [
            {
                "user_id": uid,
                "meal_id": meal["id"],
                "name": i["name"],
                "amount": i.get("menge"),
                "kcal": i.get("kcal") or 0,
                "protein_g": i.get("protein_g") or 0,
                "carbs_g": i.get("kh_g") or 0,
                "fat_g": i.get("fett_g") or 0,
            }
            for i in args["lebensmittel"]
        ],
    )
    return {
        "gespeichert": True,
        "mahlzeit_id": meal["id"],
        "summe": totals(items),
        "tagesbilanz": await _day_summary(ctx, day),
    }


async def _day_summary(ctx: ToolContext, day: date) -> dict:
    start = datetime.combine(day, time.min, ctx.tz)
    end = start + timedelta(days=1)
    meals = await ctx.db.select(
        "meals",
        select="id,meal_type,description,eaten_at,meal_items(kcal,protein_g,carbs_g,fat_g)",
        eaten_at=f"gte.{start.isoformat()}",
        order="eaten_at",
        **{"and": f"(eaten_at.lt.{end.isoformat()})"},
    )
    profiles = await ctx.db.select(
        "profiles", select="goal_kcal,goal_protein_g", id=f"eq.{ctx.db.user.id}"
    )
    goals = profiles[0] if profiles else {}
    return {
        "datum": day.isoformat(),
        "summe": totals([i for m in meals for i in m["meal_items"]]),
        "ziel_kcal": goals.get("goal_kcal"),
        "ziel_protein_g": goals.get("goal_protein_g"),
        "mahlzeiten": [
            {"id": m["id"], "typ": m["meal_type"], "beschreibung": m["description"]} for m in meals
        ],
    }


@tool(
    "tagesbilanz",
    "Kalorien, Protein, Kohlenhydrate und Fett eines Tages im Vergleich zu den Zielen.",
    obj({"datum": {"type": "string", "description": "YYYY-MM-DD, Standard: heute"}}),
)
async def tagesbilanz(ctx: ToolContext, args: dict) -> dict:
    return await _day_summary(
        ctx, date.fromisoformat(args.get("datum") or ctx.now.date().isoformat())
    )


@tool(
    "ziele_setzen",
    "Setzt die täglichen Ziele für Kalorien und/oder Protein.",
    obj({"kcal": {"type": "integer"}, "protein_g": {"type": "integer"}}),
)
async def ziele_setzen(ctx: ToolContext, args: dict) -> dict:
    values = {}
    if args.get("kcal"):
        values["goal_kcal"] = args["kcal"]
    if args.get("protein_g"):
        values["goal_protein_g"] = args["protein_g"]
    if not values:
        raise ValueError("Kein Ziel angegeben")
    await ctx.db.update("profiles", values, id=f"eq.{ctx.db.user.id}")
    return {"gespeichert": True, **values}


@tool(
    "naehrwerte_suchen",
    "Sucht Nährwerte (pro 100 g) eines gekauften Produkts in Open Food Facts, "
    "z. B. 'Ben & Jerry's Cookie Dough'. Für einfache Lebensmittel lieber selbst schätzen.",
    obj({"suchbegriff": {"type": "string"}}, ["suchbegriff"]),
)
async def naehrwerte_suchen(ctx: ToolContext, args: dict) -> dict:
    async with httpx.AsyncClient(
        timeout=8, headers={"User-Agent": "GRIND/0.1 (Privatprojekt)"}
    ) as http:
        res = await http.get(
            "https://world.openfoodfacts.org/cgi/search.pl",
            params={
                "search_terms": args["suchbegriff"],
                "json": 1,
                "page_size": 5,
                "fields": "product_name,brands,nutriments",
            },
        )
    res.raise_for_status()
    products = []
    for p in res.json().get("products", []):
        n = p.get("nutriments", {})
        if "energy-kcal_100g" not in n:
            continue
        products.append(
            {
                "produkt": p.get("product_name"),
                "marke": p.get("brands"),
                "kcal_100g": n.get("energy-kcal_100g"),
                "protein_100g": n.get("proteins_100g"),
                "kh_100g": n.get("carbohydrates_100g"),
                "fett_100g": n.get("fat_100g"),
            }
        )
    return {"treffer": products}


@tool(
    "eintrag_loeschen",
    "Löscht ein Training oder eine Mahlzeit (z. B. wenn der Nutzer sich vertan hat). "
    "Die ID steht im Ergebnis von training_speichern / mahlzeit_eintragen / tagesbilanz.",
    obj(
        {"typ": {"type": "string", "enum": ["training", "mahlzeit"]}, "id": {"type": "string"}},
        ["typ", "id"],
    ),
)
async def eintrag_loeschen(ctx: ToolContext, args: dict) -> dict:
    table = {"training": "workouts", "mahlzeit": "meals"}[args["typ"]]
    await ctx.db.delete(table, id=f"eq.{args['id']}")
    return {"geloescht": True}
