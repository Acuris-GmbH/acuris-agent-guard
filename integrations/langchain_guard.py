"""LangChain recipe — drop the Acuris check into an agent's tool belt AND as a
hard pre-pay guardrail.

    pip install acuris-agent-guard langchain langchain-anthropic

Two integration points (use both):
  1. As a TOOL the agent can call to vet a merchant.
  2. As a GUARDRAIL wrapped around your real "pay"/"checkout" tool, so payment
     is structurally impossible unless the storefront verifies — don't rely on
     the model choosing to check.
"""

from __future__ import annotations

from acuris_agent_guard import PaymentBlocked, StorefrontVerifier, pre_pay_guard

_verifier = StorefrontVerifier()  # demo mode w/o key; set ACURIS_API_KEY for live


# --- 1. As a LangChain tool -------------------------------------------------
try:
    from langchain_core.tools import tool

    @tool
    def verify_storefront(url: str, name: str = "") -> str:
        """Verify a merchant/storefront before paying it. Returns the decision
        (PROCEED/ABORT/REVIEW), whether it is safe_to_pay, and the reason.
        Always call this before any checkout/payment step."""
        v = _verifier.verify(url, name=name or None)
        return (
            f"decision={v.decision} safe_to_pay={v.safe_to_pay} "
            f"domain_bound={v.domain_bound} entity_resolves={v.entity_resolves} "
            f"sanctions_hit={v.sanctions_hit} :: {v.reason}"
        )
except Exception:  # langchain not installed — the guardrail below still works
    verify_storefront = None  # type: ignore


# --- 2. As a hard guardrail around your real payment tool -------------------
def guarded_pay(url: str, amount: str, *, name: str = "", **pay_kwargs):
    """Wrap your real payment/checkout call. Raises PaymentBlocked (which your
    agent should catch and treat as 'do not pay; route elsewhere')."""
    verdict = pre_pay_guard(url, name=name or None, verifier=_verifier)  # raises if unsafe
    # ── only reached if the storefront verified ──
    # return real_payment_api.charge(url=url, amount=amount, **pay_kwargs)
    return {"status": "PAID", "url": url, "amount": amount, "verified_entity": verdict.entity_name}


if __name__ == "__main__":
    # Minimal runnable illustration (offline demo mode).
    for u, n in [("aurora-boutique-official.shop", "Aurora Linen"),
                 ("aurora-linen.example", "Aurora Linen GmbH")]:
        try:
            print("PAID:", guarded_pay(u, "€149", name=n))
        except PaymentBlocked as e:
            print("BLOCKED:", e)
