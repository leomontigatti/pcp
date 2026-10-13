When your change touches models, the ORM or the database, use this TDD workflow.

## Principles

1. **Validate using the interface.** Test the behavior through the same path the real code uses:
   call the model method (or the controller route) on a recordset created in the test, and assert
   on the result. Odoo's `TransactionCase` gives each test a database that rolls back, so use it
   instead of mocking the ORM. Never test internal query structure, intermediate state, or how a
   method builds its SQL.

2. **Don't test what the framework proves.** If Odoo already guarantees a field type, a required
   constraint or an access rule, don't write a test for it. Focus tests on runtime behaviour the
   framework can't verify: rounding and sums of amounts, ordering of postings, state after a
   confirm, numbering, edge cases in the business logic.

3. **One test at a time.** Write a single failing test, make it pass, then write the next one. Each
   test you add should teach you something new about the implementation. If you batch-write tests
   upfront, you end up with tests that don't actually validate anything useful.

## Workflow

### 1. Write a SINGLE failing test first

Put it in the addon's `tests/` package and import it from `tests/__init__.py`, as Odoo requires.
Run it with `uv run just test <module>` and narrow with `TEST_TAGS='/<module>:<Class>.<test>'`.

### 2. Make it pass with the simplest implementation

### 3. Repeat 1 & 2 until the feature is complete

### 4. Refactor under green tests

Run `uv run just test <module>` after each refactor step; `uv run just gate` before the commit.
