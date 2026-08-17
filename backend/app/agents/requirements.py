"""Requirement Intelligence Agent (spec section 4).

Converts raw requirements (user stories, specs) into business rules,
acceptance criteria, user journeys, and detects missing/ambiguous/
contradictory requirements and risky workflows.
"""
from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from ..llm import structured_invoke
from ..schemas import RequirementAnalysis


_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a requirements analyst for test automation. Convert the given
requirements into structured testable artifacts:

- business_rules: concrete rules the system must enforce
- acceptance_criteria: measurable, testable conditions
- user_journeys: step sequences a user takes (list of {{name, steps[]}})
- gaps: list of {type: missing|ambiguous|contradictory, description, impact}
- risky_workflows: workflows that are high-risk and should be tested first

Be precise and do not invent requirements that are not stated.
""",
        ),
        ("human", "Requirements:\n{requirements}"),
    ]
)


def analyze_requirements(requirements: list[dict[str, Any]]) -> RequirementAnalysis:
    return structured_invoke(_PROMPT, {"requirements": requirements}, RequirementAnalysis)
