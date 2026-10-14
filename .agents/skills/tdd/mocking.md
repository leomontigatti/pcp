# When to Mock

Mock at **system boundaries** only:

- External services: ARCA's webservices (the client in `l10n_ar_fiscal_ws`), email, payment gateways
- The clock and randomness
- The file system (sometimes)
- The database (sometimes; prefer the test database that `TransactionCase` gives each test)

Don't mock:

- Your own models and modules
- Internal collaborators: other methods of the same model, the ORM
- Anything you control

## Designing for Mockability

At system boundaries, design interfaces that are easy to mock:

**1. Use dependency injection**

Pass external dependencies in rather than creating them internally:

```python
# Easy to mock
def process_payment(order, payment_client):
    return payment_client.charge(order.amount_total)

# Hard to mock
def process_payment(order):
    client = PaymentClient(os.environ["PAYMENT_KEY"])
    return client.charge(order.amount_total)
```

**2. Prefer SDK-style interfaces over generic fetchers**

Create specific methods for each external operation instead of one generic method with conditional logic:

```python
# GOOD: each method is independently mockable
class ArcaClient:
    def last_voucher_number(self, point_of_sale, voucher_type): ...
    def request_cae(self, payload): ...

# BAD: mocking requires conditional logic inside the mock
class ArcaClient:
    def call(self, service, **params): ...
```

The SDK approach means:

- Each mock returns one specific shape
- No conditional logic in test setup
- Easier to see which operations a test exercises

In an Odoo test, mock the boundary method with `unittest.mock.patch.object(ArcaClient, "request_cae", return_value=...)`
and assert on what the model does with the answer, not on the answer itself (see the pass-through
anti-pattern in `SKILL.md`).
