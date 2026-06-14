"""Anthropic computer-use recipe — intercept the action loop right before the
agent submits a payment, and abort if the storefront does not verify.

    pip install acuris-agent-guard anthropic

With computer use, the model emits `tool_use` actions (click/type/screenshot).
You already execute those actions in a loop. Insert ONE check: before you let a
"pay / place order / submit" action through, resolve the current storefront
domain and call the guard. If it raises, you DON'T execute the action — you feed
the block back to the model as the tool_result so it routes elsewhere.

Below is the integration point as a thin wrapper you call from your existing
computer-use executor. It is framework-agnostic: the only thing you provide is
(a) the current domain and (b) the entity the page claims to be.
"""

from __future__ import annotations

import re
from typing import Optional

from acuris_agent_guard import PaymentBlocked, StorefrontVerifier, pre_pay_guard

_verifier = StorefrontVerifier()

# Heuristic: which computer-use actions are "about to pay".
_PAY_INTENT = re.compile(r"\b(pay|place order|buy now|complete purchase|submit payment|checkout)\b", re.I)


def is_payment_action(action: dict) -> bool:
    """True if this computer-use action looks like it commits a payment.
    `action` is the tool_use input, e.g. {"action":"left_click","text":"Place order"}."""
    blob = " ".join(str(v) for v in action.values())
    return bool(_PAY_INTENT.search(blob))


def screen_before_payment(domain: str, claimed_name: Optional[str] = None) -> Optional[str]:
    """Call right before executing a payment action. Returns None if safe to
    proceed, or a string to feed back to the model as the tool_result (the
    action was NOT executed) if the storefront failed verification."""
    try:
        v = pre_pay_guard(domain, name=claimed_name, verifier=_verifier)
        return None  # safe — let the original action execute
    except PaymentBlocked as e:
        v = e.verdict
        return (
            f"PAYMENT BLOCKED by Acuris Agent Guard. Did NOT submit payment.\n"
            f"storefront: {v.domain}\ndecision: {v.decision}\nreason: {v.reason}\n"
            f"signals: domain_bound={v.domain_bound} entity_resolves={v.entity_resolves} "
            f"sanctions_hit={v.sanctions_hit}\n"
            f"Do not retry this merchant. Find a verified seller instead."
        )


# ── how it slots into your existing executor loop ───────────────────────────
#
#   for action in model_tool_uses:
#       if is_payment_action(action):
#           blocked = screen_before_payment(current_domain, claimed_name=page_brand)
#           if blocked:
#               tool_results.append({"type": "tool_result", "content": blocked})
#               continue            # <-- the click never happens; agent re-plans
#       execute(action)             # normal path
#
if __name__ == "__main__":
    # offline illustration
    for dom, brand in [("aurora-boutique-official.shop", "Aurora Linen"),
                       ("aurora-linen.example", "Aurora Linen GmbH")]:
        msg = screen_before_payment(dom, brand)
        print(f"{dom}: {'PROCEED (click executes)' if msg is None else 'BLOCKED'}")
        if msg:
            print("  " + msg.replace("\n", "\n  "))
