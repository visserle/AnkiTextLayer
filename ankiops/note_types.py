"""Ensure all AnkiOps note types exist in Anki and are up to date with our templates."""

import logging
from importlib import resources

from ankiops.anki_client import invoke
from ankiops.config import NOTE_TYPES

logger = logging.getLogger(__name__)


def _load_template(filename: str) -> str:
    """Read a card template file from the card_templates directory."""
    return (
        resources.files("ankiops.card_templates")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )


def _get_card_templates(model_name: str) -> list[dict[str, str]]:
    """Get card templates for a model.

    Returns a list of card template dicts with Name, Front, and Back keys.
    Most models have one card, but AnkiOpsReversed has two (forward and reverse).
    """
    front = _load_template(f"{model_name}Front.template.anki")
    back = _load_template(f"{model_name}Back.template.anki")

    templates = [{"Name": "Card 1", "Front": front, "Back": back}]

    # AnkiOpsReversed has a second card for the reverse direction
    if model_name == "AnkiOpsReversed":
        front2 = _load_template(f"{model_name}Front2.template.anki")
        back2 = _load_template(f"{model_name}Back2.template.anki")
        templates.append({"Name": "Card 2", "Front": front2, "Back": back2})

    return templates


def _create_model(model_name: str, is_cloze: bool) -> None:
    """Create a note type in Anki from the template files."""
    cfg = NOTE_TYPES[model_name]
    fields = [field_name for field_name, _, _ in cfg["field_mappings"]]

    css = _load_template("Styling.css")
    card_templates = _get_card_templates(model_name)

    invoke(
        "createModel",
        modelName=model_name,
        inOrderFields=fields,
        css=css,
        isCloze=is_cloze,
        cardTemplates=card_templates,
    )
    logger.info(f"Created note type '{model_name}' in Anki")


def _is_model_up_to_date(model_name: str) -> bool:
    """Check if a model's templates and styling match our template files."""
    css = _load_template("Styling.css")
    expected_templates = _get_card_templates(model_name)

    # Get current model info
    current_styling = invoke("modelStyling", modelName=model_name)
    current_templates = invoke("modelTemplates", modelName=model_name)

    # Compare styling
    if current_styling.get("css", "").strip() != css.strip():
        return False

    # Check if number of templates matches
    if len(current_templates) != len(expected_templates):
        return False

    # Compare each template (AnkiConnect returns dict with card names as keys)
    current_templates_list = list(current_templates.values())
    for i, expected in enumerate(expected_templates):
        if i >= len(current_templates_list):
            return False

        current = current_templates_list[i]
        current_front = current.get("Front", "").strip()
        current_back = current.get("Back", "").strip()
        expected_front = expected["Front"].strip()
        expected_back = expected["Back"].strip()

        if current_front != expected_front or current_back != expected_back:
            return False

    return True


def _update_model(model_name: str) -> None:
    """Update an existing note type's card templates and styling."""
    css = _load_template("Styling.css")
    expected_templates = _get_card_templates(model_name)

    # Update styling
    invoke("updateModelStyling", model={"name": model_name, "css": css})

    # Update templates - match expected templates with current template names
    current_templates = invoke("modelTemplates", modelName=model_name)
    current_template_names = list(current_templates.keys())

    # Build templates dict using actual Anki template names
    templates_dict = {}
    for i, expected in enumerate(expected_templates):
        if i < len(current_template_names):
            template_name = current_template_names[i]
            templates_dict[template_name] = {
                "Front": expected["Front"],
                "Back": expected["Back"],
            }

    invoke(
        "updateModelTemplates",
        model={"name": model_name, "templates": templates_dict},
    )
    logger.info(f"Updated note type '{model_name}' in Anki")


def ensure_note_types() -> None:
    """Ensure all required note types exist in Anki and are up to date."""
    existing = set(invoke("modelNames"))

    if "AnkiOpsQA" not in existing:
        _create_model("AnkiOpsQA", is_cloze=False)
    elif not _is_model_up_to_date("AnkiOpsQA"):
        _update_model("AnkiOpsQA")

    if "AnkiOpsReversed" not in existing:
        _create_model("AnkiOpsReversed", is_cloze=False)
    elif not _is_model_up_to_date("AnkiOpsReversed"):
        _update_model("AnkiOpsReversed")

    if "AnkiOpsCloze" not in existing:
        _create_model("AnkiOpsCloze", is_cloze=True)
    elif not _is_model_up_to_date("AnkiOpsCloze"):
        _update_model("AnkiOpsCloze")

    if "AnkiOpsInput" not in existing:
        _create_model("AnkiOpsInput", is_cloze=False)
    elif not _is_model_up_to_date("AnkiOpsInput"):
        _update_model("AnkiOpsInput")

    if "AnkiOpsChoice" not in existing:
        _create_model("AnkiOpsChoice", is_cloze=False)
    elif not _is_model_up_to_date("AnkiOpsChoice"):
        _update_model("AnkiOpsChoice")
