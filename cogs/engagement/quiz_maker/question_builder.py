# cogs/engagement/quiz_maker/question_builder.py
from __future__ import annotations

import json
import logging
import re
from typing import List

from openai import AsyncOpenAI

from .quiz_session import Question

log = logging.getLogger(__name__)

_PREFIX_RE = re.compile(r"^[A-Z]\s*[\)\.\:\-\]]\s*", re.IGNORECASE)


def _truncate_text(text: str, max_chars: int = 6000) -> str:
    """Limit input size so prompts do not explode."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _normalize_level(level: str | None) -> str:
    level_normalized = (level or "medium").lower()
    if level_normalized not in {"easy", "medium", "hard"}:
        level_normalized = "medium"
    return level_normalized


def _build_prompt(
    text: str,
    num_questions: int,
    level: str,
    existing_questions: list[str] | None = None,
) -> str:
    """
    Build the prompt asking the model to create multiple choice questions.
    Includes difficulty guidance and optional "do not repeat" hints.
    """
    level_normalized = _normalize_level(level)

    if level_normalized == "easy":
        difficulty_instructions = (
            "- Difficulty level: EASY. Focus on basic ideas and straightforward questions "
            "that a beginner could handle.\n"
        )
    elif level_normalized == "hard":
        difficulty_instructions = (
            "- Difficulty level: HARD. Ask challenging questions that require deeper reasoning, "
            "careful reading and strong understanding. Use plausible but wrong distractors.\n"
        )
    else:
        difficulty_instructions = (
            "- Difficulty level: MEDIUM. Mix conceptual understanding with some light application, "
            "appropriate for an intermediate learner.\n"
        )

    avoid_repeats_block = ""
    if existing_questions:
        bullet_list = "\n".join(
            f"- {q}" for q in existing_questions if str(q).strip()
        )
        if bullet_list:
            avoid_repeats_block = (
                "\nThe quiz already includes the following questions. "
                "Do not repeat these questions or create new questions that have essentially "
                "the same meaning:\n"
                f"{bullet_list}\n"
            )

    return (
        "You are a quiz generator. Create high quality multiple choice questions "
        "from the document content below.\n\n"
        "Requirements:\n"
        f"- Create exactly {num_questions} questions.\n"
        "- Each question must have 4 options.\n"
        "- Mark the correct option using an index.\n"
        "- Include a short explanation for the correct answer.\n"
        f"{difficulty_instructions}\n"
        "Additional constraints:\n"
        "- Avoid repeating questions.\n"
        "- Avoid trivially rephrasing previous questions in the same quiz.\n"
        f"{avoid_repeats_block}\n"
        "Return ONLY valid JSON in this structure:\n"
        "{\n"
        '  "questions": [\n'
        "    {\n"
        '      "question": "text",\n'
        '      "choices": ["A", "B", "C", "D"],\n'
        '      "correct_index": 0,\n'
        '      "explanation": "text"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Document content starts here:\n\n"
        f"{text}"
    )


def _safe_load_json(raw: str) -> dict:
    """
    Try to parse JSON even if the model wrapped it in extra text.
    """
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        log.error("Model returned invalid JSON: %s", exc)
        log.debug("Raw model output: %s", raw)
        raise ValueError(f"Model returned invalid JSON: {exc}") from exc


def _clean_choice_text(text: str) -> str:
    """
    Strip any leading label like 'A)', 'b.', 'C -' from a choice string.
    This avoids 'A. A) DataFrame' style duplication.
    """
    text = str(text).strip()
    text = _PREFIX_RE.sub("", text, count=1)
    return text.strip()


async def build_questions_from_text(
    client: AsyncOpenAI,
    source_text: str,
    num_questions: int,
    *,
    level: str = "medium",
    model: str = "gpt-4o-mini",
    existing_questions: list[str] | None = None,
) -> List[Question]:
    """
    Use the OpenAI client to generate questions from text.

    This is asynchronous so it does not block the event loop.

    When existing_questions is provided, attempts to avoid generating
    questions with the same prompt text.
    """
    trimmed = _truncate_text(source_text)
    level_normalized = _normalize_level(level)
    prompt = _build_prompt(trimmed, num_questions, level_normalized, existing_questions)

    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You create technical quizzes."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2000,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = (resp.choices[0].message.content or "").strip()
    if not content:
        raise ValueError("Empty response from model")

    data = _safe_load_json(content)
    raw_questions = data.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise ValueError("Model response missing 'questions' list")

    existing_normalized: set[str] = set()
    if existing_questions:
        for q in existing_questions:
            text = str(q).strip().lower()
            if text:
                existing_normalized.add(text)

    batch_seen_prompts: set[str] = set()

    questions: List[Question] = []
    for item in raw_questions:
        try:
            q_text = str(item.get("question", "")).strip()
            raw_choices = item.get("choices", [])
            choices = [_clean_choice_text(c) for c in raw_choices]
            correct_index = int(item.get("correct_index", 0))
            explanation = str(item.get("explanation", "")).strip()
        except Exception:
            continue

        if not q_text or len(choices) < 2:
            continue

        normalized_prompt = q_text.strip().lower()
        if not normalized_prompt:
            continue

        if normalized_prompt in existing_normalized or normalized_prompt in batch_seen_prompts:
            continue
        batch_seen_prompts.add(normalized_prompt)

        if correct_index < 0 or correct_index >= len(choices):
            correct_index = 0

        choices = choices[:4]
        while len(choices) < 4:
            choices.append("N/A")

        questions.append(
            Question(
                prompt=q_text,
                choices=choices,
                correct_index=correct_index,
                explanation=explanation or "No explanation provided.",
                difficulty=level_normalized,
            )
        )

    if not questions:
        raise ValueError("No valid questions parsed from model output")

    return questions[:num_questions]
