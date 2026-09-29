# Artifact Evaluation Exchange Format (AEF)

AEF is a paste-only interchange contract for artifact metrics extracted outside Genshin Planner. The application does not read screenshots or run OCR. A user reviews and confirms every value before it is persisted.

Machine-readable schema: [`schemas/aef-v1.schema.json`](../schemas/aef-v1.schema.json).

## AEF v1 single evaluation

```json
{
  "format": "AEF",
  "version": 1,
  "characterKey": "Fischl",
  "source": "ASSISTED_MANUAL",
  "metrics": {
    "rv": 2471.3,
    "cv": null,
    "rankPercent": null,
    "customScore": null,
    "slots": {
      "flower": 512.4,
      "plume": 488.7,
      "sands": 431.2,
      "goblet": 445.6,
      "circlet": 593.4
    },
    "extra": {}
  }
}
```

### Fields and validation

- `format` must be `AEF`; `version` must be the integer `1`.
- `characterKey` is the canonical owned-character key, for example `Fischl`. Display names are not resolved automatically.
- `source` is optional and, when supplied, must be `ASSISTED_MANUAL`.
- `metrics` may contain `rv`, `cv`, `rankPercent`, `customScore`, `slots`, and `extra`. Unknown top-level or metric fields are rejected.
- Overall metrics and slot metrics accept finite, non-negative numbers or `null`. `null` means unavailable and is never converted to zero. Omitted values are also unavailable.
- Slot keys are exactly `flower`, `plume`, `sands`, `goblet`, and `circlet`. Slot values are diagnostic only.
- `extra` retains named finite numeric metrics that the current Planner adapter ignores unless explicitly configured.
- The active quality adapter determines whether the evaluation can produce a normalized score. For example, an RV adapter reports that RV is required when `rv` is `null`; the raw confirmed evaluation can still be saved safely without generating a Planner quality goal.
- Strings, booleans, `NaN`, infinities, negative values, unsupported versions, unknown character keys, and duplicate character rows in a bulk request are rejected or flagged in preview.

## Bulk format

Bulk input may be either a bare JSON array of evaluation objects or the envelope below. Both formats are validated row by row in Preview; neither format saves data until confirmation.

```json
[
  { "format": "AEF", "version": 1, "characterKey": "Fischl", "source": "ASSISTED_MANUAL", "metrics": { "rv": 2471.3 } },
  { "format": "AEF", "version": 1, "characterKey": "RaidenShogun", "source": "ASSISTED_MANUAL", "metrics": { "rv": 2310 } }
]
```

The equivalent enveloped format is:

```json
{
  "format": "AEF",
  "version": 1,
  "evaluations": [
    {
      "format": "AEF",
      "version": 1,
      "characterKey": "Fischl",
      "source": "ASSISTED_MANUAL",
      "metrics": { "rv": 2471.3, "slots": {}, "extra": {} }
    }
  ]
}
```

Preview does not persist anything. Correct values in the preview, select the rows to confirm, and submit them together. A confirmation batch is atomic; one invalid selected row rejects the entire batch. The same character cannot occur more than once in a confirmed batch.

## Template

```json
{
  "format": "AEF",
  "version": 1,
  "characterKey": "",
  "source": "ASSISTED_MANUAL",
  "metrics": {
    "rv": null,
    "cv": null,
    "rankPercent": null,
    "customScore": null,
    "slots": { "flower": null, "plume": null, "sands": null, "goblet": null, "circlet": null },
    "extra": {}
  }
}
```
