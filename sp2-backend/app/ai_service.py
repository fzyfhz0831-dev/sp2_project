from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from app.config import BASE_DIR

ENV_PATH = BASE_DIR / ".env"
DEFAULT_MODEL = "gpt-4.1-mini"
RESPONSES_URL = "https://api.openai.com/v1/responses"
PLACEHOLDER_KEY_VALUES = {
    "your_openai_api_key_here",
    "your_api_key_here",
    "replace_me",
    "changeme",
}


class AIServiceError(RuntimeError):
    """Raised when AI analysis fails."""


def _load_env_value(name: str) -> str | None:
    """Read one value from the process environment or local .env file."""
    value = os.getenv(name)
    if value:
        return value

    if not ENV_PATH.exists():
        return None

    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
            continue

        key, raw_value = clean_line.split("=", 1)
        if key.strip() == name:
            return raw_value.strip().strip('"').strip("'") or None

    return None


def _has_real_api_key(api_key: str | None) -> bool:
    """Return True only for values that look like real OpenAI API keys."""
    if not api_key:
        return False

    clean_key = api_key.strip()
    lower_key = clean_key.lower()
    if lower_key in PLACEHOLDER_KEY_VALUES:
        return False

    return clean_key.startswith("sk-")


def _build_prompt(
    parsed_data: dict[str, Any],
    findings: dict[str, Any] | None = None,
    wiki_context: list[str] | None = None,
) -> str:
    """Build a prompt that uses rule-based findings for the AI to explain naturally.

    When *findings* is provided, the AI is asked to summarize and explain the
    pre-computed issues in natural language rather than generating generic advice.

    When *wiki_context* is provided, it is injected as additional expert
    knowledge the AI should reference in its explanation.
    """
    run_json = json.dumps(parsed_data, ensure_ascii=False, indent=2)

    # Build wiki context block if available.
    wiki_block = ""
    if wiki_context:
        wiki_block = (
            "\n\nExpert Wiki Knowledge (reference these facts in your analysis):\n"
            + "\n".join(f"- {entry}" for entry in wiki_context)
            + "\n"
        )

    if findings and (findings.get("problems") or findings.get("warnings") or findings.get("suggestions")):
        # Structured findings available — AI explains them.
        findings_json = json.dumps(findings, ensure_ascii=False, indent=2)
        return (
            "You are a Slay the Spire coach explaining a run analysis to a player. "
            "A rule-based analysis engine has already identified specific problems, "
            "strengths, warnings, and suggestions. Your job is to write a natural, "
            "helpful explanation of these findings.\n\n"
            "Rules:\n"
            "- Do NOT invent problems the rule engine did not find.\n"
            "- Do NOT give generic advice — only explain the specific issues below.\n"
            "- If strengths are listed, acknowledge them positively.\n"
            "- If suggestions are listed, explain WHY each one helps.\n"
            "- Write in friendly, encouraging tone (the player just lost a run).\n"
            f"{wiki_block}\n"
            "Return your response with these exact sections:\n"
            "1. Reason for success/failure\n"
            "2. 3 key mistakes (derived from the problems/warnings below)\n"
            "3. 3 improvement suggestions (derived from the suggestions below)\n"
            "4. Short summary\n\n"
            "Rule-based findings:\n"
            f"{findings_json}\n\n"
            "Parsed run data (for context):\n"
            f"{run_json}"
        )

    # Fallback: no findings — use generic prompt.
    return (
        "You are analyzing a Slay the Spire run. Return a concise analysis with "
        "these exact sections:\n"
        "1. Reason for success/failure\n"
        "2. 3 key mistakes\n"
        "3. 3 improvement suggestions\n"
        "4. Short summary\n\n"
        "Parsed run data:\n"
        f"{run_json}"
    )


def _mock_analysis(parsed_data: dict[str, Any], findings: dict[str, Any] | None = None) -> str:
    """Return a local result when no API key is configured, using rule findings."""
    character = parsed_data.get("character") or "Unknown character"
    floor = parsed_data.get("floor_reached") or parsed_data.get("floor") or "unknown floor"
    victory = parsed_data.get("victory")
    outcome = "success" if victory is True else "failure" if victory is False else "result"

    if findings:
        problems = findings.get("problems", [])
        strengths = findings.get("strengths", [])
        suggestions = findings.get("suggestions", [])

        # Build mistakes from problems (up to 3)
        mistakes = problems[:3] if problems else [
            "Review whether the deck had enough block for late fights.",
            "Check if elite or boss pathing created unnecessary risk.",
            "Look for missing scaling or weak card/relic synergy.",
        ]
        while len(mistakes) < 3:
            mistakes.append("No further specific issues detected.")

        # Build suggestions from rule suggestions (up to 3)
        rule_suggestions = suggestions[:3] if suggestions else [
            "Add reliable defense before taking high-risk paths.",
            "Pick cards that support one clear win condition.",
            "Compare boss needs against your deck before the final act.",
        ]
        while len(rule_suggestions) < 3:
            rule_suggestions.append("Continue playing to gather more data for analysis.")

        strength_text = ""
        if strengths:
            strength_text = f"\n\nStrengths noted:\n- " + "\n- ".join(strengths[:4])

        reason_line = (
            f"Reason for success/failure:\n"
            f"{character} recorded a {outcome} at floor {floor}. "
            + (f"Key issues: {problems[0]}" if problems else "No specific problems detected.")
            + f"\n(Rule-based analysis — no AI key configured)"
        )

        return (
            f"{reason_line}\n\n"
            f"3 key mistakes:\n"
            + "\n".join(f"{i+1}. {m}" for i, m in enumerate(mistakes)) +
            f"\n\n3 improvement suggestions:\n"
            + "\n".join(f"{i+1}. {s}" for i, s in enumerate(rule_suggestions)) +
            f"{strength_text}\n\n"
            f"Short summary:\n"
            f"Rule-based analysis of {character}'s run to floor {floor}. "
            f"{len(problems)} problem(s), {len(suggestions)} suggestion(s) found."
        )

    # No findings at all — truly generic fallback.
    return (
        "Reason for success/failure:\n"
        f"Mock analysis: {character} recorded a {outcome} around floor {floor}. "
        "No usable OPENAI_API_KEY was found, so this is a local placeholder.\n\n"
        "3 key mistakes:\n"
        "1. Review whether the deck had enough block for late fights.\n"
        "2. Check if elite or boss pathing created unnecessary risk.\n"
        "3. Look for missing scaling or weak card/relic synergy.\n\n"
        "3 improvement suggestions:\n"
        "1. Add reliable defense before taking high-risk paths.\n"
        "2. Pick cards that support one clear win condition.\n"
        "3. Compare boss needs against your deck before the final act.\n\n"
        "Short summary:\n"
        "This mock result confirms the analysis pipeline is working without an API key."
    )


def _extract_response_text(response: Any) -> str:
    """Extract text from OpenAI Responses API objects."""
    if isinstance(response, dict):
        output_text = response.get("output_text")
        if output_text:
            return str(output_text).strip()

        pieces: list[str] = []
        for item in response.get("output", []) or []:
            for content in item.get("content", []) or []:
                text = content.get("text")
                if text:
                    pieces.append(str(text))
        return "\n".join(pieces).strip()

    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text).strip()

    output = getattr(response, "output", None) or []
    pieces: list[str] = []
    for item in output:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                pieces.append(str(text))

    return "\n".join(pieces).strip()


def _call_openai_http(prompt: str, model: str, api_key: str) -> str:
    """Call the OpenAI Responses API with Python's standard library."""
    payload = json.dumps({"model": model, "input": prompt}).encode("utf-8")
    request = urllib.request.Request(
        RESPONSES_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise AIServiceError(f"OpenAI HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise AIServiceError(f"OpenAI request failed: {error.reason}") from error

    try:
        response_json = json.loads(body)
    except json.JSONDecodeError as error:
        raise AIServiceError("OpenAI returned invalid JSON.") from error

    text = _extract_response_text(response_json)
    if not text:
        raise AIServiceError("OpenAI returned an empty analysis.")

    return text


def _call_chat_completions_http(prompt: str, model: str, api_key: str, base_url: str) -> str:
    """Call a Chat Completions-compatible API with Python's standard library.

    Used when the ``openai`` package is not installed and the provider
    exposes a ``/chat/completions`` endpoint (DeepSeek, OpenAI, etc.).
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as http_response:
            body = http_response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise AIServiceError(f"AI API HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise AIServiceError(f"AI API request failed: {error.reason}") from error

    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        raise AIServiceError("AI API returned invalid JSON.") from error

    # Chat Completions response format: {"choices": [{"message": {"content": "..."}}]}
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise AIServiceError("AI API response missing expected content.") from error

    if not text or not str(text).strip():
        raise AIServiceError("AI API returned an empty analysis.")

    return str(text).strip()


def _call_chat_completions(prompt: str, model: str, api_key: str, base_url: str) -> str:
    """Call a Chat Completions-compatible API via the OpenAI SDK.

    Supports any provider with a ``/chat/completions`` endpoint
    (DeepSeek, OpenAI, Groq, Fireworks, etc.).
    """
    try:
        from openai import OpenAI
    except ImportError:
        return _call_chat_completions_http(prompt, model, api_key, base_url)

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content
    except Exception as error:
        raise AIServiceError(str(error)) from error

    if not text or not str(text).strip():
        raise AIServiceError("AI API returned an empty analysis.")

    return str(text).strip()


def _call_openai(prompt: str, model: str, api_key: str, base_url: str | None = None) -> str:
    """Call the AI provider.

    When *base_url* is provided, uses the Chat Completions API
    (compatible with DeepSeek and other providers).  Otherwise uses
    the OpenAI Responses API.
    """
    if base_url:
        return _call_chat_completions(prompt, model, api_key, base_url)

    try:
        from openai import OpenAI
    except ImportError:
        return _call_openai_http(prompt, model, api_key)

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            input=prompt,
        )
        text = _extract_response_text(response)
    except Exception as error:
        raise AIServiceError(str(error)) from error

    if not text:
        raise AIServiceError("OpenAI returned an empty analysis.")

    return text


def analyze_run(
    parsed_data: dict[str, Any],
    findings: dict[str, Any] | None = None,
    wiki_context: list[str] | None = None,
) -> str:
    """Analyze one parsed run using AI, or a mock result without a key.

    When *findings* (from :func:`rule_analyzer.analyze_run_rules`) is provided,
    the AI is instructed to explain those specific findings rather than invent
    generic advice.

    When *wiki_context* is provided, expert wiki knowledge entries are injected
    into the prompt so the AI can reference them in its analysis.

    Environment variables
    ---------------------
    ``OPENAI_API_KEY``
        Required.  Must start with ``sk-``.
    ``OPENAI_MODEL``
        Optional — ``gpt-4.1-mini`` when unset.
    ``OPENAI_BASE_URL``
        Optional.  When set (e.g. ``https://api.deepseek.com``) the
        provider's Chat Completions API is used instead of OpenAI's
        Responses API, enabling DeepSeek and other compatible providers.
    """
    api_key = _load_env_value("OPENAI_API_KEY")
    model = _load_env_value("OPENAI_MODEL") or DEFAULT_MODEL
    base_url = _load_env_value("OPENAI_BASE_URL")

    if not _has_real_api_key(api_key):
        return _mock_analysis(parsed_data, findings)

    prompt = _build_prompt(parsed_data, findings, wiki_context=wiki_context)
    return _call_openai(prompt, model, api_key, base_url)
