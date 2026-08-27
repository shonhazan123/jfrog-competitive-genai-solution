# Digests — HTTP surface

Two distinct digest routes. Do not collapse sales/product into the exec weekly
roll-up, and do not invent a third assembly path.

## `GET /digests/{persona}` — sales / product (first-class)

Persona ∈ `{sales, product}`. Paths: `/digests/sales`, `/digests/product`.

Assembled, budget-capped, ranked by persona tier (`act_on_it` → `worth_knowing` →
`background`; stable within a tier). Response shape is
[API_CONTRACT §2.1](../API_CONTRACT.md#21-get-digestspersona--assembled-per-persona-digest):

`persona`, `date`, `subject`, `lead`, `budget`, `item_count`,
`handling_caution_count`, `awareness_only_count`, `items` (list of Signal),
`silent_entities`.

Implemented in:

- `backend/app/routers/digests.py` — `GET /{persona}`
- `backend/app/controllers/digests.py` — `persona_digest`

Task 11 originally omitted this route; verification added it to match the
contract. Keep it.

## `GET /digests/exec/weekly` — executive roll-up (separate)

Weekly trends + stability statement. Different response shape
([API_CONTRACT §3.1](../API_CONTRACT.md#31-get-digestsexecweekly--weekly-executive-roll-up)).
Implemented as `GET /exec/weekly` on the same router, `exec_weekly` in the
controller. Do not serve this payload from `GET /digests/{persona}`.
