# KIT rollup, citations, and display labels

## GET /kits

Returns all six Key Intelligence Topics (KITs) for the **latest run** — the batch of
signals whose `created_at` falls on the most recent calendar date in the database.
There is no `Run` model yet; latest run is inferred from signal timestamps only.

Each item includes:

- `key`, `label`, `question`, `category`, `order`
- `status`: `active` when the KIT has deliverable signals, otherwise `no_change`
- `count`: deliverable signals in this KIT for the latest run
- `withheld`: signals assigned to the KIT but excluded because they fail citation rules
- `priority_label`: tier label from `config/labels.yaml` (`Act on it` / `Worth knowing` /
  `Background`) based on `tier_for()` applied to the highest persona score in the KIT
- `snippet`: headline, quote, implication, and `citation` for the lead signal (or `null` when quiet)
- `signal_ids`: `sig_{id}` references for deliverable members

KIT membership is defined in `config/kits.yaml`. Every `signal_type` belongs to exactly
one KIT. Signals whose `subject_entity` is JFrog are promoted into **Deal Threats**
regardless of type.

Quiet KITs are always returned with `count: 0` and `status: no_change` — they are never omitted.

## Citation enforcement

`backend/app/services/citation.py` defines the cross-API `Citation` shape:

`{ source_name, source_url, captured_at, origin, archived_url, grade }`

- `deliverable(record)` — authored positions (`origin: authored`) always pass; otherwise
  `source_url` must start with `http`.
- `build_citation(record)` — archive captures (`provenance: archive`) add
  `archived_url` as `https://web.archive.org/web/{YYYYMMDDHHMMSS}id_/{source_url}`.

Records failing `deliverable()` are withheld from KIT delivery surfaces and from consumer
payloads that use this gate.

## Display labels

`config/labels.yaml` maps machine enums to human strings. API serializers add parallel
`*_label` fields (e.g. `signal_type_label`, `handling_label`) alongside raw values so
Settings can still use machine names. Evidence and Ask citations embed a `citation` object
on every delivered assertion.

The parallel `*_label` fields are emitted uniformly across the read endpoints that carry a
`signal_type` — `/signals`, `/kits`, `/industry`, `/coverage` and `/email/preview` — so the
client never has to translate a machine enum on a consumer screen. The contract-shape tests
in `tests/test_api_reads.py` compare each endpoint against its client fixture, so a serializer
and its fixture must agree on exactly these keys.
