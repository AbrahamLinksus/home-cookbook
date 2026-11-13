# Usage scenarios — Home Cookbook

> Written by the Product Critic against `docs/SPEC.md`. Each scenario follows the spec's own flows.
> Result: `handled` (with the US/F id that covers it) or `GAP` (gap ids refer to the Gaps list in the critic report).

## S-01 · Typing in awkward amounts on the phone
Jake copies Grandma's Apple Pie from a stained card onto his phone. The card says "1 1/2 cups flour", "2-3 cloves" (in the cider glaze), "⅛ tsp nutmeg", "0.5 cup brown sugar". The phone keyboard has no ½ key, so he types "1 1/2" and "0.5". For the garlic he can only type one number.
- Walk: F-1 lets him enter amount + unit + name, and US-03 shows "2½" is a valid amount, but the spec never says which ways of writing an amount are accepted ("1 1/2", "1.5", "½", "3/4"), whether "1 1/2" might be read as 11/2, or how a range like "2-3" is entered and scaled.
- Result: **GAP** (G-4).

## S-02 · Scaling a metric recipe down to 3 people
Aunt May's Scones: 8 servings, "225 g flour", "50 g butter", "1 egg", "⅛ tsp salt", "150 ml buttermilk". Jake scales to 3 servings.
- Walk: F-3 rounds to the nearest whole or ¼/⅓/½/⅔/¾ in the same unit. 225 g × ⅜ = 84⅜ g → shows "84⅓ g"; 50 g → "18¾ g"; ⅛ tsp × ⅜ ≈ 0.05 → would round to 0, so shows "¼ tsp", which is *more* than the original ⅛ tsp; "1 egg" → ⅜ → rounds to "½ egg" (counted-item rule) though the min-step rule says ¼. Fractions of a gram are not something anyone measures, and the minimum step can make an amount bigger than the unscaled recipe.
- Result: **GAP** (G-5).

## S-03 · Phone and laptop at the same time
Sunday evening: Jake has "Lemon Cake" open in the edit form on the laptop, rewriting steps 3–6. Meanwhile his partner Sam, in the kitchen, opens Lemon Cake on the phone, fixes the oven temperature from 220°C to 180°C and saves. Jake saves ten minutes later. Separately, Sam deletes "Shepherd's Pie" on the phone (the undo bar goes away) while Jake still has it open in edit on the laptop; Jake then taps Save.
- Walk: §9 says "the last save wins" *(assumed)*. Jake's save silently replaces Sam's oven fix; neither of them is told. For the deleted recipe, the spec does not say whether Jake's save brings it back, fails, or loses his typing.
- Result: **GAP** (G-2, G-9).

## S-04 · The wrong recipe deleted, and the phone locks
Flour on his hands, Jake means to delete "Apple Crumble (old)" but taps Delete on "Grandma's Apple Pie". The phone screen locks a few seconds later; when he unlocks it 30 seconds on, the Undo bar is gone. Another time he deletes it, then taps into "Lemon Cake" to check something within the 10 seconds.
- Walk: F-4 and §13 say after ~10 s the delete is final, restorable only from an export (owner's choice). Covered. Not stated: whether the Undo bar stays visible when he opens another recipe or the phone sleeps during the 10 seconds.
- Result: **handled** (F-4, §13), plus a small **GAP** (G-11).

## S-05 · Loading an older export over current recipes
In March Jake exported 42 recipes. Since then he renamed "Mum's Scones" to "Aunt May's Scones", and last week he accidentally wiped the ingredient list of "Lemon Cake" while editing and saved it. He imports the March file hoping to get the old Lemon Cake back.
- Walk: F-6 skips titles already in the app, so the broken "Lemon Cake" is not replaced, and "Mum's Scones" comes back as a second copy beside "Aunt May's Scones". Since D-30 the result names "Lemon Cake" as skipped and says "To restore one, delete it first, then import again", so he deletes the broken one, imports again and gets the March version back.
- Result: **covered** (F-6, D-30).

## S-06 · The home computer's disk dies
In November the home computer's disk fails. Jake reinstalls the app (now a newer version) on a new computer. His last export, `cookbook-2026-04-02`, is on his phone's Downloads folder.
- Walk: §13 states he loses everything since the last export; importing that file restores the rest (US-09). Covered — but he had no idea his last export was seven months old: nothing in the app shows when he last exported. And the spec doesn't say whether an export made by an older version of the app still loads into a newer one; if it doesn't, F-6 says "This file isn't a Home Cookbook export" and every recipe is gone.
- Result: **GAP** (G-3, G-7).

## S-07 · Two recipes with the same title
Jake has two pancake recipes from two grandmothers and types both in as "Pancakes" (one 4 servings with buttermilk, one 6 servings with milk). Later he exports all 42 recipes, empties the app (new computer) and imports the file.
- Walk: F-1 doesn't say whether two recipes may share a title. If it allows it, F-6's rule "two recipes with the same title inside one file: the first is imported, the second skipped" means the restore shows 41 recipes and one grandmother's pancakes are silently gone — breaking US-09's "all 42 identical".
- Result: **GAP** (G-1).

## S-08 · Searching the way people actually type
Jake searches by ingredient for "egg" (recipes list "3 eggs" and "1 eggplant"), by name for "grandmas apple" (title is "Grandma's Apple Pie"), and for "creme" (ingredient is "crème fraîche").
- Walk: US-04 shows part-of-title matching ("pie") and ignoring case, but the spec doesn't say whether ingredient search matches part of a word ("egg" in "eggs" — and then also "eggplant"), whether apostrophes and accents are ignored, or whether ingredient search looks at the name only or the unit/amount too.
- Result: **GAP** (G-8).

## S-09 · A huge recipe and a forgotten line
Christmas cake: 38 ingredients, 22 steps, step 4 is a 900-word paragraph pasted from an email. Halfway through typing Jake realises he skipped "4 eggs" after "250 g butter" (line 6) and adds it — it lands at the bottom as line 39.
- Walk: §6 assumes up to ~30 ingredients / ~20 steps but doesn't say if more is refused; §7 gives steps add/remove/**reorder** but ingredient rows only add/remove. To put eggs in order he must delete and retype 32 lines.
- Result: **GAP** (G-10). Size beyond ~30/20 is low risk if not refused.

## S-10 · First day, empty app
Jake opens the app for the first time, searches "soup", and taps "Export all recipes" to see what happens.
- Walk: F-2 "No recipes yet" with "Add recipe"; search with no matches shows "No recipes match 'soup'" with "Clear search"; F-5 exports a file saying it holds 0 recipes.
- Result: **handled** (F-2, F-5).

## S-11 · A wrong or damaged file
Jake picks `holiday.jpg` by mistake, then a real export he once opened in a text editor and accidentally saved with a missing bracket halfway through recipe 17 of 42.
- Walk: F-6 shows "This file isn't a Home Cookbook export; nothing was changed" and imports all-or-nothing, so no half-import.
- Result: **handled** (F-6, §5 bad-file row).

## S-12 · At Grandma's house, away from home Wi-Fi
Visiting Grandma, Jake wants to show her the apple pie recipe. The phone can't reach the app. §9 says "recipes are unavailable unless the owner opens an export file", and he has `cookbook-2026-11-13` on his phone.
- Walk: Not reaching the app is accepted (§9, §11). But the spec doesn't say whether the export file is something a person can open and read on a phone, or only the app can load it.
- Result: **handled** for the app being unreachable; **GAP** (G-12) for reading the file.

## S-13 · Cookies, not servings
"Oat Cookies" makes 24 cookies. Jake enters servings 24 and scales to 36 for a bake sale: "1 cup oats" → "1½ cups", "1 egg" → "1½ eggs".
- Walk: F-1 accepts any whole number ≥ 1; F-3 scales and rounds to the ½ for counted items.
- Result: **handled** (F-1, F-3). (The label reads "24 servings"; acceptable.)
