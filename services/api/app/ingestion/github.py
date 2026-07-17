import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from app.domain.repositories import InvalidRepositoryError, RepositoryAcquisitionError

_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def normalize_github_url(value: str) -> tuple[str, str]:
    parsed = urlparse(value.strip())
    parts = [part for part in parsed.path.removesuffix(".git").split("/") if part]
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"github.com", "www.github.com"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or len(parts) != 2
        or not all(_SLUG_PATTERN.fullmatch(part) for part in parts)
        or parts[0] in {".", ".."}
        or parts[1] in {".", ".."}
    ):
        raise InvalidRepositoryError(
            "Enter a public GitHub URL in the form https://github.com/owner/repository."
        )
    owner, repository = parts
    return f"https://github.com/{owner}/{repository}.git", f"{owner}/{repository}"


def clone_public_repository(repository_url: str, destination: Path, timeout_seconds: int) -> str:
    normalized_url, repository_name = normalize_github_url(repository_url)
    environment = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    try:
        subprocess.run(
            [
                "git",
                "-c",
                "credential.helper=",
                "clone",
                "--depth=1",
                "--single-branch",
                "--no-tags",
                "--",
                normalized_url,
                str(destination),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=environment,
        )
    except FileNotFoundError as error:
        raise RepositoryAcquisitionError("Git is not installed on the API host.") from error
    except subprocess.TimeoutExpired as error:
        raise RepositoryAcquisitionError("Repository cloning exceeded the configured timeout.") from error
    except subprocess.CalledProcessError as error:
        raise RepositoryAcquisitionError(
            "The repository could not be cloned. Confirm that it exists and is public."
        ) from error
    return repository_name

