# External Libraries
import json
import os
from pathlib import Path

from dotenv import load_dotenv


# Project Paths
CORE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CORE_DIR.parent.parent

ENV_FILE = PROJECT_ROOT / ".env"

# Load Environment Variables
load_dotenv(ENV_FILE)


def load_rules(scheme: str) -> dict:
    """
    Load rules for the requested government scheme.

    The scheme name must match the JSON filename.
    Example:
        load_rules("pm_kisan")
        -> app/core/pm_kisan.json
    """

    if not scheme:
        raise ValueError("Scheme name cannot be empty.")

    rules_file = CORE_DIR / f"{scheme}.json"

    if not rules_file.exists():
        raise FileNotFoundError(
            f"Rules file not found for scheme '{scheme}': {rules_file}"
        )

    try:
        with rules_file.open("r", encoding="utf-8") as file:
            rules = json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in rules file: {error}"
        ) from error

    if not isinstance(rules, dict):
        raise ValueError(
            "Rules file must contain a JSON object."
        )

    return rules


def get_env(
    key: str,
    default: str | None = None
) -> str | None:
    """
    Safely retrieve an environment variable.
    """

    return os.getenv(key, default)