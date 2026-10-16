# Domain docs

How this repo's domain documentation is laid out and read. The shared `domain-modeling` skill
writes it.

## Layout

One context, so one glossary:

```
/
├── GLOSSARY.md      ← the terms
├── docs/adr/        ← the decisions, created with the first ADR
└── prototype/addons/
```

Before exploring an area, read `GLOSSARY.md` and the ADRs in `docs/adr/` that touch it. If
`docs/adr/` does not exist yet, proceed without it: it is created when the first decision is
recorded.

## The glossary

Each term has an English name, used in discussion and in every code identifier, and a Spanish
translation (`_Spanish_:`), used only where an end user reads it. When your output names a domain
concept (an issue title, a test name, a hypothesis), use the glossary's term, not a synonym it lists
under `_Avoid_`. New entries keep this shape, the `_Spanish_:` line included, rather than the `ui:`
line of the shared skill's `GLOSSARY-FORMAT.md`. A concept the glossary lacks is either language the project does not use, or a gap
for `domain-modeling`.

## Stress-testing a term

The edge cases here are Argentine tax cases: invoices, IVA categories, CAE, Perceptions and
Withholdings. Name the taxpayer category (`Responsable Inscripto`, `Monotributo`, `Consumidor Final`,
`Exento`) and the document type (`Factura A`, `B` or `C`, `Nota de Crédito`) in every scenario.

## ADR conflicts

If your output contradicts an existing ADR, say so explicitly rather than silently overriding it:

> _Contradicts ADR-0007 (…), but worth reopening because…_
