"""Illustrative demo fixtures shaped like real Acuris /storefront-verify
responses. Used by demo mode so the PoC runs with ZERO setup (no API key, no
network). Values are representative of the reachable verification path; the
field structure mirrors the live endpoint so the decision logic in verdict.py
is exercised identically in demo and live mode.

Two merchants for the canonical "naked agent vs guarded agent" story:
  - aurora-linen.example  -> a real, bound, sanctions-clean merchant (PROCEED)
  - aurora-boutique-official.shop -> a CLONE: it presents a real brand's
    identity (entity exists in the register) on a fresh look-alike domain that
    is NOT bound to that entity (ABORT) — the exact, differentiated catch.
"""

from __future__ import annotations

_VERIFIED = {
    "domain": "aurora-linen.example",
    "domain_bound": True,
    "entity_resolves": True,
    "bound_entity": "AURORA LINEN GMBH",
    "register_name": "AURORA LINEN GMBH",
    "score": 96,
    "verdict": "verified",
    "recommended_action": "proceed",
    "buyer_warning": None,
    "jurisdiction_risk_band": "low",
    "jurisdiction_risk": {"iso2": "DE", "risk_band": "low", "risk_score": 25, "cpi_score": 75},
    "binding": {"matched": True, "method": "tls_org"},
    "evidence": [
        {"signal": "entity_in_register", "source": "gleif", "value": "AURORA LINEN GMBH"},
        {"signal": "domain_tls_org_match", "source": "tls_cert", "value": "AURORA LINEN GMBH"},
        {"signal": "vat_active", "source": "vies", "value": "DE811569869"},
    ],
    "layers": {
        "coherence": {
            "entity_exists": True, "entity_found": True, "entity_gone": False,
            "domain_binding": True, "binding_matched": True, "binding_method": "tls_org",
            "reachable": True, "state": "bound", "vat_conflict": False, "non_negotiable": True,
        },
        "commercial_health": {"known": True, "distressed": False, "state": "healthy"},
        "compliance": {
            "default_action": "allow", "sanctions_hit": False, "ubo_sanctions_hit": False,
            "state": "clear", "non_negotiable_default": True,
        },
    },
}

_CLONE = {
    "domain": "aurora-boutique-official.shop",
    "domain_bound": False,
    "entity_resolves": True,          # the clone presents a REAL brand that exists in registers
    "bound_entity": None,
    "register_name": "AURORA LINEN GMBH",
    "score": 11,
    "verdict": "clone_suspected",
    "recommended_action": "block",
    "buyer_warning": "The brand shown exists, but this domain is not the brand's verified domain. "
                     "Registered ~6 days ago; no binding to the registered entity. Do not pay.",
    "jurisdiction_risk_band": "low",
    "jurisdiction_risk": {"iso2": "DE", "risk_band": "low", "risk_score": 25, "cpi_score": 75},
    "binding": {"matched": False, "method": "tls_org"},
    "evidence": [
        {"signal": "entity_in_register", "source": "gleif", "value": "AURORA LINEN GMBH"},
        {"signal": "domain_age_days", "source": "rdap", "value": "6"},
        {"signal": "domain_tls_org_match", "source": "tls_cert", "value": None},
        {"signal": "lookalike_of", "source": "brand_permutation", "value": "aurora-linen.example"},
    ],
    "layers": {
        "coherence": {
            "entity_exists": True, "entity_found": True, "entity_gone": False,
            "domain_binding": False, "binding_matched": False, "binding_method": "tls_org",
            "reachable": True, "state": "unbound", "vat_conflict": False, "non_negotiable": True,
        },
        "commercial_health": {"known": False, "distressed": False, "state": "unknown"},
        "compliance": {
            "default_action": "block", "sanctions_hit": False, "ubo_sanctions_hit": False,
            "state": "clear", "non_negotiable_default": True,
        },
    },
}

# A sanctioned-merchant fixture, for the third demo beat if desired.
_SANCTIONED = {
    "domain": "ural-trading-export.example",
    "domain_bound": True,
    "entity_resolves": True,
    "bound_entity": "URAL TRADING LLC",
    "register_name": "URAL TRADING LLC",
    "score": 0,
    "verdict": "blocked_sanctions",
    "recommended_action": "block",
    "buyer_warning": "A beneficial owner of this merchant appears on a sanctions list. Payment is prohibited.",
    "jurisdiction_risk_band": "high",
    "jurisdiction_risk": {"iso2": "RU", "risk_band": "high", "risk_score": 86, "cpi_score": 22},
    "binding": {"matched": True, "method": "tls_org"},
    "evidence": [{"signal": "ubo_sanctions_match", "source": "eu_consolidated", "value": "1 owner matched"}],
    "layers": {
        "coherence": {"entity_exists": True, "domain_binding": True, "binding_matched": True,
                      "reachable": True, "state": "bound", "vat_conflict": False, "non_negotiable": True},
        "commercial_health": {"known": True, "distressed": False, "state": "healthy"},
        "compliance": {"default_action": "block", "sanctions_hit": True, "ubo_sanctions_hit": True,
                       "state": "hit", "non_negotiable_default": True},
    },
}

DEMO_RESPONSES = {
    "aurora-linen.example": _VERIFIED,
    "aurora-boutique-official.shop": _CLONE,
    "ural-trading-export.example": _SANCTIONED,
}


def demo_response(domain: str) -> dict:
    """Return a fixture for a known demo domain, else a generic 'unreachable'
    response (mirrors what the live API returns when it cannot fetch a site)."""
    key = (domain or "").lower().replace("https://", "").replace("http://", "").strip("/").split("/")[0]
    if key.startswith("www."):
        key = key[4:]
    if key in DEMO_RESPONSES:
        return dict(DEMO_RESPONSES[key])
    return {
        "domain": key,
        "domain_bound": None,
        "entity_resolves": None,
        "buyer_warning": None,
        "verdict": "unverifiable_unreachable",
        "layers": {"coherence": {"reachable": False, "state": "unreachable"},
                   "compliance": {"default_action": None, "sanctions_hit": False}},
        "_demo_note": "Unknown demo domain — try aurora-linen.example or aurora-boutique-official.shop, "
                      "or set ACURIS_API_KEY for live verification.",
    }
