import json
import random
import anthropic

client = anthropic.Anthropic()

THEMES = [
    "animals", "food & cooking", "jobs & careers", "school & teachers",
    "sports", "music & instruments", "space & astronomy", "weather",
    "technology & computers", "medicine & doctors", "construction & tools",
    "ocean & sea life", "farming & plants", "time & clocks", "money & banks",
    "travel & transport", "art & painting", "books & libraries", "magic & wizards",
    "royalty & castles",
]

PUN_STYLES = [
    "homophone (sounds like another word)",
    "double meaning (word means two things)",
    "compound word split (e.g. 'butter-fly')",
    "name pun (person's name sounds like a phrase)",
    "prefix/suffix wordplay",
]


def generate_pun_joke(used_jokes: list | None = None) -> dict:
    used_jokes = used_jokes or []

    # Pick a random theme + style to force variety
    theme = random.choice(THEMES)
    style = random.choice(PUN_STYLES)

    # Extract both questions AND punchline keywords from recent jokes
    # so the model avoids the underlying wordplay, not just the surface question
    avoid_section = ""
    if used_jokes:
        recent = used_jokes[-60:]
        avoid_section = (
            f"\nAVOID these already-used joke topics/punchlines:\n"
            f"{json.dumps(recent, indent=2)}\n"
            f"Do not reuse ANY of the wordplay concepts above, even with different wording.\n"
        )

    prompt = f"""You are a creative pun writer. Generate ONE original pun joke.

REQUIRED theme: {theme}
REQUIRED wordplay style: {style}

Rules:
- Setup: max 12 words, ends with "?" 
- Punchline: max 10 words, the wordplay payoff
- Family-friendly, groan-worthy
- Must genuinely use the required theme and style — not just mention them
- Pick 2–3 fitting emojis
{avoid_section}
Think of a FRESH angle within the theme — avoid the most obvious/famous puns.

Respond ONLY with valid JSON, no preamble, no markdown fences:
{{"question": "...", "answer": "...", "emojis": "..."}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,   # <-- max creativity; was missing entirely before
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    joke = json.loads(raw)

    for key in ("question", "answer"):
        if key not in joke or not joke[key]:
            raise ValueError(f"Missing field: {key}")

    joke.setdefault("emojis", "😂✨")
    joke["theme"] = theme  # store so agent.py can log/track it

    return joke
