# Good and Bad Tests

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of internal parts. In Odoo, that
means a `TransactionCase` that creates records and calls the model method.

```python
# GOOD: tests observable behavior
def test_confirm_moves_order_to_sale(self):
    order = self._new_order(partner=self.wholesale_partner)
    order.action_confirm()
    self.assertEqual(order.state, "sale")
```

Characteristics:

- Tests behavior users/callers care about
- Uses public API only
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```python
# BAD: tests implementation details
def test_confirm_calls_sequence_next(self):
    with patch.object(type(self.env["ir.sequence"]), "next_by_code") as nxt:
        self._new_order().action_confirm()
    nxt.assert_called_once()
```

Red flags:

- Mocking internal collaborators
- Testing private methods
- Asserting on call counts/order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Verifying through external means instead of interface

```python
# BAD: bypasses the interface to verify
def test_create_saves_row(self):
    self.env["sale.order"].create({"partner_id": self.partner.id})
    self.env.cr.execute("SELECT count(*) FROM sale_order")
    self.assertEqual(self.env.cr.fetchone()[0], 1)

# GOOD: verifies through the interface
def test_created_order_is_searchable(self):
    order = self.env["sale.order"].create({"partner_id": self.partner.id})
    self.assertIn(order, self.env["sale.order"].search([("partner_id", "=", self.partner.id)]))
```

**Tautological tests**: Expected value restates the implementation, so the test passes by construction.

```python
# BAD: expected value is recomputed the way the code computes it
def test_total_sums_lines(self):
    lines = [10, 5]
    self.assertEqual(total(lines), sum(lines))

# GOOD: expected value is an independent, known literal
def test_total_sums_lines(self):
    self.assertEqual(total([10, 5]), 15)
```
