# SPEC — Home Cookbook

> Written by the planner from the owner's answers, round by round. Approved before any design.
> Lines marked *(assumed)* were decided by the planner because the owner chose "decide for me".
> Status after round 3: 13/13 sections complete (SPEC COMPLETE). Critic round: gaps G-1, G-2, G-3 folded in from the owner's answers. Spec change after LLD (D-21..D-24): G-4, G-8, G-9 resolved, G-5 partly resolved (scaled grams/millilitres). G-6 resolved by D-30 (import names skipped recipes, F-6).

## 1. Goal
A private recipe box for one person's family recipes. The owner saves each recipe (title, number of servings, ingredients with amounts, and steps), finds recipes again by name or by ingredient, scales a recipe to a different number of servings with kitchen-friendly amounts, marks favourites so they appear at the top, and exports every recipe to a file that can be loaded back in, so nothing is ever lost. It runs on the owner's own computer at home and is opened from a browser on their phone or laptop while on the home Wi-Fi. No accounts, no sharing, no cloud.

## 2. Users
| User | What they want | How often |
|---|---|---|
| The owner (only user), cooking at home | Look up a family recipe on the phone in the kitchen, scaled to how many people are eating | A few times a week |
| The owner, at the laptop | Type in or tidy up family recipes; export a copy for safekeeping, or load one back in | Occasionally (batches of entry, then rarely) |

## 3. User stories
| ID | As a… | I want to… | So that… | Acceptance (checkable) |
|---|---|---|---|---|
| US-01 | owner | add a recipe with title, servings, ingredients (amount + unit + name) and numbered steps | my family recipes are saved in one place | After saving "Grandma's Apple Pie" (8 servings, 6 ingredients, 5 steps), it appears in the recipe list and reopening it shows exactly what was typed; saving a second recipe titled "pancakes" while "Pancakes" exists is refused with "You already have a recipe called 'Pancakes'" and the form stays open until the title is changed (e.g. "Pancakes (Gran's)") |
| US-02 | owner | open a recipe and read it comfortably on my phone | I can cook from it in the kitchen | On a 390px-wide phone screen the title, servings, ingredient list and steps are readable without sideways scrolling |
| US-03 | owner | edit or delete a recipe, with a short chance to undo a delete | I can fix mistakes and remove recipes I no longer want without losing one by accident | Changing "2 cups flour" to "2½ cups flour" and saving shows the new amount; if the recipe was saved on another device after the form was opened, Save shows "This recipe changed on another device" with "Reload theirs" and "Keep mine", and neither version is lost without that choice; if the recipe was deleted on another device while the form was open, the typing is kept and Save offers "Save as new" or "Discard"; a deleted recipe disappears at once and an "Undo" button shows for about 10 seconds; tapping it brings the recipe back unchanged; after that it no longer appears in the list or in search |
| US-04 | owner | search recipes by name | I find a recipe quickly | Typing "pie" lists "Grandma's Apple Pie" and "Shepherd's Pie" and not "Lemon Cake"; matching finds part of a word and ignores upper/lower case, accents and apostrophes (e.g. "shepherds" finds "Shepherd's Pie", "creme" finds "Crème Brûlée") |
| US-05 | owner | search recipes by ingredient | I can see what I can make with what I have | Typing "buttermilk" lists every recipe that has buttermilk among its ingredients and no others |
| US-06 | owner | scale a recipe to a different number of servings | I cook the right amount for the people eating | Scaling an 8-serving recipe with "2 cups flour" to 4 servings shows "1 cup flour"; amounts are rounded to ones you can measure in the same unit (e.g. ½ cup, 1½ eggs); grams and millilitres show whole numbers (e.g. "84 g", never "84⅓ g"); the saved recipe itself is unchanged |
| US-07 | owner | mark and unmark a recipe as a favourite | my go-to recipes are at the top | A favourited recipe is listed above all non-favourites in the recipe list; unmarking it returns it to its normal place |
| US-08 | owner | export all my recipes to one file | I have a copy that survives anything happening to the app | One click/tap downloads a single file containing every recipe with all its fields |
| US-09 | owner | load an export file back into the app | I can restore my recipes after a wipe or on a new computer | Exporting 42 recipes, emptying the app, then importing that file shows all 42 recipes again with every field (servings, ingredients, steps, favourites) identical; importing the same file into an app that already holds 2 of those titles adds 40, leaves the 2 existing ones untouched and says "Imported 40 recipes · skipped 2 with the same title"; an export file made by any earlier version of the app imports into the current version with every field intact |

## 4. Main flows
### F-1 · Add or edit a recipe (US-01, US-03)
1. From the recipe list, tap "Add recipe" (or "Edit" on an open recipe).
2. Fill in title, servings, ingredient lines (amount, unit, name) and steps; add or remove lines as needed.
3. Tap "Save"; the recipe opens in read view.
- Errors / edge cases: missing title or servings → the form stays open and points at the empty field; servings must be a whole number of 1 or more; an ingredient may have no amount ("salt, to taste") and is then never scaled; an amount is one number written in any common form — whole ("2"), decimal ("2.5"), fraction ("1/2"), mixed ("1 1/2") or fraction character ("½", "2½") — and is shown back kitchen-style (e.g. "1 1/2" shows as "1½") *(owner D-22; display style assumed)*; a range ("2-3", "2 to 3") or anything that isn't one number is refused: the form stays open with "Enter one amount, e.g. 2 or 2½" under the field *(wording assumed)*; leaving the form with unsaved changes asks "Discard changes?".
- Same title (owner: "No, ask for another name"): no two recipes may share a title. Saving a title that matches another recipe's → the form stays open with "You already have a recipe called 'Pancakes'. Please choose another name, e.g. 'Pancakes (Gran's)'" under the title; nothing is saved until it is changed. Titles count as the same when they match ignoring upper/lower case and spaces at the start or end *(assumed, same rule as F-6)*. Editing a recipe and keeping its own title is fine.
- Changed on another device (owner: "Warn the second save"): if the recipe was saved on another device after this form was opened, tapping "Save" does not save yet; it shows "This recipe changed on another device" with two choices: "Reload theirs" (the typed changes are dropped and the other device's version opens in read view) or "Keep mine" (this version is saved over theirs). Starring/unstarring on another device does not count as a change and keeps its star either way *(assumed)*. 
- Deleted on another device (owner D-21, gap G-9): if the recipe is deleted on another device while this form is open, the owner can keep typing; tapping "Save" shows "This recipe was deleted on another device" with two choices: "Save as new" (the typed version is saved as a new recipe and opens in read view) or "Discard" (the typed changes are dropped and the recipe list opens). If the delete was undone before Save, Save works as normal *(assumed)*. "Save as new" follows the same-title rule above *(assumed)*.

### F-2 · Find and read a recipe (US-02, US-04, US-05, US-07)
1. Open the app: the recipe list shows favourites first, then all other recipes alphabetically *(assumed: alphabetical order within each group)*.
2. Type in the search box; choose "by name" or "by ingredient" *(assumed: one search box with a name/ingredient toggle)*.
3. The list narrows as you type; tap a recipe to open it. Matching is forgiving (owner D-24): the typed text may be part of a word ("app" finds "Apple"), and upper/lower case, accents ("creme" = "crème") and apostrophes ("shepherds" = "shepherd's") are ignored; the same rule applies to names and ingredients.
4. Tap the star to favourite/unfavourite.
- Errors / edge cases: no matches → "No recipes match 'xyz'" with a "Clear search" link; empty recipe box → "No recipes yet" with an "Add recipe" button; home computer off or phone not on home Wi-Fi → the app does not open (the browser shows it can't reach it) *(owner accepted: home only)*.

### F-3 · Scale a recipe (US-06)
1. On an open recipe, change the servings number (e.g. 8 → 4).
2. All ingredient amounts update at once, shown kitchen-friendly in the same unit; a note says "Scaled from 8 servings" with a "Reset" link.
- Rounding: amounts in grams or millilitres round to the nearest whole number ("84 g", not "84⅓ g") (owner D-23); halves round up ("62.5 g" → "63 g") *(assumed)*; only g/gram(s) and ml/millilitre(s) count, other metric units such as kg or l use the fraction rule *(assumed)*. All other units round to the nearest whole or common fraction — ¼, ⅓, ½, ⅔, ¾ — in the recipe's own unit; counted items without a unit (eggs, apples) round to the nearest ½ *(assumed: exact fraction set)*. Units are never converted (no cups → tablespoons, no g → kg). An amount that would round to 0 shows as the smallest step rather than vanishing: 1 g or 1 ml; ½ for counted items without a unit (eggs, apples), matching their ½ rounding; ¼ for every other unit *(assumed)*.
- Errors / edge cases: servings below 1 or not a number are refused; ingredients without an amount stay as written; scaling is for viewing only and never changes the saved recipe.

### F-4 · Delete a recipe (US-03)
1. On an open recipe, tap "Delete".
2. The recipe disappears at once and the app returns to the list; a bar shows "'Grandma's Apple Pie' deleted · Undo" for about 10 seconds.
3. Tapping "Undo" brings the recipe back exactly as it was (including its favourite star). After the bar disappears the delete is final.
- Errors / edge cases: no "Are you sure?" question (the undo replaces it); deleting a second recipe while the bar is showing makes the first delete final and shows the bar for the second *(assumed)*.

### F-5 · Export all recipes (US-08)
1. From the menu, tap "Export all recipes".
2. A single file named like `cookbook-2026-11-13` downloads to the device in use.
- Errors / edge cases: with zero recipes, export still works and the file says it holds 0 recipes.

### F-6 · Import an export file (US-09)
1. From the menu, tap "Import recipes" and choose an export file from the device.
2. The app reads the file and shows "Imported 42 recipes" (or "Imported 40 recipes · skipped 2 with the same title").
- Recipes already in the app (owner's answer: "Add, keep, skip same title"): recipes from the file are added alongside the existing ones; nothing already in the app is changed or removed; a recipe in the file whose title matches one already in the app is skipped, not doubled.
- Skipped recipes are named (owner D-30, gap G-6): the import result lists the title of every skipped recipe and says "To restore one, delete it first, then import again", e.g. "Imported 40 recipes · skipped 2 with the same title: Lemon Cake, Shepherd's Pie. To restore one, delete it first, then import again" *(exact layout assumed)*. The skip rule itself is unchanged: an import never replaces a recipe already in the app. Titles count as the same when they match ignoring upper/lower case and spaces at the start or end *(assumed)*. The app never lets two recipes share a title (F-1), so an export restored into an empty app always brings back every recipe; nothing in a backup is dropped. If a file still holds two recipes with the same title (e.g. edited by hand), both are imported and the second gets " (2)" added to its title, and the message says so *(assumed, replaces "second skipped")*.
- Old files (owner: "Yes, always"): any export file ever made by any version of the app loads into every later version, forever, with every field intact. A future version may never refuse an older file as "too old".
- Errors / edge cases: a file that isn't a Home Cookbook export, or is damaged → "This file isn't a Home Cookbook export; nothing was changed" and no recipe is touched; importing never half-finishes (all or nothing) *(assumed)*.

## 5. Inputs and outputs (concrete examples)
| Flow | Example input | Expected output |
|---|---|---|
| F-1 Add | Title "Grandma's Apple Pie", servings 8, ingredients "2 cups flour", "1 cup butter", "6 apples", "¾ cup sugar", "1 tsp cinnamon", "salt, to taste"; 5 steps starting "Preheat oven to 200°C" | Recipe saved; list shows "Grandma's Apple Pie · 8 servings" |
| F-1 Same title | Save a new recipe titled " pancakes " while "Pancakes" exists | Not saved; "You already have a recipe called 'Pancakes'. Please choose another name, e.g. 'Pancakes (Gran's)'"; saving as "Pancakes (Gran's)" works |
| F-1 Amount forms | Ingredient amounts typed as "2", "2.5", "1/2", "1 1/2", "½" | All saved; shown as "2", "2½", "½", "1½", "½" |
| F-1 Amount range | Ingredient amount "2-3" eggs | Not saved; "Enter one amount, e.g. 2 or 2½" under the amount |
| F-1 Deleted elsewhere | Laptop has "Lemon Cake" open in edit; phone deletes "Lemon Cake"; laptop taps Save | Laptop shows "This recipe was deleted on another device" · "Save as new" (laptop version saved as "Lemon Cake") / "Discard" (back to the list, "Lemon Cake" stays deleted) |
| F-1 Changed elsewhere | Laptop has "Lemon Cake" open in edit; phone changes 220°C → 180°C and saves; laptop taps Save | Laptop shows "This recipe changed on another device" · "Reload theirs" (shows 180°C, laptop typing dropped) / "Keep mine" (laptop version saved) |
| F-2 Search by name | "pie" | "Grandma's Apple Pie", "Shepherd's Pie" |
| F-2 Search by ingredient | "buttermilk" | "Buttermilk Pancakes", "Aunt May's Scones" |
| F-2 Forgiving search | By name: "shepherds"; "creme"; "APP" | "Shepherd's Pie"; "Crème Brûlée"; "Grandma's Apple Pie" |
| F-2 Favourites | Star "Sunday Roast Chicken" | It moves to the top of the list, above "Aunt May's Scones" |
| F-3 Scale down | "Grandma's Apple Pie" 8 → 4 servings | "1 cup flour", "½ cup butter", "3 apples", "⅓ cup sugar" (¾ ÷ 2 = ⅜, rounded to ⅓), "½ tsp cinnamon", "salt, to taste" |
| F-3 Scale up | "Buttermilk Pancakes" (4 servings, "3 eggs", "⅓ cup sugar") 4 → 6 | "4½ eggs", "½ cup sugar" |
| F-3 Scale grams/ml | "Aunt May's Scones" (3 servings, "253 g flour", "150 ml buttermilk", "2 tbsp sugar") 3 → 1 | "84 g flour" (84⅓ rounded to whole grams), "50 ml buttermilk", "⅔ tbsp sugar" |
| F-4 Delete + undo | Delete "Lemon Cake", tap "Undo" within 10 seconds | "Lemon Cake" is back in the list, unchanged |
| F-5 Export | 42 saved recipes | One file `cookbook-2026-11-13` with all 42 recipes, every field included |
| F-6 Import | `cookbook-2026-11-13` (42 recipes) into an empty app | "Imported 42 recipes"; list shows all 42, favourites on top |
| F-6 Import with existing | Same file into an app already holding "Lemon Cake" and "shepherd's pie" | "Imported 40 recipes · skipped 2 with the same title"; existing "Lemon Cake" and "shepherd's pie" unchanged |
| F-6 Import old file | `cookbook-2026-04-02` made by an earlier version of the app, into the current version on a new computer | "Imported 38 recipes"; every recipe and field as it was in April |
| F-6 Import bad file | A photo `holiday.jpg` | "This file isn't a Home Cookbook export; nothing was changed" |

## 6. Data
- What is stored: recipes (title, servings, ingredient lines with amount/unit/name, ordered steps, favourite flag, created/updated dates), kept on the owner's home computer.
- Source: typed in by the owner, or loaded from an export file (US-09).
- Volume: up to a few hundred recipes (say 500 at most), each with up to ~30 ingredients and ~20 steps *(assumed)*.
- Photos: none. Recipes are text only (owner: "No photos").
- Retention: kept until the owner deletes them; a deleted recipe can be undone for about 10 seconds, then it is gone.

## 7. Screens (UI projects)
| Screen | Purpose | Key elements | Wireframe |
|---|---|---|---|
| Recipe list | Browse and search | Search box with name/ingredient toggle, favourites first, star per recipe, "Add recipe", menu with "Export all recipes" and "Import recipes", "deleted · Undo" bar | docs/wireframes/recipe-list.png |
| Recipe view | Cook from a recipe | Title, star, servings stepper (scaling) with "Scaled from 8 servings · Reset", ingredient list, numbered steps, Edit, Delete | docs/wireframes/recipe-view.png |
| Recipe edit | Add or change a recipe | Title, servings, ingredient rows (amount, unit, name, add/remove), step rows (add/remove/reorder), Save, Cancel, "already have a recipe called…" title error, "This recipe changed on another device" dialog (Reload theirs / Keep mine), "This recipe was deleted on another device" dialog (Save as new / Discard), "Enter one amount" amount error | docs/wireframes/recipe-edit.png |

## 8. Integrations
- None. No external services, accounts or keys.

## 9. Non-functional
- Scale / load: one user, usually one device at a time; up to ~500 recipes *(assumed)*. If phone and laptop change the same recipe at once, the second save is warned "This recipe changed on another device" and chooses "Reload theirs" or "Keep mine" (owner: "Warn the second save"); no change is overwritten silently.
- Compatibility: every export file the app has ever made must load into every later version, forever (owner: "Yes, always").
- Latency: search results update while typing; any screen opens in under 1 second *(assumed)*.
- Offline: not supported. The app works only while the home computer is on and the phone/laptop is on the home Wi-Fi (owner's answer: "only at home"). Away from home, recipes are unavailable unless the owner opens an export file.
- Security & privacy: no accounts (owner's choice); recipes never leave the home. No password screen: anyone on the home Wi-Fi can open, change, delete, export and import recipes (owner: "Yes, anyone at home"). Not reachable from outside the home network.
- Cost limits: free to run; no paid services *(assumed from "runs on my own computer")*.
- Platforms/devices: phone browser and laptop browser, at home; mobile-first layout, desktop layout too.

## 10. Constraints
- Stack preferences or bans: none stated.
- Deadline: none (owner: "No deadline").
- Deployment target: the owner's own computer at home, reachable from phone and laptop on the home Wi-Fi.
- Budget: none beyond the owner's own computer.

## 11. Non-goals (explicitly out)
- No accounts, logins or multiple users (owner said "just for me").
- No cloud hosting, online sync or use away from home; it runs on the owner's computer only.
- No offline copy on the phone (owner chose "only at home").
- No sharing recipes with other people (links, social, email).
- No meal planning, shopping lists or nutrition information *(assumed: likeliest scope creep, owner can promote)*.
- No unit conversion between systems (cups to grams) or within a system (cups to tablespoons) *(assumed; owner chose "same unit")*.
- No importing from other recipe apps or websites; import reads only this app's own export file *(assumed)*.
- No photos or pictures on recipes (owner: "No photos").
- No passwords or per-person access on the home Wi-Fi (owner: "anyone at home").

## 12. Definition of done
- [ ] On the phone, I can open the app, add "Grandma's Apple Pie", and see it in the list on the laptop too.
- [ ] Searching "pie" by name and "buttermilk" by ingredient shows exactly the matching recipes.
- [ ] Changing an 8-serving recipe to 4 servings shows kitchen-friendly amounts (½ cup, not 0.375 cup), and the saved recipe is unchanged afterwards.
- [ ] A starred recipe sits at the top of the list.
- [ ] Deleting a recipe and tapping "Undo" straight away brings it back.
- [ ] "Export all recipes" gives me one file; loading that file into an emptied app brings every recipe back.

## 13. Data safety
- Backup: the owner exports all recipes to a file (US-08) whenever they choose; that file can be loaded back into the app to restore every recipe (US-09). *(owner: "App can load it back in")* Every export loads into every later version of the app, forever (owner: "Yes, always"), and because titles are unique a restore never drops a recipe (owner: "No, ask for another name").
- Two devices editing at once: the second save is warned and chooses; a change is never overwritten without the owner knowing (owner: "Warn the second save").
- Second device: there is one copy, on the home computer; the phone and laptop are just windows onto it and always show the same recipes. *(owner: "Yes, only at home")*
- If the home computer is wiped or the app reinstalled, the owner loses: every recipe added or changed since the last export; everything up to that export comes back by importing the file. Losing the phone or laptop loses nothing.
- Undo: a deleted recipe disappears at once with an "Undo" button for about 10 seconds; after that it is gone for good (restorable only from an earlier export). *(owner: "Undo for ~10 seconds")*
- Consequence line for the spec card: "Backup is manual: anything added since your last export is lost if the home computer dies."

## Open questions
- None.
- Critic gaps resolved after LLD: G-4 amount input (D-22, F-1), G-8 search matching (D-24, F-2), G-9 edit of a recipe deleted elsewhere (D-21, F-1), G-6 import over an existing title (D-30, F-6: skipped recipes are named with "To restore one, delete it first, then import again"). G-5 partly resolved: scaled grams/millilitres show whole numbers (D-23, F-3); the rest of G-5 stays as written in F-3.
