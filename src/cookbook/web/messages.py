"""Every user-facing text, in one place (LLD §6.4)."""

from typing import Final

from cookbook.services.backup.service import ImportResult

OUTSIDE_HOME: Final = "Home Cookbook only answers inside the home"
OTHER_WEBSITE: Final = "Home Cookbook only accepts requests made from its own pages"
RECIPE_GONE: Final = "That recipe isn't here any more"
PAGE_GONE: Final = "That page isn't here"
SERVER_ERROR: Final = "Something went wrong on the home computer. Please try again"
BAD_REQUEST: Final = "That request could not be read"
NOT_AN_EXPORT: Final = "This file isn't a Home Cookbook export; nothing was changed"
NEWER_VERSION: Final = (
    "This file was made by a newer version of Home Cookbook. "
    "Update the app to load it; nothing was changed"
)
IMPORT_INTERRUPTED: Final = (
    "Something changed while importing; nothing was changed, please try again"
)
CHANGED_ELSEWHERE: Final = "This recipe changed on another device"
DELETED_ELSEWHERE: Final = "This recipe was deleted on another device"
DISCARD_CHANGES: Final = "Discard changes?"

RESTORED_RENAMED: Final = "'{title}' is back as '{renamed}' because another recipe now has its name"
UNDO_EXPIRED: Final = "Too late to undo; '{title}' is gone"

# Texts the browser shows (undo.js, api.js, edit.js, list.js, view.js);
# base.html renders them into <body data-texts>.
# "{name}" placeholders are filled in by api.js uiText().
UI_TEXTS: Final = {
    "undo": "Undo",
    "deleted": "'{title}' deleted",
    "restored": "'{title}' is back",
    "restored_renamed": RESTORED_RENAMED,
    "undo_expired": UNDO_EXPIRED,
    "undo_failed": "Could not undo",
    "network": "Could not reach the home computer. Please try again",
    "discard_changes": DISCARD_CHANGES,
    "changed_elsewhere": CHANGED_ELSEWHERE,
    "deleted_elsewhere": DELETED_ELSEWHERE,
    "reload_theirs": "Reload theirs",
    "keep_mine": "Keep mine",
    "save_as_new": "Save as new",
    "discard_mine": "Discard my changes",
    "search_failed": "Could not search. Please try again",
    "add_favourite": "Add to favourites",
    "remove_favourite": "Remove from favourites",
    "favourite_failed": "Could not change the star. Please try again",
    "scaled_from": "Scaled from {n} servings",
    "scaled_from_one": "Scaled from {n} serving",
    "scaled_to": "Amounts now for {n} servings",
    "scaled_to_one": "Amounts now for {n} serving",
}

FIELD_MESSAGES: Final = {
    "required": "Please fill this in",
    "not_whole": "Use a whole number of 1 or more",
    "bad_amount": "Enter one amount, e.g. 2 or 2½",
    "range": "Enter one amount, e.g. 2 or 2½",
    "unclear_amount": "This amount is unclear; write e.g. 1000 for a thousand, or 1,0 for one",
    "too_long": "This is too long; please shorten it",
}


def field_message(code: str) -> str:
    return FIELD_MESSAGES.get(code, FIELD_MESSAGES["required"])


def duplicate_title(existing: str) -> str:
    return (
        f"You already have a recipe called '{existing}'. "
        f"Please choose another name, e.g. '{existing} (Gran's)'"
    )


def undo_expired(title: str) -> str:
    return UNDO_EXPIRED.format(title=title)


def restored_renamed(title: str, renamed: str) -> str:
    return RESTORED_RENAMED.format(title=title, renamed=renamed)


def imported(result: ImportResult) -> str:
    noun = "recipe" if result.imported == 1 else "recipes"
    text = f"Imported {result.imported} {noun}"
    if result.skipped:
        titles = ", ".join(result.skipped_titles)
        text += f" · skipped {result.skipped} with the same title: {titles}"
    if result.renamed:
        text += f" · renamed {result.renamed} with a repeated title"
    if result.skipped:
        text += ". To restore one, delete it first, then import again"
    return text
