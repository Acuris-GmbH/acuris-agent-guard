"""Decision-logic tests — the load-bearing part (maps API signals → PROCEED/ABORT/REVIEW)."""

from acuris_agent_guard import PaymentBlocked, StorefrontVerifier, decide, pre_pay_guard
from acuris_agent_guard.verdict import ABORT, PROCEED, REVIEW


def _raw(**coh):
    base = {"domain": "x.example", "domain_bound": True, "entity_resolves": True,
            "layers": {"coherence": {"reachable": True}, "compliance": {}}}
    base["layers"]["coherence"].update(coh)
    return base


def test_verified_proceeds():
    r = _raw()
    assert decide(r).decision == PROCEED


def test_recommended_action_drives_decision():
    # The SDK maps the engine's authoritative action; it does NOT re-derive.
    def mk(action):
        return {"domain": "x.example", "domain_bound": False, "entity_resolves": True,
                "recommended_action": action,
                "layers": {"coherence": {"reachable": True}, "compliance": {}}}
    assert decide(mk("proceed")).decision == PROCEED
    assert decide(mk("review")).decision == REVIEW
    assert decide(mk("do_not_proceed")).decision == REVIEW
    assert decide(mk("block")).decision == ABORT


def test_legit_review_store_is_not_called_a_clone():
    # Regression (the 28-store bug): a real entity on a DV cert (unbound) gets
    # engine action `review`. The SDK must return REVIEW, NOT ABORT "likely a clone".
    r = {"domain": "walmart.com", "domain_bound": False, "entity_resolves": True,
         "recommended_action": "review", "register_name": "Walmart Inc.",
         "layers": {"coherence": {"reachable": True}, "compliance": {}}}
    v = decide(r)
    assert v.decision == REVIEW
    assert "clone" not in v.reason.lower()


def test_engine_block_surfaces_buyer_warning():
    r = {"domain": "clone.shop", "domain_bound": False, "entity_resolves": True,
         "recommended_action": "block",
         "buyer_warning": "This domain is not the brand's verified domain. Do not pay.",
         "layers": {"coherence": {"reachable": True}, "compliance": {}}}
    v = decide(r)
    assert v.decision == ABORT and "verified domain" in v.reason


def test_unbound_without_action_is_review_not_clone():
    # No recommended_action (old API / transport error) -> conservative fallback,
    # never an ABORT-as-clone on a merely unbound store.
    r = {"domain": "clone.shop", "domain_bound": False, "entity_resolves": True,
         "layers": {"coherence": {"reachable": True}, "compliance": {}}}
    v = decide(r)
    assert v.decision == REVIEW and "clone" not in v.reason.lower()


def test_no_entity_aborts():
    r = {"domain": "fake.shop", "domain_bound": False, "entity_resolves": False,
         "layers": {"coherence": {"reachable": True}, "compliance": {}}}
    assert decide(r).decision == ABORT


def test_sanctions_aborts_even_if_bound():
    r = {"domain": "ural.example", "domain_bound": True, "entity_resolves": True,
         "layers": {"coherence": {"reachable": True}, "compliance": {"sanctions_hit": True}}}
    v = decide(r)
    assert v.decision == ABORT and "sanction" in v.reason.lower()


def test_unreachable_is_review_not_proceed():
    r = {"domain": "x.example", "domain_bound": None, "entity_resolves": None,
         "layers": {"coherence": {"reachable": False}, "compliance": {}}}
    assert decide(r).decision == REVIEW


def test_compliance_block_aborts():
    r = {"domain": "x.example", "domain_bound": True, "entity_resolves": True,
         "layers": {"coherence": {"reachable": True}, "compliance": {"default_action": "block"}}}
    assert decide(r).decision == ABORT


def test_demo_fixtures_end_to_end():
    v = StorefrontVerifier(mode="demo")
    assert v.verify("aurora-linen.example").decision == PROCEED
    assert v.verify("aurora-boutique-official.shop").decision == ABORT
    assert v.verify("ural-trading-export.example").decision == ABORT  # sanctions


def test_guard_raises_on_clone_and_passes_verified():
    vf = StorefrontVerifier(mode="demo")
    assert pre_pay_guard("aurora-linen.example", verifier=vf).safe_to_pay is True
    try:
        pre_pay_guard("aurora-boutique-official.shop", verifier=vf)
        assert False, "should have raised"
    except PaymentBlocked as e:
        assert e.verdict.decision == ABORT


def test_guard_blocks_review_when_failing_closed():
    vf = StorefrontVerifier(mode="demo")
    # unknown domain -> unreachable -> REVIEW; default block_on_review=True -> raises
    try:
        pre_pay_guard("some-unknown-domain.example", verifier=vf)
        assert False, "should fail closed on REVIEW"
    except PaymentBlocked:
        pass
    # block_on_review=False -> returns the REVIEW verdict instead of raising
    v = pre_pay_guard("some-unknown-domain.example", verifier=vf, block_on_review=False)
    assert v.decision == REVIEW
