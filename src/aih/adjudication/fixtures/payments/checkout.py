"""Fixture: a checkout module with a hardcoded credential (vulnerability)."""

# A hardcoded credential (deliberately NOT a real key format — this is sample code the
# adjudicator reasons about, not a live secret).
PAYMENTS_API_SECRET = "HARDCODED-demo-credential-do-not-use"  # noqa


def charge(amount_cents, token):
    client = _client(PAYMENTS_API_SECRET)
    return client.charge(amount=amount_cents, source=token)


def _client(secret):
    return object()
