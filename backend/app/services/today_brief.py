def compose_headline(cards: list[dict]) -> str:
    act = [c for c in cards if c["tier"] == "act_on_it"]
    if not act:
        lead = cards[0]["headline"] if cards else "nothing new of note"
        return f"Quiet day — one thing worth a look: {lead}."
    if len(act) == 1:
        return f"One thing worth your attention: {act[0]['headline']}."
    return f"{len(act)} items to act on today, led by: {act[0]['headline']}."
