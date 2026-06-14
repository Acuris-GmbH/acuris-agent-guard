"""The guardrail: one function to drop into an agent's pre-payment step.

    from acuris_agent_guard import pre_pay_guard, PaymentBlocked
    try:
        pre_pay_guard(url, name="Aurora Linen")   # raises if unsafe
        do_payment(...)
    except PaymentBlocked as e:
        agent.report(str(e))                       # abort, route elsewhere

`block_on_review=True` (default) treats an unverifiable storefront as unsafe —
fail closed. Set False to allow REVIEW-tier merchants through with a warning.
"""

from __future__ import annotations

from typing import Optional

from .client import StorefrontVerifier
from .verdict import ABORT, PROCEED, REVIEW, StorefrontVerdict

_DEFAULT = StorefrontVerifier()


class PaymentBlocked(Exception):
    """Raised when a storefront fails verification before payment."""

    def __init__(self, verdict: StorefrontVerdict):
        self.verdict = verdict
        super().__init__(f"[{verdict.decision}] {verdict.domain}: {verdict.reason}")


def pre_pay_guard(
    url_or_domain: str,
    *,
    name: Optional[str] = None,
    vat: Optional[str] = None,
    lei: Optional[str] = None,
    country: Optional[str] = None,
    verifier: Optional[StorefrontVerifier] = None,
    block_on_review: bool = True,
) -> StorefrontVerdict:
    """Verify a storefront; raise PaymentBlocked if not safe to pay. Returns the
    verdict on success so the caller can log the evidence trail."""
    v = (verifier or _DEFAULT).verify(url_or_domain, name=name, vat=vat, lei=lei, country=country)
    if v.decision == PROCEED:
        return v
    if v.decision == REVIEW and not block_on_review:
        return v
    raise PaymentBlocked(v)
