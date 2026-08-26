from langchain_core.tools import tool


@tool
def search_signals(query: str, filters: dict | None = None) -> list:
    """Search ledger signals matching query and optional filters."""
    return []


@tool
def get_claim(claim_id: str) -> dict:
    """Retrieve a single claim by id."""
    return {}


@tool
def claim_history(claim_id: str) -> list:
    """Return revision history for a claim."""
    return []


@tool
def compare_entities(entity_a: str, entity_b: str) -> dict:
    """Compare claims and signals between two entities."""
    return {}


@tool
def list_sources() -> list:
    """List available ledger sources."""
    return []


TOOLS = [search_signals, get_claim, claim_history, compare_entities, list_sources]
