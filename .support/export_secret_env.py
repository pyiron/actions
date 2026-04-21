"""Export selected GitHub Actions secrets into later-step environment variables."""

from __future__ import annotations

import json
import os
import re
import sys
import uuid

NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def workflow_escape(value: str) -> str:
    """Escape text embedded in a GitHub workflow command."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def fail(message: str) -> None:
    print(f"::error::{workflow_escape(message)}", file=sys.stderr)
    raise SystemExit(1)


def parse_secret_env_map(raw_map: str) -> list[tuple[str, str]]:
    """Parse SECRET_NAME or ENV_NAME=SECRET_NAME mapping lines."""
    mappings: list[tuple[str, str]] = []
    seen_env_names: set[str] = set()

    for line_number, raw_line in enumerate(raw_map.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if "=" in line:
            env_name, secret_name = (part.strip() for part in line.split("=", 1))
        else:
            env_name = secret_name = line

        if not env_name or not secret_name:
            fail(f"Invalid secret env mapping on line {line_number}.")
        if not NAME_PATTERN.fullmatch(env_name):
            fail(
                f"Invalid environment variable name {env_name!r} on line {line_number}."
            )
        if not NAME_PATTERN.fullmatch(secret_name):
            fail(f"Invalid secret name {secret_name!r} on line {line_number}.")
        if env_name in seen_env_names:
            fail(f"Duplicate environment variable mapping for {env_name!r}.")

        seen_env_names.add(env_name)
        mappings.append((env_name, secret_name))

    return mappings


def load_secrets() -> dict[str, str]:
    """Load the full secret object supplied only to the trusted export step."""
    raw_secrets = os.environ.get("PYIRON_ALL_SECRETS_JSON")
    if not raw_secrets:
        fail("PYIRON_ALL_SECRETS_JSON is required when exporting selected secrets.")

    try:
        secrets = json.loads(raw_secrets)
    except json.JSONDecodeError as exc:
        fail(f"Failed to parse PYIRON_ALL_SECRETS_JSON: {exc}")

    if not isinstance(secrets, dict):
        fail("PYIRON_ALL_SECRETS_JSON must decode to a JSON object.")

    return {str(name): str(value) for name, value in secrets.items()}


def choose_github_env_delimiter(value: str) -> str:
    """Choose a delimiter that is not present as a complete value line."""
    value_lines = set(value.splitlines())
    while True:
        delimiter = f"PYIRON_SECRET_{uuid.uuid4().hex}"
        if delimiter not in value_lines:
            return delimiter


def append_github_env(env_name: str, value: str) -> None:
    """Append one environment variable using GitHub's multiline-safe format."""
    github_env = os.environ.get("GITHUB_ENV")
    if not github_env:
        fail("GITHUB_ENV is not set.")

    delimiter = choose_github_env_delimiter(value)
    with open(github_env, "a", encoding="utf-8") as env_file:
        env_file.write(f"{env_name}<<{delimiter}\n{value}\n{delimiter}\n")


def main() -> int:
    mappings = parse_secret_env_map(os.environ.get("PYIRON_SECRET_ENV_MAP", ""))
    if not mappings:
        return 0

    secrets = load_secrets()
    missing = [secret_name for _, secret_name in mappings if secret_name not in secrets]
    if missing:
        fail("Requested secret(s) are not available: " + ", ".join(sorted(missing)))

    for env_name, secret_name in mappings:
        value = secrets[secret_name]
        if value:
            print(f"::add-mask::{workflow_escape(value)}")
        append_github_env(env_name, value)

    print(f"Exported {len(mappings)} selected secret environment variable(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
