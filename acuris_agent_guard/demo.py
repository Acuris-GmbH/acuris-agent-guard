"""Side-by-side demo: the same autonomous shopping agent, with and without the
Acuris guard, told to buy a product from "the cheapest site it can find" — where
the cheapest site is a clone.

    python -m acuris_agent_guard.demo            # offline demo mode, ANSI output
    ACURIS_API_KEY=... python -m acuris_agent_guard.demo --live

This is the runnable twin of the website animation. Zero dependencies.
"""

from __future__ import annotations

import os
import sys
import time

from .client import StorefrontVerifier
from .guard import PaymentBlocked, pre_pay_guard

# ANSI
R = "\033[31m"; G = "\033[32m"; Y = "\033[33m"; B = "\033[36m"; DIM = "\033[2m"; BOLD = "\033[1m"; X = "\033[0m"

PRODUCT = "Aurora Linen Dress"
PRICE = "€149"
TASK = f'Buy the {PRODUCT} ({PRICE}) from the cheapest site you can find.'

# Two candidate stores the "agent" found; the cheapest is the clone.
CLONE = {"domain": "aurora-boutique-official.shop", "name": "Aurora Linen", "price": "€119"}
LEGIT = {"domain": "aurora-linen.example", "name": "Aurora Linen GmbH", "price": "€149"}


def _p(msg, pause):
    print(msg)
    sys.stdout.flush()
    time.sleep(pause)


def run_unprotected(pause):
    print(f"\n{BOLD}{R}╶─ AGENT A — WITHOUT Acuris ─────────────────────────────╴{X}")
    _p(f"{DIM}task:{X} {TASK}", pause)
    _p(f"  • search …  found 2 stores", pause)
    _p(f"  • cheapest = {CLONE['domain']} ({CLONE['price']})  → choosing it", pause)
    _p(f"  • open checkout", pause)
    _p(f"  • {Y}autofill saved card + shipping address{X}", pause)
    _p(f"  • submit payment …", pause)
    _p(f"  {R}{BOLD}✗ Payment sent. {PRICE} gone. Goods never arrive.{X}", pause)
    _p(f"  {R}It was a clone of a real brand on a 6-day-old domain.{X}", pause)
    return False


def run_protected(pause, verifier):
    print(f"\n{BOLD}{G}╶─ AGENT B — WITH Acuris guard ──────────────────────────╴{X}")
    _p(f"{DIM}task:{X} {TASK}", pause)
    _p(f"  • search …  found 2 stores", pause)
    _p(f"  • cheapest = {CLONE['domain']} ({CLONE['price']})  → choosing it", pause)
    _p(f"  • {B}pre-pay check → acuris.verify_storefront(\"{CLONE['domain']}\"){X}", pause)
    try:
        pre_pay_guard(CLONE["domain"], name=CLONE["name"], verifier=verifier)
        paid = CLONE
    except PaymentBlocked as e:
        v = e.verdict
        _p(f"    {R}↩ {v.decision}{X}  domain_bound={v.domain_bound}  entity_resolves={v.entity_resolves}", pause)
        _p(f"    {R}reason: {v.reason}{X}", pause)
        _p(f"  {Y}✓ Purchase ABORTED. {PRICE} protected.{X}", pause)
        _p(f"  • fall back to next store = {LEGIT['domain']} ({LEGIT['price']})", pause)
        _p(f"  • {B}pre-pay check → acuris.verify_storefront(\"{LEGIT['domain']}\"){X}", pause)
        try:
            ok = pre_pay_guard(LEGIT["domain"], name=LEGIT["name"], verifier=verifier)
            _p(f"    {G}↪ {ok.decision}{X}  bound to {BOLD}{ok.entity_name}{X}  ({ok.reason})", pause)
            paid = LEGIT
        except PaymentBlocked:
            _p(f"  {Y}No verified store found — agent declines to pay. Funds safe.{X}", pause)
            return True
    _p(f"  • pay {paid['price']} to verified merchant", pause)
    _p(f"  {G}{BOLD}✓ Paid the real {paid['name']}. Right goods, right seller.{X}", pause)
    return True


def main(argv=None):
    argv = argv or sys.argv[1:]
    live = "--live" in argv
    fast = "--fast" in argv
    pause = 0.0 if fast else 0.7
    verifier = StorefrontVerifier(mode="live" if live else "demo")

    print(f"{BOLD}Acuris Agent Guard — live demo{X}  {DIM}({'LIVE api' if live else 'offline demo mode'}){X}")
    print(f"{DIM}Same agent, same task, same clone. One checks the merchant first.{X}")
    run_unprotected(pause)
    run_protected(pause, verifier)
    print(f"\n{DIM}One API call in the agent's pre-pay step is the whole difference.{X}")
    print(f"{DIM}Illustrative demo. Acuris verifies merchant legitimacy from official registers before an agent pays.{X}\n")


if __name__ == "__main__":
    main()
