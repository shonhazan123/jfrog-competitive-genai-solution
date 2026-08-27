from app.services.today_brief import compose_headline


def test_headline_quiet_day():
    assert "Quiet day" in compose_headline([{"tier": "background", "headline": "x"}])


def test_headline_one_act_item():
    cards = [{"tier": "act_on_it", "headline": "Sonatype claims 80% better malware data"}]
    h = compose_headline(cards)
    assert "one thing worth your attention" in h.lower()
    assert "Sonatype" in h


def test_headline_multiple_act_items():
    cards = [{"tier": "act_on_it", "headline": "A"}, {"tier": "act_on_it", "headline": "B"}]
    assert "act on" in compose_headline(cards).lower()
