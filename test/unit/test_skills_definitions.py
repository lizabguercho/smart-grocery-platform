"""Tests for the SKILL.md playbooks shipped with the platform.

These guard the skill files themselves: a malformed frontmatter block or a
renamed directory would otherwise only surface as the model quietly losing
guidance at runtime.
"""

from __future__ import annotations

import re

import pytest
from pydantic_ai_skills import SkillsToolset, discover_skills

from src.agent_platform.chat_service.skill_service import SCRIPT_EXECUTION_TOOL
from src.agent_platform.config import default_skills_directory

# The name rule enforced by pydantic-ai-skills.
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
EXPECTED_SKILLS = {"grocery-database", "price-comparison", "chain-competitiveness"}
GROCERY_TOOL_NAMES = {
    "find_products",
    "compare_product_prices",
    "cheapest_chain_summary",
    "category_price_summary",
    "database_overview",
}


@pytest.fixture
def skills():
    return discover_skills(default_skills_directory())


def test_the_expected_skills_are_discovered(skills) -> None:
    assert {skill.name for skill in skills} == EXPECTED_SKILLS


def test_skill_names_satisfy_the_package_rules(skills) -> None:
    for skill in skills:
        assert SKILL_NAME_PATTERN.match(skill.name), skill.name
        assert len(skill.name) <= MAX_NAME_LENGTH


def test_skill_descriptions_are_present_and_bounded(skills) -> None:
    for skill in skills:
        assert skill.description.strip()
        assert len(skill.description) <= MAX_DESCRIPTION_LENGTH


def test_skills_have_content(skills) -> None:
    for skill in skills:
        assert skill.content.strip()


def test_the_database_skill_ships_its_reference(skills) -> None:
    by_name = {skill.name: skill for skill in skills}

    resources = [resource.name for resource in by_name["grocery-database"].resources]
    assert "REFERENCE.md" in resources


def test_skills_only_reference_tools_that_exist(skills) -> None:
    """A playbook naming a tool that does not exist would misdirect the model."""

    referenced = set()
    for skill in skills:
        for tool_name in GROCERY_TOOL_NAMES:
            if tool_name in skill.content:
                referenced.add(tool_name)

    assert referenced == GROCERY_TOOL_NAMES


def test_no_skill_ships_an_executable_script(skills) -> None:
    """Script execution is disabled, so a script here would be dead weight."""

    for skill in skills:
        assert skill.scripts == []


def test_toolset_excludes_script_execution() -> None:
    toolset = SkillsToolset(
        directories=[default_skills_directory()],
        exclude_tools=[SCRIPT_EXECUTION_TOOL],
    )

    assert SCRIPT_EXECUTION_TOOL not in toolset.tools
    assert "load_skill" in toolset.tools
