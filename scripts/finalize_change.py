from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
PREPARED_MESSAGE_PATH = ROOT / ".git" / "COMPETITORIQ_COMMIT_MESSAGE"

PROTECTED_BRANCHES = {"main", "master"}
ALLOWED_CHANGELOG_CATEGORIES = {
    "Added",
    "Changed",
    "Fixed",
    "Removed",
    "Security",
}

FORBIDDEN_EXACT_PATHS = {
    ".env",
    ".env.local",
    ".env.production",
    ".venv",
}

FORBIDDEN_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}

FORBIDDEN_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}


class FinalizationError(RuntimeError):
    """Raised when the finalization workflow cannot continue safely."""


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def run(
    command: Sequence[str],
    *,
    check: bool = True,
    capture_output: bool = True,
) -> CommandResult:
    completed = subprocess.run(
        list(command),
        cwd=ROOT,
        text=True,
        capture_output=capture_output,
        check=False,
    )

    result = CommandResult(
        command=tuple(command),
        returncode=completed.returncode,
        stdout=completed.stdout.strip() if completed.stdout else "",
        stderr=completed.stderr.strip() if completed.stderr else "",
    )

    if check and result.returncode != 0:
        rendered_command = " ".join(result.command)
        details = result.stderr or result.stdout or "No command output."
        raise FinalizationError(
            f"Command failed with exit code {result.returncode}:\n"
            f"{rendered_command}\n\n{details}"
        )

    return result


def git(*arguments: str, check: bool = True) -> CommandResult:
    return run(("git", *arguments), check=check)


def ensure_repository_root() -> None:
    result = git("rev-parse", "--show-toplevel")
    actual_root = Path(result.stdout).resolve()

    if actual_root != ROOT:
        raise FinalizationError(
            f"Expected repository root {ROOT}, but Git reported {actual_root}."
        )


def repository_has_commits() -> bool:
    result = git(
        "rev-parse",
        "--verify",
        "HEAD",
        check=False,
    )
    return result.returncode == 0


def current_branch() -> str:
    branch = git("branch", "--show-current").stdout.strip()

    if not branch:
        raise FinalizationError(
            "The repository is in detached HEAD state. "
            "Switch to a named feature branch before finalizing."
        )

    return branch


def ensure_non_protected_branch(action: str) -> str:
    branch = current_branch()

    if branch in PROTECTED_BRANCHES:
        raise FinalizationError(
            f"Refusing to {action} from protected branch '{branch}'. "
            "Create or switch to a feature branch first."
        )

    return branch


def changed_paths() -> list[str]:
    result = git(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )

    paths: list[str] = []

    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue

        path_text = line[3:]

        if " -> " in path_text:
            path_text = path_text.split(" -> ", maxsplit=1)[1]

        paths.append(path_text.strip())

    return sorted(set(paths))


def is_forbidden_path(path_text: str) -> bool:
    path = Path(path_text)
    normalized = path.as_posix()

    if normalized in FORBIDDEN_EXACT_PATHS:
        return True

    if any(part in FORBIDDEN_PATH_PARTS for part in path.parts):
        return True

    return path.suffix.lower() in FORBIDDEN_SUFFIXES


def ensure_no_forbidden_paths(paths: Sequence[str]) -> None:
    forbidden = sorted(path for path in paths if is_forbidden_path(path))

    if forbidden:
        formatted = "\n".join(f"- {path}" for path in forbidden)
        raise FinalizationError(
            "Refusing to continue because potentially sensitive or generated "
            f"paths are present:\n{formatted}"
        )


def infer_base_branch() -> str:
    if not repository_has_commits():
        return "No commits yet."

    for candidate in ("origin/main", "main", "origin/master", "master"):
        result = git(
            "rev-parse",
            "--verify",
            "--quiet",
            candidate,
            check=False,
        )
        if result.returncode == 0:
            return candidate

    return "HEAD"


def print_inspection() -> None:
    branch = current_branch()
    base_branch = infer_base_branch()
    paths = changed_paths()
    has_commits = repository_has_commits()

    status = git(
        "status",
        "--short",
        "--branch",
        "--untracked-files=all",
    ).stdout

    staged_stat = git("diff", "--cached", "--stat").stdout

    if has_commits:
        diff_stat = git("diff", "--stat", "HEAD").stdout
        recent_commits = git(
            "log",
            "--oneline",
            "--decorate",
            "-5",
        ).stdout
    else:
        diff_stat = (
            "No commits yet. All current repository files are part of the "
            "initial working tree."
        )
        recent_commits = "No commits found."

    report = {
        "branch": branch,
        "base_branch": base_branch,
        "has_commits": has_commits,
        "protected_branch": branch in PROTECTED_BRANCHES,
        "changed_file_count": len(paths),
        "changed_files": paths,
        "forbidden_paths": [path for path in paths if is_forbidden_path(path)],
    }

    print("Repository inspection")
    print("=====================")
    print(json.dumps(report, indent=2))

    print("\nGit status")
    print("----------")
    print(status or "Working tree clean.")

    print("\nUnstaged and working-tree diff stat")
    print("-----------------------------------")
    print(diff_stat or "No unstaged or working-tree diff.")

    print("\nStaged diff stat")
    print("----------------")
    print(staged_stat or "No staged diff.")

    print("\nRecent commits")
    print("--------------")
    print(recent_commits)


def run_verification() -> None:
    commands = (
        ("uv", "run", "ruff", "check", ".", "--fix"),
        ("uv", "run", "ruff", "format", "."),
        ("uv", "run", "pytest"),
    )

    for command in commands:
        print(f"\n$ {' '.join(command)}")
        result = run(command)

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr, file=sys.stderr)

    print("\nVerification completed successfully.")


def require_changelog() -> str:
    if not CHANGELOG_PATH.exists():
        raise FinalizationError(f"{CHANGELOG_PATH.relative_to(ROOT)} does not exist.")

    return CHANGELOG_PATH.read_text(encoding="utf-8")


def validate_changelog_structure(content: str) -> None:
    if "## [Unreleased]" not in content:
        raise FinalizationError(
            "CHANGELOG.md must contain an '## [Unreleased]' section."
        )

    for category in ALLOWED_CHANGELOG_CATEGORIES:
        heading = f"### {category}"
        if heading not in content:
            raise FinalizationError(
                f"CHANGELOG.md is missing the required heading '{heading}'."
            )


def normalize_changelog_message(message: str) -> str:
    stripped = message.strip()

    if not stripped:
        raise FinalizationError("The changelog message cannot be empty.")

    if "\n" in stripped:
        raise FinalizationError("The changelog message must fit on one line.")

    normalized = " ".join(stripped.split())
    normalized = normalized.removesuffix(".")

    if not normalized:
        raise FinalizationError("The changelog message cannot be empty.")

    if len(normalized) > 180:
        raise FinalizationError("The changelog message must not exceed 180 characters.")

    return normalized


def add_changelog_entry(category: str, message: str) -> None:
    if category not in ALLOWED_CHANGELOG_CATEGORIES:
        allowed = ", ".join(sorted(ALLOWED_CHANGELOG_CATEGORIES))
        raise FinalizationError(
            f"Invalid changelog category '{category}'. Allowed: {allowed}."
        )

    content = require_changelog()
    validate_changelog_structure(content)

    normalized_message = normalize_changelog_message(message)
    entry = f"- {normalized_message}"
    heading = f"### {category}"

    category_start = content.index(heading)
    next_heading_match = re.search(
        r"\n### |\n## ",
        content[category_start + len(heading) :],
    )

    if next_heading_match is None:
        category_end = len(content)
    else:
        category_end = category_start + len(heading) + next_heading_match.start()

    category_block = content[category_start:category_end]

    if entry in category_block:
        print("The changelog entry already exists; no change was made.")
        return

    insertion_point = category_start + len(heading)
    updated = content[:insertion_point] + f"\n\n{entry}" + content[insertion_point:]

    CHANGELOG_PATH.write_text(updated, encoding="utf-8")
    print(f"Added changelog entry under {heading}:")
    print(entry)


def unreleased_entries(content: str) -> list[tuple[str, str]]:
    validate_changelog_structure(content)

    unreleased_start = content.index("## [Unreleased]")
    next_release_match = re.search(
        r"\n## \[(?!Unreleased\])",
        content[unreleased_start + len("## [Unreleased]") :],
    )

    if next_release_match is None:
        unreleased_end = len(content)
    else:
        unreleased_end = (
            unreleased_start + len("## [Unreleased]") + next_release_match.start()
        )

    block = content[unreleased_start:unreleased_end]
    category: str | None = None
    entries: list[tuple[str, str]] = []

    for line in block.splitlines():
        if line.startswith("### "):
            candidate = line.removeprefix("### ").strip()
            category = candidate if candidate in ALLOWED_CHANGELOG_CATEGORIES else None
            continue

        if category and line.startswith("- "):
            entries.append((category, line.removeprefix("- ").strip()))

    return entries


def slug_to_scope(branch: str) -> str:
    raw = branch.split("/", maxsplit=1)[-1]
    tokens = [
        token for token in re.split(r"[-_]+", raw) if token and not token.isdigit()
    ]

    if not tokens:
        return "project"

    ignored = {
        "add",
        "added",
        "change",
        "changed",
        "create",
        "created",
        "fix",
        "fixed",
        "implement",
        "implemented",
        "update",
        "updated",
    }

    meaningful = [token for token in tokens if token.lower() not in ignored]
    selected = meaningful or tokens
    return "-".join(selected[:3]).lower()


def category_to_commit_type(category: str) -> str:
    mapping = {
        "Added": "feat",
        "Changed": "refactor",
        "Fixed": "fix",
        "Removed": "refactor",
        "Security": "fix",
    }
    return mapping[category]


def changelog_to_subject(message: str) -> str:
    prefixes = (
        "Added ",
        "Changed ",
        "Fixed ",
        "Removed ",
        "Improved ",
        "Updated ",
    )

    subject = message.strip()

    for prefix in prefixes:
        if subject.startswith(prefix):
            subject = subject[len(prefix) :]
            break

    if not subject:
        raise FinalizationError(
            "Could not derive a commit subject from the changelog entry."
        )

    return subject[0].lower() + subject[1:]


def prepare_commit_message() -> None:
    ensure_non_protected_branch("prepare a commit")
    content = require_changelog()
    entries = unreleased_entries(content)

    if not entries:
        raise FinalizationError("No entry exists in the Unreleased changelog section.")

    category, message = entries[-1]
    branch = current_branch()
    commit_type = category_to_commit_type(category)
    scope = slug_to_scope(branch)
    subject = changelog_to_subject(message)

    first_line = f"{commit_type}({scope}): {subject}"

    if len(first_line) > 100:
        first_line = f"{commit_type}: {subject}"

    if len(first_line) > 100:
        raise FinalizationError(
            "The generated commit message exceeds 100 characters. "
            "Use a shorter changelog entry."
        )

    prepared_message = f"{first_line}\n\nChangelog: {category} - {message}\n"

    PREPARED_MESSAGE_PATH.write_text(
        prepared_message,
        encoding="utf-8",
    )

    print("Prepared commit message:")
    print("------------------------")
    print(prepared_message)


def final_check() -> None:
    branch = ensure_non_protected_branch("finalize changes")
    paths = changed_paths()

    if not paths:
        raise FinalizationError("There are no working-tree changes to finalize.")

    ensure_no_forbidden_paths(paths)

    changelog_content = require_changelog()
    validate_changelog_structure(changelog_content)

    if not unreleased_entries(changelog_content):
        raise FinalizationError("The Unreleased changelog section has no entries.")

    run_verification()

    remaining_paths = changed_paths()
    ensure_no_forbidden_paths(remaining_paths)

    print("\nFinal checks passed.")
    print(f"Branch: {branch}")
    print(f"Changed files: {len(remaining_paths)}")


def commit_changes() -> None:
    branch = ensure_non_protected_branch("commit")
    paths = changed_paths()

    if not paths:
        raise FinalizationError("There are no changes to commit.")

    ensure_no_forbidden_paths(paths)

    if not PREPARED_MESSAGE_PATH.exists():
        raise FinalizationError(
            "No prepared commit message exists. "
            "Run 'prepare-message' before committing."
        )

    message = PREPARED_MESSAGE_PATH.read_text(encoding="utf-8").strip()

    if not message:
        raise FinalizationError("The prepared commit message is empty.")

    git("add", "--all")

    staged_paths_result = git(
        "diff",
        "--cached",
        "--name-only",
        "--diff-filter=ACMR",
    )
    staged_paths = [
        line.strip() for line in staged_paths_result.stdout.splitlines() if line.strip()
    ]

    ensure_no_forbidden_paths(staged_paths)

    if not staged_paths:
        raise FinalizationError("No eligible files were staged for commit.")

    git("commit", "--file", str(PREPARED_MESSAGE_PATH))

    commit_hash = git("rev-parse", "--short", "HEAD").stdout
    print(f"Created commit {commit_hash} on branch '{branch}'.")


def push_branch() -> None:
    branch = ensure_non_protected_branch("push")

    if changed_paths():
        raise FinalizationError(
            "Refusing to push while the working tree contains changes."
        )

    upstream = git(
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
        check=False,
    )

    if upstream.returncode == 0:
        git("push")
        print(f"Pushed branch '{branch}' to its configured upstream.")
        return

    git("push", "--set-upstream", "origin", branch)
    print(f"Pushed branch '{branch}' to 'origin/{branch}'.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Finalize CompetitorIQ repository changes safely."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "inspect",
        help="Print deterministic repository state information.",
    )

    subparsers.add_parser(
        "verify",
        help="Run Ruff fixes, formatting, and tests.",
    )

    changelog_parser = subparsers.add_parser(
        "changelog",
        help="Insert a validated entry into CHANGELOG.md.",
    )
    changelog_parser.add_argument(
        "--category",
        required=True,
        choices=sorted(ALLOWED_CHANGELOG_CATEGORIES),
    )
    changelog_parser.add_argument(
        "--message",
        required=True,
    )

    subparsers.add_parser(
        "final-check",
        help="Run all deterministic readiness checks.",
    )

    subparsers.add_parser(
        "prepare-message",
        help="Generate the commit message deterministically.",
    )

    subparsers.add_parser(
        "commit",
        help="Commit after explicit user approval.",
    )

    subparsers.add_parser(
        "push",
        help="Push the current non-protected branch after approval.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()

    try:
        ensure_repository_root()

        if arguments.command == "inspect":
            print_inspection()
        elif arguments.command == "verify":
            run_verification()
        elif arguments.command == "changelog":
            add_changelog_entry(
                category=arguments.category,
                message=arguments.message,
            )
        elif arguments.command == "final-check":
            final_check()
        elif arguments.command == "prepare-message":
            prepare_commit_message()
        elif arguments.command == "commit":
            commit_changes()
        elif arguments.command == "push":
            push_branch()
        else:
            parser.error(f"Unsupported command: {arguments.command}")

    except FinalizationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
