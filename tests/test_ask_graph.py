def test_tools_are_read_only_and_ledger_scoped():
    from agent.tools.ledger import TOOLS

    names = {t.name for t in TOOLS}
    assert names <= {
        "search_signals",
        "get_claim",
        "claim_history",
        "compare_entities",
        "list_sources",
    }
    assert not any("fetch" in n or "write" in n or "delete" in n for n in names)
