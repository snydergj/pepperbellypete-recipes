/* Shopping-list merge + weekly pick. Works in the browser and in Node. */
(function (root) {
  "use strict";

  var LIQUIDS = {
    "beef broth": 1, "chicken broth": 1, "beer": 1, "evaporated milk": 1,
    "water": 1, "oil": 1, "ketchup": 1, "Worcestershire sauce": 1,
    "hot sauce": 1, "habanero sauce": 1, "Zippy Zap": 1
  };

  var SHOP_ORDER = ["meat", "produce", "canned", "dairy", "spices", "other"];
  var SHOP_LABEL = {
    meat: "Meat",
    produce: "Produce",
    canned: "Canned & jarred",
    dairy: "Dairy",
    spices: "Spices & seasonings",
    other: "Other"
  };

  var PLURAL = {
    "onion": "onions",
    "jalapeños": "jalapeños",
    "rotisserie chicken": "rotisserie chickens",
    "lime": "limes",
    "potatoes": "potatoes",
    "bay leaf": "bay leaves",
    "bell pepper": "bell peppers",
    "fresh corn": "fresh corn"
  };

  function isLiquid(item) { return !!LIQUIDS[item]; }

  function formatNum(n) {
    if (n == null || !isFinite(n)) return "";
    var sign = n < 0 ? "-" : "";
    n = Math.abs(n);
    var whole = Math.floor(n + 1e-9);
    var frac = n - whole;
    if (frac < 1e-6) return sign + String(whole);
    var dens = [2, 3, 4, 8, 16];
    var bestN = 0, bestD = 1, bestE = 1;
    for (var i = 0; i < dens.length; i++) {
      var d = dens[i];
      var numer = Math.round(frac * d);
      var e = Math.abs(frac - numer / d);
      if (numer > 0 && numer < d && e < bestE - 1e-12) {
        bestN = numer; bestD = d; bestE = e;
      }
      if (numer === d && e < 1e-6) return sign + String(whole + 1);
    }
    if (bestE < 1e-6) {
      return sign + (whole ? whole + " " : "") + bestN + "/" + bestD;
    }
    var r = Math.round(n * 100) / 100;
    if (Math.abs(r - Math.round(r)) < 1e-6) return sign + String(Math.round(r));
    var r2 = Math.round(n * 10) / 10;
    if (Math.abs(n - r2) < 1e-6) return sign + String(r2);
    return sign + String(r);
  }

  function isTidy(value, dens) {
    for (var i = 0; i < dens.length; i++) {
      var d = dens[i];
      var n = Math.round(value * d);
      if (Math.abs(value - n / d) < 1e-6) return n / d;
    }
    return null;
  }

  function formatOz(oz) {
    return formatNum(oz) + " oz";
  }

  function formatLb(oz) {
    var lb = Math.floor((oz + 1e-9) / 16);
    var rem = Math.round((oz - lb * 16) * 1000) / 1000;
    if (rem < 1e-6) rem = 0;
    if (lb && rem) return formatNum(lb) + " lb " + formatNum(rem) + " oz";
    if (lb) return formatNum(lb) + " lb";
    return formatNum(oz) + " oz";
  }

  function formatTsp(tsp) {
    if (tsp <= 0) return "";
    var cup = tsp / 48;
    if (cup >= 0.25 - 1e-9) {
      var niceCup = isTidy(cup, [2, 3, 4, 8]);
      if (niceCup != null) return formatNum(niceCup) + (niceCup <= 1 ? " cup" : " cups");
    }
    var tbsp = tsp / 3;
    // Halves and quarters of a tablespoon only — never "1/3 tbsp" for a teaspoon.
    var niceTbsp = isTidy(tbsp, [2, 4]);
    if (niceTbsp != null && niceTbsp >= 0.5) return formatNum(niceTbsp) + " tbsp";
    var wholeTbsp = Math.floor(tsp / 3 + 1e-9);
    var rem = Math.round((tsp - wholeTbsp * 3) * 1000) / 1000;
    if (rem < 1e-6) rem = 0;
    if (wholeTbsp && rem) return formatNum(wholeTbsp) + " tbsp + " + formatNum(rem) + " tsp";
    if (wholeTbsp) return formatNum(wholeTbsp) + " tbsp";
    return formatNum(tsp) + " tsp";
  }

  function family(ing) {
    var u = ing.unit;
    if (ing.each_oz && (u === "can" || u === "packet" || u === "block" || u === "stick")) {
      return isLiquid(ing.item) ? "volume" : "weight";
    }
    if (u === "lb" || u === "oz") return isLiquid(ing.item) ? "volume" : "weight";
    if (u === "tsp" || u === "tbsp" || u === "cup") return "volume";
    if (u === "can" || u === "packet" || u === "clove" || u === "count" ||
        u === "ear" || u === "splash" || u === "bag" || u === "stick" || u === "block") {
      return u;
    }
    return "none";
  }

  function toBase(ing, fam) {
    var q = Number(ing.qty);
    if (!isFinite(q)) return 0;
    var u = ing.unit;
    if (fam === "weight") {
      if (ing.each_oz && (u === "can" || u === "packet" || u === "block" || u === "stick")) {
        return q * Number(ing.each_oz);
      }
      if (u === "lb") return q * 16;
      if (u === "oz") return q;
    }
    if (fam === "volume") {
      if (u === "tsp") return q;
      if (u === "tbsp") return q * 3;
      if (u === "cup") return q * 48;
      if (u === "oz") return q * 6; // fl oz → tsp
      if (ing.each_oz && (u === "can" || u === "packet" || u === "block")) {
        return q * Number(ing.each_oz) * 6;
      }
    }
    return q;
  }

  function unitWord(unit, qty) {
    var map = {
      ear: ["ear", "ears"], clove: ["clove", "cloves"], can: ["can", "cans"],
      packet: ["packet", "packets"], bag: ["bag", "bags"], stick: ["stick", "sticks"],
      block: ["block", "blocks"]
    };
    if (!map[unit]) return unit || "";
    return qty === 1 ? map[unit][0] : map[unit][1];
  }

  function itemWord(item, fam, qty) {
    if (fam === "count" && qty !== 1) return PLURAL[item] || (item + "s");
    return item;
  }

  function qtyPhrase(fam, amount, item, shop, parts) {
    if (fam === "weight") return formatWeight(amount, item, shop, parts);
    if (fam === "volume") return formatTsp(amount);
    if (fam === "count") return formatNum(amount);
    if (fam === "splash") return "a splash";
    if (fam === "none") return "some, to taste";
    return formatNum(amount) + " " + unitWord(fam, amount);
  }

  function formatWeight(oz, item, shop, parts) {
    parts = parts || [];
    var weightParts = parts.filter(function (p) { return family(p) === "weight"; });
    var sized = weightParts.filter(function (p) { return p.each_oz; });
    var unsized = weightParts.filter(function (p) { return !p.each_oz; });
    // Prefer a can/packet count when every sized part shares a size and ounces divide evenly.
    if (sized.length) {
      var each = Number(sized[0].each_oz);
      var same = sized.every(function (p) { return Number(p.each_oz) === each; });
      var u0 = sized[0].unit === "packet" ? "packet" : (sized[0].unit === "block" ? "block" : "can");
      var sameU = sized.every(function (p) {
        var u = p.unit === "packet" ? "packet" : (p.unit === "block" ? "block" : "can");
        return u === u0;
      });
      if (same && sameU && each) {
        var unsizedOz = 0;
        unsized.forEach(function (p) { unsizedOz += toBase(p, "weight"); });
        if (unsizedOz && Math.abs((unsizedOz / each) - Math.round(unsizedOz / each)) < 1e-6) {
          unsizedOz = 0; // fold exact multiples of the can size into the can count
        }
        var nCans = (oz - unsizedOz) / each;
        if (Math.abs(nCans - Math.round(nCans)) < 1e-6 && unsizedOz < 1e-9) {
          return formatNum(Math.round(nCans)) + " " + unitWord(u0, Math.round(nCans));
        }
      }
    }
    if (shop === "meat") return formatLb(oz);
    return formatOz(oz);
  }

  function mergeIngredients(selected) {
    /* selected: [{id, title, ingredients:[{text,qty,unit,item,shop,each_oz,approx,optional}]}] */
    var groups = {};
    selected.forEach(function (recipe) {
      (recipe.ingredients || []).forEach(function (ing) {
        var key = ing.item;
        if (!groups[key]) {
          groups[key] = { item: ing.item, shop: ing.shop || "other", parts: [], sources: [], optional: true };
        }
        groups[key].parts.push(Object.assign({ _title: recipe.title, _id: recipe.id }, ing));
        if (groups[key].sources.indexOf(recipe.title) === -1) {
          groups[key].sources.push(recipe.title);
        }
        if (!ing.optional) groups[key].optional = false;
      });
    });

    var rows = Object.keys(groups).map(function (key) {
      var g = groups[key];
      var buckets = {};
      var approx = false;
      g.parts.forEach(function (ing) {
        var fam = family(ing);
        if (ing.approx) approx = true;
        if (fam === "none" || ing.qty == null && fam !== "splash") {
          if (ing.unit === "splash") fam = "splash";
          else fam = "none";
        }
        if (!buckets[fam]) buckets[fam] = { amount: 0, n: 0 };
        if (fam === "none" || fam === "splash") {
          buckets[fam].n += 1;
        } else {
          buckets[fam].amount += toBase(ing, fam);
          buckets[fam].n += 1;
        }
      });

      var bits = [];
      var order = ["weight", "volume", "can", "packet", "clove", "count", "ear", "stick", "block", "bag", "splash", "none"];
      var primaryFam = null;
      order.forEach(function (fam) {
        if (!buckets[fam]) return;
        if (!primaryFam && fam !== "splash" && fam !== "none") primaryFam = fam;
        bits.push(qtyPhrase(fam, buckets[fam].amount, g.item, g.shop, g.parts));
      });

      var line;
      if (bits.length === 1 && buckets.splash && !buckets.none && Object.keys(buckets).length === 1) {
        line = "a splash of " + g.item;
      } else if (bits.length === 1 && buckets.none && Object.keys(buckets).length === 1) {
        line = g.item + ", to taste";
      } else if (bits.length === 1) {
        var name = itemWord(g.item, primaryFam, buckets[primaryFam] ? buckets[primaryFam].amount : 1);
        line = bits[0] + " " + name;
      } else {
        line = g.item + ": " + bits.join(" + ");
      }
      if (g.optional) line += " (optional)";
      if (approx && !/^a splash/.test(line) && !/, to taste$/.test(line)) {
        /* leave unmarked; individual "About" amounts already summed */
      }
      return {
        item: g.item,
        shop: g.shop,
        line: line.replace(/\s+/g, " ").trim(),
        sources: g.sources,
        optional: g.optional
      };
    });

    rows.sort(function (a, b) {
      var ia = SHOP_ORDER.indexOf(a.shop);
      var ib = SHOP_ORDER.indexOf(b.shop);
      if (ia < 0) ia = 99;
      if (ib < 0) ib = 99;
      if (ia !== ib) return ia - ib;
      return a.item.toLowerCase().localeCompare(b.item.toLowerCase());
    });
    return rows;
  }

  function groupedList(rows) {
    var out = [];
    var cur = null;
    rows.forEach(function (row) {
      if (!cur || cur.shop !== row.shop) {
        cur = { shop: row.shop, label: SHOP_LABEL[row.shop] || row.shop, items: [] };
        out.push(cur);
      }
      cur.items.push(row);
    });
    return out;
  }

  function listAsText(selected, rows) {
    var titles = selected.map(function (r) { return r.title; });
    var lines = ["Shopping list", titles.join(", "), ""];
    groupedList(rows).forEach(function (g) {
      lines.push(g.label);
      g.items.forEach(function (row) {
        lines.push("- " + row.line + "  (" + row.sources.join("; ") + ")");
      });
      lines.push("");
    });
    return lines.join("\n").trim() + "\n";
  }

  // Pantry staples get little or no weight in similar-recipe scoring.
  var STAPLES = {
    "salt": 1, "black pepper": 1, "oil": 1, "chili powder": 1, "cumin": 1,
    "garlic powder": 1, "onion powder": 1, "smoked paprika": 1, "cayenne pepper": 1,
    "dried oregano": 1, "ground coriander": 1, "bay leaf": 1, "garlic salt": 1,
    "ground red pepper": 1, "ancho chili powder": 1, "water": 1
  };

  var DISPLAY_ITEM = {
    "green chiles": "Hatch chiles"
  };

  function displayItem(name) {
    return DISPLAY_ITEM[name] || name;
  }

  function isStaple(name) {
    return !!STAPLES[name];
  }

  function itemWeight(ing) {
    var name = typeof ing === "string" ? ing : (ing && ing.item);
    var shop = typeof ing === "object" && ing ? ing.shop : null;
    if (!name) return 0;
    if (STAPLES[name]) return 0;
    if (shop === "meat" || shop === "produce" || shop === "dairy") return 3;
    if (/cilantro|parsley|herb/.test(name)) return 3;
    if (shop === "canned") return 2;
    return 0.4;
  }

  function ingredientIndex(recipe) {
    var map = {};
    (recipe.ingredients || []).forEach(function (ing) {
      if (!ing || !ing.item) return;
      if (!map[ing.item]) map[ing.item] = ing;
    });
    return map;
  }

  function meatPounds(recipe) {
    var oz = 0;
    (recipe.ingredients || []).forEach(function (ing) {
      if (!ing || ing.shop !== "meat" || ing.qty == null) return;
      if (ing.unit === "lb") oz += Number(ing.qty) * 16;
      else if (ing.unit === "oz") oz += Number(ing.qty);
      else if (ing.unit === "count" && /chicken/.test(ing.item)) oz += Number(ing.qty) * 32;
    });
    return oz / 16;
  }

  function batchPenalty(recipe) {
    var text = ((recipe.servings || "") + " " + (recipe.summary || "")).toLowerCase();
    var p = 0;
    if (/12-?quart|\b12q\b/.test(text)) p += 0.16;
    else if (/10-?quart/.test(text)) p += 0.12;
    var lb = meatPounds(recipe);
    if (lb >= 5) p += 0.14;
    else if (lb >= 4) p += 0.08;
    else if (lb >= 3) p += 0.04;
    return Math.min(p, 0.22);
  }

  function scoreRecipeAgainstPick(pick, candidate) {
    var pickMap = ingredientIndex(pick);
    var candMap = ingredientIndex(candidate);
    var shared = [];
    var sharedPerishable = [];
    var overlap = 0;
    Object.keys(pickMap).forEach(function (name) {
      if (!candMap[name]) return;
      shared.push(name);
      var w = Math.max(itemWeight(pickMap[name]), itemWeight(candMap[name]));
      overlap += w;
      if (w >= 2) sharedPerishable.push(name);
    });
    var newItems = [];
    var newCost = 0;
    Object.keys(candMap).forEach(function (name) {
      if (pickMap[name]) return;
      newItems.push(name);
      newCost += itemWeight(candMap[name]);
    });
    var sharedUseful = shared.filter(function (n) { return !isStaple(n); });
    var newUseful = newItems.filter(function (n) { return !isStaple(n); });
    var denom = overlap + newCost + 0.5;
    var score = (denom ? overlap / denom : 0)
      + 0.18 * sharedPerishable.length
      - 0.06 * newUseful.length
      - batchPenalty(candidate);
    if (sharedUseful.length === 0) score = -1;

    sharedUseful.sort(function (a, b) {
      var wa = itemWeight(pickMap[a] || candMap[a]);
      var wb = itemWeight(pickMap[b] || candMap[b]);
      if (wb !== wa) return wb - wa;
      return a.toLowerCase().localeCompare(b.toLowerCase());
    });
    var shown = sharedUseful.map(displayItem);
    var listed = shown.slice(0, 6);
    var ellip = shown.length > 6 ? "…" : "";
    var reason = "Shares " + sharedUseful.length + " ingredient" + (sharedUseful.length === 1 ? "" : "s")
      + " with this week's pick"
      + (listed.length ? ": " + listed.join(", ") + ellip : ".");
    var needs = "needs " + newUseful.length + " new item" + (newUseful.length === 1 ? "" : "s");
    return {
      recipe: candidate,
      id: candidate.id,
      title: candidate.title,
      score: Math.round(score * 1000) / 1000,
      shared: sharedUseful,
      sharedCount: sharedUseful.length,
      newItems: newUseful,
      newCount: newUseful.length,
      perishableShared: sharedPerishable,
      reason: reason,
      needs: needs
    };
  }

  function recommendSimilar(pick, recipes, n) {
    n = n == null ? 5 : n;
    if (!pick) return [];
    var scored = (recipes || []).filter(function (r) { return r && r.id !== pick.id; })
      .map(function (r) { return scoreRecipeAgainstPick(pick, r); })
      .filter(function (x) { return x.sharedCount > 0 && x.score >= 0; });
    scored.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      if (b.sharedCount !== a.sharedCount) return b.sharedCount - a.sharedCount;
      return a.newCount - b.newCount;
    });
    return scored.slice(0, n);
  }

  var Shop = {
    mergeIngredients: mergeIngredients,
    groupedList: groupedList,
    listAsText: listAsText,
    recommendSimilar: recommendSimilar,
    scoreRecipeAgainstPick: scoreRecipeAgainstPick,
    itemWeight: itemWeight,
    isStaple: isStaple,
    formatNum: formatNum,
    formatOz: formatOz,
    formatTsp: formatTsp,
    STAPLES: STAPLES,
    SHOP_ORDER: SHOP_ORDER,
    SHOP_LABEL: SHOP_LABEL
  };

  if (typeof module !== "undefined" && module.exports) module.exports = Shop;
  root.Shop = Shop;
})(typeof globalThis !== "undefined" ? globalThis : this);
