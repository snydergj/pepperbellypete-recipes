"""Parse recipe ingredient strings into structured {qty, unit, item, ...} fields."""
from __future__ import annotations
import re
from fractions import Fraction

UNICODE = str.maketrans({
    "½": " 1/2", "⅓": " 1/3", "⅔": " 2/3", "¼": " 1/4", "¾": " 3/4",
    "⅛": " 1/8", "⅜": " 3/8", "⅝": " 5/8", "⅞": " 7/8",
})

# Canonical unit names
UNIT_ALIASES = {
    "pound": "lb", "pounds": "lb", "lbs": "lb", "lb": "lb",
    "ounce": "oz", "ounces": "oz", "oz": "oz",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp", "tsps": "tsp",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp", "tbsps": "tbsp", "tbs": "tbsp",
    "cup": "cup", "cups": "cup",
    "can": "can", "cans": "can",
    "clove": "clove", "cloves": "clove",
    "packet": "packet", "packets": "packet",
    "stick": "stick", "sticks": "stick",
    "block": "block", "blocks": "block",
    "ear": "ear", "ears": "ear",
    "bag": "bag", "bags": "bag",
    "leaf": "count", "leaves": "count",
    "whole": "count",
}

LIQUIDS = {
    "beef broth", "chicken broth", "beer", "evaporated milk", "water",
    "olive oil", "oil", "ketchup", "worcestershire sauce", "hot sauce",
    "habanero sauce", "zippy zap",
}

SHOP_RULES = [
    ("meat", r"ground beef|ground sirloin|chili-grind|breakfast sausage|rotisserie chicken|pork shoulder|chuck roast"),
    ("produce", r"onion|jalapeños|^garlic$|cilantro|^lime$|potatoes|bell pepper|^peppers$|garden-fresh tomatoes|fresh corn"),
    ("dairy", r"^(.*\bcheese|unsalted butter|cream cheese|evaporated milk)$"),
    ("spices", r"chili powder|cumin|black pepper|garlic powder|onion powder|salt|paprika|oregano|coriander|cayenne|chili seasoning|williams|flavor-time|ranch seasoning|taco seasoning|fajita|adobo|bouillon|bay leaf|garlic salt|ground red pepper"),
    ("canned", r"tomato paste|tomato sauce|diced tomatoes|rotel|fire-roasted tomatoes|crushed tomatoes|chili-style tomatoes|green chiles|chili magic|broth|beans|whole-kernel corn|refried"),
    ("other", r"."),
]

# Most-specific first. Each maps a cleaned item string to a canonical name.
ITEM_ALIASES = [
    (r"zippy zap", "Zippy Zap"),
    (r"flavor-?time southern seasoning", "Flavor-Time Southern Seasoning"),
    (r"williams.*chili seasoning", "Williams Original Chili Seasoning"),
    (r"bush'?s chili magic", "Bush's Chili Magic"),
    (r"worcestershire", "Worcestershire sauce"),
    (r"chili-grind beef", "chili-grind beef"),
    (r"ground sirloin", "ground sirloin"),
    (r"chuck roast", "chuck roast"),
    (r"pork shoulder", "pork shoulder"),
    (r"ground (beef|meat)", "ground beef"),
    (r"(hot )?breakfast( or pan)? sausage", "breakfast sausage"),
    (r"rotisserie chicken", "rotisserie chicken"),
    (r"(hatch )?green chiles?", "green chiles"),
    (r"fire-?roasted rotel|rotel", "Rotel"),
    (r"petite diced tomatoes|diced tomatoes", "diced tomatoes"),
    (r"fire-?roasted tomatoes", "fire-roasted tomatoes"),
    (r"crushed tomatoes", "crushed tomatoes"),
    (r"chili-style tomatoes", "chili-style tomatoes"),
    (r"garden-fresh tomatoes", "garden-fresh tomatoes"),
    (r"tomato sauce", "tomato sauce"),
    (r"tomato paste", "tomato paste"),
    (r"chili paste", "chili paste"),
    (r"beef (broth|stock)", "beef broth"),
    (r"chicken broth", "chicken broth"),
    (r"stone-?ground mustard", "stone-ground mustard"),
    (r"(yellow )?mustard", "mustard"),
    (r"ancho chili powder", "ancho chili powder"),
    (r"chili powder", "chili powder"),
    (r"chili-lime adobo seasoning", "chili-lime adobo seasoning"),
    (r"chicken fajita seasoning", "chicken fajita seasoning"),
    (r"taco seasoning", "taco seasoning"),
    (r"ranch seasoning", "ranch seasoning"),
    (r"your favorite chili seasoning|chili seasoning", "chili seasoning"),
    (r"tomato-chicken bouillon", "tomato-chicken bouillon"),
    (r"habanero sauce", "habanero sauce"),
    (r"hot sauce", "hot sauce"),
    (r"olive oil|^oil$", "oil"),
    (r"white american cheese", "white American cheese"),
    (r"pepper jack cheese", "pepper jack cheese"),
    (r"medium cheddar cheese", "medium cheddar cheese"),
    (r"sharp white cheddar cheese", "sharp white cheddar cheese"),
    (r"colby jack cheese", "Colby Jack cheese"),
    (r"cream cheese", "cream cheese"),
    (r"shredded cheese|^cheese$", "cheese"),
    (r"unsalted butter|^butter$", "unsalted butter"),
    (r"evaporated milk", "evaporated milk"),
    (r"white kidney beans", "white kidney beans"),
    (r"black beans", "black beans"),
    (r"ranch-style beans", "ranch-style beans"),
    (r"chili beans", "chili beans"),
    (r"refried beans", "refried beans"),
    (r"15-bean dried beans", "15-bean dried beans"),
    (r"^beans$", "beans"),
    (r"whole-kernel corn", "whole-kernel corn"),
    (r"fresh corn|^corn$", "fresh corn"),
    (r"jumbo elbow noodles", "jumbo elbow noodles"),
    (r"^macaroni$", "macaroni"),
    (r"^pasta$", "pasta"),
    (r"cornbread mix", "cornbread mix"),
    (r"tater tots", "tater tots"),
    (r"tortilla chips", "tortilla chips"),
    (r"chili-cheese pork rinds|pork rinds", "chili-cheese pork rinds"),
    (r"^crackers$", "crackers"),
    (r"^oatmeal$", "oatmeal"),
    (r"^ketchup$", "ketchup"),
    (r"^beer$", "beer"),
    (r"^water$", "water"),
    (r"bay leaf", "bay leaf"),
    (r"garlic powder", "garlic powder"),
    (r"onion powder", "onion powder"),
    (r"garlic salt", "garlic salt"),
    (r"smoked paprika|^paprika$", "smoked paprika"),
    (r"dried oregano|^oregano$", "dried oregano"),
    (r"ground coriander|^coriander$", "ground coriander"),
    (r"cayenne pepper|^cayenne$", "cayenne pepper"),
    (r"ground red pepper", "ground red pepper"),
    (r"ground black pepper|^black pepper$", "black pepper"),
    (r"ground cumin|^cumin$", "cumin"),
    (r"^salt$", "salt"),
    (r"(large |medium |small |white |yellow )*(onions?)", "onion"),
    (r"jalape[nñ]os?", "jalapeños"),
    (r"(fresh minced |minced |fresh )?garlic", "garlic"),
    (r"bell pepper", "bell pepper"),
    (r"^peppers$", "peppers"),
    (r"potatoes", "potatoes"),
    (r"cilantro", "cilantro"),
    (r"^lime$", "lime"),
]


def to_float(s: str) -> float:
    s = " ".join(str(s).translate(UNICODE).split())
    m = re.fullmatch(r"(\d+)\s+(\d+/\d+)", s)
    if m:
        return float(int(m.group(1)) + Fraction(m.group(2)))
    if re.fullmatch(r"\d+/\d+", s):
        return float(Fraction(s))
    return float(s)


def normalize_item(raw: str) -> str:
    s = raw.lower().strip()
    s = s.replace("pepperbellypete's", "").replace("pepper belly pete's", "")
    s = s.replace("jalapeno", "jalapeño").replace("jalapeños", "jalapeños")
    s = s.replace("chilies", "chiles").replace("chilis", "chiles")
    s = re.sub(r"\s+", " ", s).strip(" .")
    for pat, name in ITEM_ALIASES:
        if re.search(pat, s, re.I):
            return name
    return s or raw.strip()


SHOP_BY_ITEM = {
    "ground beef": "meat", "ground sirloin": "meat", "chili-grind beef": "meat",
    "breakfast sausage": "meat", "rotisserie chicken": "meat",
    "pork shoulder": "meat", "chuck roast": "meat",
    "onion": "produce", "jalapeños": "produce", "garlic": "produce",
    "bell pepper": "produce", "peppers": "produce", "potatoes": "produce",
    "cilantro": "produce", "lime": "produce", "fresh corn": "produce",
    "garden-fresh tomatoes": "produce",
    "green chiles": "canned", "Rotel": "canned", "diced tomatoes": "canned",
    "fire-roasted tomatoes": "canned", "crushed tomatoes": "canned",
    "chili-style tomatoes": "canned", "tomato sauce": "canned",
    "tomato paste": "canned", "chili paste": "canned",
    "beef broth": "canned", "chicken broth": "canned",
    "white kidney beans": "canned", "black beans": "canned",
    "ranch-style beans": "canned", "chili beans": "canned",
    "refried beans": "canned", "15-bean dried beans": "canned", "beans": "canned",
    "whole-kernel corn": "canned", "Bush's Chili Magic": "canned",
    "white American cheese": "dairy", "pepper jack cheese": "dairy",
    "medium cheddar cheese": "dairy", "sharp white cheddar cheese": "dairy",
    "Colby Jack cheese": "dairy", "cream cheese": "dairy", "cheese": "dairy",
    "unsalted butter": "dairy", "evaporated milk": "dairy",
    "chili powder": "spices", "ancho chili powder": "spices", "cumin": "spices",
    "black pepper": "spices", "garlic powder": "spices", "onion powder": "spices",
    "salt": "spices", "smoked paprika": "spices", "dried oregano": "spices",
    "ground coriander": "spices", "cayenne pepper": "spices",
    "chili seasoning": "spices", "Williams Original Chili Seasoning": "spices",
    "Flavor-Time Southern Seasoning": "spices", "ranch seasoning": "spices",
    "taco seasoning": "spices", "chicken fajita seasoning": "spices",
    "chili-lime adobo seasoning": "spices", "tomato-chicken bouillon": "spices",
    "bay leaf": "spices", "garlic salt": "spices", "ground red pepper": "spices",
    "chili-cheese pork rinds": "other",
}
def shop_cat(item: str) -> str:
    if item in SHOP_BY_ITEM:
        return SHOP_BY_ITEM[item]
    s = item.lower()
    for cat, pat in SHOP_RULES:
        if re.search(pat, s, re.I):
            return cat
    return "other"


def _clean_rest(rest: str) -> str:
    s = rest.strip()
    # Drop equivalent-measure parens like "(1/2 cup)" or "(15.5 oz each)" already consumed
    s = re.sub(r"\((?:about )?two 15\.5 oz cans\)", " ", s, flags=re.I)
    s = re.sub(r"\(about 2 tbsp minced\)", " ", s, flags=re.I)
    s = re.sub(r"\(80/20\)", " ", s)
    s = re.sub(r"\(93/7\)", " ", s)
    s = re.sub(r"\(Jimmy Dean Hot\)", " ", s, flags=re.I)
    s = re.sub(r"\(his own blend\)", " ", s, flags=re.I)
    s = re.sub(r"\(optional, to finish\)", " ", s, flags=re.I)
    s = re.sub(r"\(optional\)", " ", s, flags=re.I)
    s = re.sub(r"\(amount not specified\)", " ", s, flags=re.I)
    s = re.sub(r"\(amount not clearly specified;? possibly 1 tbsp\)", " ", s, flags=re.I)
    s = re.sub(r"\(some videos of this same recipe use 2 large jalapeños\)", " ", s, flags=re.I)
    s = re.sub(r"\(Pete uses a grocery-store roasted chicken\)", " ", s, flags=re.I)
    s = re.sub(r"\(from the grocery store deli\)", " ", s, flags=re.I)
    s = re.sub(r"\(Pete prefers the packet over the can\)", " ", s, flags=re.I)
    s = re.sub(r"\(Pete calls it '[^']+'\)", " ", s, flags=re.I)
    s = re.sub(r"\(Pete uses rotini\)", " ", s, flags=re.I)
    s = re.sub(r"\(Pete uses a unsweetened mix; use whatever you like\)", " ", s, flags=re.I)
    s = re.sub(r"\(Pete uses pinto; use whatever you like\)", " ", s, flags=re.I)
    s = re.sub(r"\(or 1 can of corn\)", " ", s, flags=re.I)
    s = re.sub(r"\(or regular chili powder\)", " ", s, flags=re.I)
    s = re.sub(r"\(your favorite\)", " ", s, flags=re.I)
    s = re.sub(r"\(part of the 'Texas Trinity'\)", " ", s, flags=re.I)
    s = re.sub(r"\(Campfire Style\)", " ", s, flags=re.I)
    s = re.sub(r", Campfire Style", " ", s, flags=re.I)
    s = re.sub(r"\(the audio may be 'tomato paste'; 6 oz is the amount\)", " ", s, flags=re.I)
    s = re.sub(r"\(Pete adds 'Heat Blast'\)", " ", s, flags=re.I)
    s = re.sub(r"\(two 32 oz containers\)", " ", s, flags=re.I)
    s = re.sub(r"\(type and amount not specified\)", " ", s, flags=re.I)
    s = re.sub(r"enough to line the top,?\s*", " ", s, flags=re.I)
    # Only strip trailing prep and serving notes. Do not remove words that
    # are part of a product name (diced tomatoes, fire-roasted, white cheddar).
    s = re.sub(r",?\s*to taste", " ", s, flags=re.I)
    s = re.sub(r",?\s*to finish", " ", s, flags=re.I)
    s = re.sub(r",?\s*optional", " ", s, flags=re.I)
    s = re.sub(r",?\s*for serving", " ", s, flags=re.I)
    s = re.sub(r",?\s*for topping", " ", s, flags=re.I)
    s = re.sub(r",?\s*for searing", " ", s, flags=re.I)
    s = re.sub(r",?\s*for roasting the garlic and peppers", " ", s, flags=re.I)
    s = re.sub(r",?\s*trimmed and cubed", " ", s, flags=re.I)
    s = re.sub(r",?\s*seeds and all", " ", s, flags=re.I)
    s = re.sub(r",?\s*kernels cut off", " ", s, flags=re.I)
    s = re.sub(r",?\s*deboned and chopped", " ", s, flags=re.I)
    s = re.sub(r",?\s*boiled 8 minutes(?: \(al dente\))?", " ", s, flags=re.I)
    s = re.sub(r",?\s*rinsed", " ", s, flags=re.I)
    s = re.sub(r",?\s*(chopped|diced|minced|pureed|seeded)$", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" ,.")
    return s


def parse_ingredient(text: str) -> dict:
    original = text
    s = " ".join(text.translate(UNICODE).split()).strip()
    optional = bool(re.search(r"\boptional\b", s, re.I))
    approx = bool(re.match(r"^(about|approximately|roughly)\b", s, re.I))
    s0 = re.sub(r"^(about|approximately|roughly)\s+", "", s, flags=re.I)

    qty = None
    unit = None
    each_oz = None
    rest = s0

    # Special phrasings
    m = re.match(r"^splash of\s+(.+)$", s0, re.I)
    if m:
        rest = m.group(1)
        unit = "splash"
        return _finish(original, None, unit, rest, None, approx, optional)

    m = re.match(r"^a couple of tablespoons?\s+(.+)$", s0, re.I)
    if m:
        return _finish(original, 2.0, "tbsp", m.group(1), None, True, optional)

    m = re.match(r"^a little\s+(.+)$", s0, re.I)
    if m:
        return _finish(original, None, None, m.group(1), None, True, optional)

    m = re.match(r"^juice of\s+(\d+|one)\s+(?:whole\s+)?(.+)$", s0, re.I)
    if m:
        q = 1.0 if m.group(1).lower() == "one" else to_float(m.group(1))
        return _finish(original, q, "count", m.group(2), None, approx, optional)

    # N cans/packets/blocks (X oz each) ITEM
    m = re.match(
        r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s+"
        r"(cans?|packets?|blocks?)\s+"
        r"\((?:about\s+)?(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s*oz\s+each\)\s*(.+)$",
        s0, re.I,
    )
    if m:
        return _finish(original, to_float(m.group(1)), UNIT_ALIASES[m.group(2).lower()], m.group(4), to_float(m.group(3)), approx, optional)

    # 1 can/packet/block (X oz) ITEM
    m = re.match(
        r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s+"
        r"(cans?|packets?|blocks?)\s+"
        r"\((?:about\s+)?(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s*oz\)\s*(.+)$",
        s0, re.I,
    )
    if m:
        return _finish(original, to_float(m.group(1)), UNIT_ALIASES[m.group(2).lower()], m.group(4), to_float(m.group(3)), approx, optional)

    # 1 oz packet oatmeal
    m = re.match(r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s*oz\s+packets?\s+(.+)$", s0, re.I)
    if m:
        return _finish(original, 1.0, "packet", m.group(2), to_float(m.group(1)), approx, optional)

    # 1 lb bag ITEM
    m = re.match(r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s*lb\s+bags?\s+(.+)$", s0, re.I)
    if m:
        return _finish(original, to_float(m.group(1)), "lb", m.group(2), None, approx, optional)

    # N cloves [minced] garlic / N cloves ITEM
    m = re.match(r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s+cloves?\s+(?:minced\s+)?(.+)$", s0, re.I)
    if m:
        return _finish(original, to_float(m.group(1)), "clove", m.group(2), None, approx, optional)

    # 4 oz (1/2 cup) ITEM  — prefer the leading unit, ignore the equivalent
    m = re.match(
        r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s*"
        r"(lb|lbs|pounds?|oz|ounces?|tsp|teaspoons?|tbsp|tbsps?|tablespoons?|cups?|sticks?|ears?)\s+"
        r"\([^)]+\)\s*(.+)$",
        s0, re.I,
    )
    if m:
        u = UNIT_ALIASES[m.group(2).lower()]
        return _finish(original, to_float(m.group(1)), u, m.group(3), None, approx, optional)

    # Leading qty + unit + item
    m = re.match(
        r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s*"
        r"(lb|lbs|pounds?|oz|ounces?|tsp|teaspoons?|tbsp|tbsps?|tbs|tablespoons?|cups?|"
        r"cans?|packets?|sticks?|blocks?|ears?|bags?)\s+(?:of\s+)?(.+)$",
        s0, re.I,
    )
    if m:
        return _finish(original, to_float(m.group(1)), UNIT_ALIASES[m.group(2).lower()], m.group(3), None, approx, optional)

    # Qty with a size word then a count item: 1 large onion, 3 fresh jalapeños, 1 fully cooked...
    m = re.match(r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s+(.+)$", s0, re.I)
    if m:
        return _finish(original, to_float(m.group(1)), "count", m.group(2), None, approx, optional)

    # No quantity
    return _finish(original, None, None, s0, None, approx, optional)


def _finish(text, qty, unit, rest, each_oz, approx, optional):
    item = normalize_item(_clean_rest(rest))
    # 1 stick butter -> each_oz 4 (standard US stick)
    if unit == "stick" and each_oz is None and "butter" in item.lower():
        each_oz = 4.0
    out = {
        "text": text,
        "qty": qty,
        "unit": unit,
        "item": item,
        "shop": shop_cat(item),
        "each_oz": each_oz,
        "approx": approx,
        "optional": optional,
    }
    return out


def annotate_recipes(recipes: list) -> list:
    """Ensure every ingredient is a structured object; keep original display as 'text'."""
    for r in recipes:
        parsed = []
        for ing in r.get("ingredients") or []:
            if isinstance(ing, str):
                parsed.append(parse_ingredient(ing))
            elif isinstance(ing, dict) and "text" in ing:
                # Re-parse from text so parser improvements always apply
                parsed.append(parse_ingredient(ing["text"]))
            else:
                parsed.append(ing)
        r["ingredients"] = parsed
    return recipes


if __name__ == "__main__":
    import json
    from pathlib import Path
    recipes = json.loads(Path("/workspace/artifacts/recipes.json").read_text())
    annotate_recipes(recipes)
    for r in recipes:
        print("====", r["title"])
        for i in r["ingredients"]:
            q = i["qty"]
            qst = "" if q is None else (str(int(q)) if float(q) == int(q) else str(q))
            extra = []
            if i["each_oz"]:
                extra.append(f"each_oz={i['each_oz']}")
            if i["approx"]:
                extra.append("approx")
            if i["optional"]:
                extra.append("opt")
            print(f"  {qst:>6} {str(i['unit'] or '-'):<7} {i['item']:<36} [{i['shop']}] {' '.join(extra)}")
            print(f"         «{i['text']}»")
