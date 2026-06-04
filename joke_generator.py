"""
joke_generator.py
Generates fresh pun jokes using the Claude API.
"""

import json
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env


def generate_pun_joke(used_jokes: list | None = None) -> dict:
    """
    Returns a dict with keys: question, answer, emojis
    Example: {"question": "Why was 6 afraid of 7?",
               "answer": "Because 7 8 9!",
               "emojis": "😂🍽️😱"}
    """
    avoid_block = ""
    if used_jokes:
        sample = used_jokes[-40:]          # send only the most recent 40
        avoid_block = (
            f"\nDo NOT reuse any of these questions:\n{json.dumps(sample)}\n"
        )

    prompt = f"""You are a pun master. Generate ONE classic wordplay / pun joke.

Rules:
- The question must be a short, punny setup (max 12 words).
- The answer is the punchline that uses a homophone, double-meaning, or wordplay (max 12 words).
- Pick 2-3 fitting emojis for the answer.
- Make it groan-worthy but family-friendly.
- Use varied themes: animals, food, jobs, school, sports, etc.
{avoid_block}
Respond ONLY with valid JSON (no preamble, no markdown):
{{
  "question": "...",
  "answer": "...",
  "emojis": "..."
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    joke = json.loads(raw)

    for key in ("question", "answer", "emojis"):
        if key not in joke or not joke[key]:
            raise ValueError(f"Missing field in joke response: {key}")

    return joke
