"""The decision layer: turn an Acuris storefront-verify response into a single
agent-actionable verdict (PROCEED / ABORT / REVIEW).

The decision is taken from the engine's authoritative `recommended_action`
(`proceed` / `review` / `do_not_proceed` / `block`) — the field the API is
designed for an agent to branch on. That action already folds in the full
policy (sanctions grading, orphaned-brand, commercial-health, binding), so the
SDK maps it DIRECTLY rather than re-deriving its own decision from a subset of
raw signals. Re-deriving drifts from the engine and, worst of all, mislabels a
merely-unbound but legitimate store (a real company on a DV cert — the common
case) as a "clone" → ABORT. Mapping the action keeps the SDK and the engine in
lockstep. If a response carries no `recommended_action` (older API or a
transport error) we fall back to a conservative, fail-closed read of the raw
signals that still never calls an unbound store a clone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

PROCEED = "PROCEED"
ABORT = "ABORT"
REVIEW = "REVIEW"

# Engine recommended_action -> agent decision. `do_not_proceed` is "couldn't
# confirm" (unreachable / no covered register), not "confirmed bad", so it maps
# to REVIEW (fail closed) — never ABORT. Only an engine `block` (sanctions hit,
# no entity, conflicting identity) is a hard ABORT.
_ACTION_TO_DECISION = {
    "proceed": PROCEED,
    "review": REVIEW,
    "do_not_proceed": REVIEW,
    "block": ABORT,
}

_DEFAULT_REASON = {
    PROCEED: "Storefront is bound to a real, sanctions-clean registered entity.",
    REVIEW: (
        "The registered entity could not be independently bound to this domain "
        "(or the site could not be reached) — verify the seller before paying."
    ),
    ABORT: (
        "Payment blocked: a sanctions hit, no registered entity behind the "
        "storefront, or a conflicting identity (possible impersonation)."
    ),
}


@dataclass
class StorefrontVerdict:
    domain: str
    entity_name: Optional[str]
    decision: str                 # PROCEED | ABORT | REVIEW
    reason: str                   # human + agent readable, one line
    domain_bound: Optional[bool]
    entity_resolves: Optional[bool]
    sanctions_hit: bool
    jurisdiction_risk_band: Optional[str]
    score: Optional[float]
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def safe_to_pay(self) -> bool:
        return self.decision == PROCEED

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "entity_name": self.entity_name,
            "decision": self.decision,
            "reason": self.reason,
            "signals": {
                "domain_bound": self.domain_bound,
                "entity_resolves": self.entity_resolves,
                "sanctions_hit": self.sanctions_hit,
                "jurisdiction_risk_band": self.jurisdiction_risk_band,
            },
            "score": self.score,
        }


def _reason_for(raw: dict, decision: str) -> str:
    """Prefer the engine's own `buyer_warning` (it explains the real cause —
    clone, sanctions, distress); else a clean, action-appropriate default. We do
    NOT surface raw reason codes or assert "clone" for a merely unbound store."""
    bw = (raw.get("buyer_warning") or "").strip()
    if bw:
        return bw
    return _DEFAULT_REASON.get(decision, _DEFAULT_REASON[REVIEW])


def _fallback_from_signals(raw, coh, comp, domain_bound, entity_resolves, sanctions):
    """Only used when the response has no `recommended_action` (older API or a
    transport error). Fails CLOSED; never calls a merely-unbound store a clone."""
    if sanctions:
        return ABORT, "Merchant or a beneficial owner is on a sanctions list."
    if entity_resolves is False:
        return ABORT, "No real registered company exists behind this storefront."
    if str(comp.get("default_action") or "").lower() == "block":
        return ABORT, "Compliance policy blocks payment to this storefront."
    if domain_bound and entity_resolves is not False and coh.get("reachable", True):
        return PROCEED, _DEFAULT_REASON[PROCEED]
    # Unbound, unreachable, or unknown -> REVIEW (verify), never ABORT-as-clone.
    return REVIEW, _DEFAULT_REASON[REVIEW]


def decide(raw: dict) -> StorefrontVerdict:
    """Map an Acuris /storefront-verify response -> StorefrontVerdict."""
    layers = raw.get("layers") or {}
    coh = layers.get("coherence") or {}
    comp = layers.get("compliance") or {}

    domain_bound = raw.get("domain_bound")
    entity_resolves = raw.get("entity_resolves")
    sanctions = bool(comp.get("sanctions_hit") or comp.get("ubo_sanctions_hit"))
    risk_band = raw.get("jurisdiction_risk_band") or (raw.get("jurisdiction_risk") or {}).get("risk_band")
    entity_name = raw.get("bound_entity") or raw.get("register_name")

    action = str(raw.get("recommended_action") or "").strip().lower()
    if action in _ACTION_TO_DECISION:
        decision = _ACTION_TO_DECISION[action]
        reason = _reason_for(raw, decision)
    else:
        decision, reason = _fallback_from_signals(
            raw, coh, comp, domain_bound, entity_resolves, sanctions
        )

    return StorefrontVerdict(
        domain=raw.get("domain") or "",
        entity_name=entity_name,
        decision=decision,
        reason=reason,
        domain_bound=domain_bound,
        entity_resolves=entity_resolves,
        sanctions_hit=sanctions,
        jurisdiction_risk_band=risk_band,
        score=raw.get("score"),
        raw=raw,
    )
