# Pepperbellypete Recipes

A single-page recipe collector built from Pepperbellypete YouTube shorts. The page lists 55 unique recipes — chili, chicken, and turkey (duplicate shorts of the same recipe are merged). It is a self-contained `index.html` file: open it directly in a browser or host it on GitHub Pages. All CSS and JavaScript are inlined, with no external assets.

## Features

- Search, category filters, a compact recipe index, and collapsible recipe cards. Categories include beef, chicken, and green chili; chili mac; chicken soups and stews, pasta and rice, casseroles, fried chicken and wings; dips; and turkey.
- **Shopping list:** check any recipes as you scroll, then generate one combined list. Duplicate ingredients are merged (quantities are added when the units are compatible). The list is grouped by category, can be checked off, copied, or printed. Your recipe selection is saved in the browser.
- **This week's pick:** check exactly one recipe to make it the week's pick. A badge and highlight mark that card, and the pick is saved in the browser even if you later check more recipes for the shopping list. Before you choose one, the panel says "Check one recipe to make it this week's pick."
- **Recommend similar recipes:** when exactly one recipe is checked, a "Recommend Similar Recipes" button suggests other recipes that can use up leftover perishables (meat, produce, dairy, herbs, and opened canned goods). Pantry staples like salt, pepper, oil, and common spices barely count. Suggestions show what they share with the pick and how many new items they'd need, and you can jump to a card or add it to the shopping list. The button is disabled with a "Select just one recipe" hint unless exactly one recipe is checked.

## Rebuild the page

From this folder (Python 3):

```bash
python3 build_recipes.py
```

That reads `recipes.json`, parses ingredients into structured quantities, and writes both `index.html` and `pepperbellypete-recipes.html`. `parse_ingredients.py` and `shop.js` must sit in the same folder as `build_recipes.py`.

`recipes.json` is the source of truth for titles, steps, notes, and ingredients. Each ingredient keeps its original display string plus parsed `qty`, `unit`, `item`, and shopping category.
