from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from src.core.config import get_settings
from src.core.observability import get_openai_client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SnippetPersonResult:
    person_name: str | None
    title: str | None
    source_url: str | None
    confidence: float | None


async def extract_person_from_snippets(
    *,
    company_name: str,
    snippets: list[dict],
) -> SnippetPersonResult | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None

    if not company_name or not snippets:
        return None

    prompt = {
        "company_name": company_name,
        "snippets": snippets,
        "task": "Identify the primary decision-maker (owner, president, director, or manager).",
        "output_schema": {
            "person_name": "string | null",
            "title": "string | null",
            "source_url": "string | null",
            "confidence": "float 0-1",
        },
    }

    client = get_openai_client()
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract decision-maker names from search snippets. "
                        "Return only valid JSON matching the schema."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            return None

        data = json.loads(content)
        return SnippetPersonResult(
            person_name=data.get("person_name"),
            title=data.get("title"),
            source_url=data.get("source_url"),
            confidence=data.get("confidence"),
        )
    except Exception as e:
        logger.debug(f"LLM snippet extraction failed: {e}")
        return None


@dataclass(frozen=True)
class SnippetDomainResult:
    domain: str | None
    confidence: float | None


async def pick_domain_from_snippets(
    *,
    company_name: str,
    snippets: list[dict],
    candidate_domains: list[str],
) -> SnippetDomainResult | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None

    if not company_name or not snippets or not candidate_domains:
        return None

    prompt = {
        "company_name": company_name,
        "candidate_domains": candidate_domains,
        "snippets": snippets,
        "task": "Select the most likely official company domain from the candidates.",
        "output_schema": {"domain": "string | null", "confidence": "float 0-1"},
    }

    client = get_openai_client()
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You select the official company domain from candidates. "
                        "Return only valid JSON."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            return None

        data = json.loads(content)
        return SnippetDomainResult(
            domain=data.get("domain"),
            confidence=data.get("confidence"),
        )
    except Exception as e:
        logger.debug(f"LLM domain selection failed: {e}")
        return None
