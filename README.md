# Acuris Agent Guard

**Verify the merchant before your AI agent pays.**

When an AI agent shops on someone's behalf, the entire trust stack verifies the
*buyer's agent* (Visa Trusted Agent Protocol, Mastercard Agent Pay) — and
**nobody verifies the merchant.** Agents don't read the URL bar or sniff a
"too good to be true" deal; they autofill the saved card and pay. Security
researchers have already shown agentic browsers checking out on fake stores
([Guardio "Scamlexity"](https://guard.io/labs), 2025), and AI assistants
surface clone storefronts on look-alike domains
([Netcraft](https://www.netcraft.com/blog): 34% of brand URLs returned by an
LLM weren't brand-owned).

`acuris-agent-guard` is the one pre-pay check that answers:

> **Is this storefront a real, operating, sanctions-clean legal entity that
> actually controls the domain it claims?**

`{ address_valid, company_exists, website_bound, sanctions }` → one decision:
**PROCEED / ABORT / REVIEW.** The differentiator is **`website_bound`** —
catching a clone that shows a *real* company's name/VAT on a fresh look-alike
domain, which a plain "does this company exist?" check waves through.

## See it in 10 seconds (zero setup, runs offline)

Install into a virtualenv (recommended — modern Debian/Ubuntu block `pip` into
the system Python with an `externally-managed-environment` error; that's an OS
guard, not this package):

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install git+https://github.com/Acuris-GmbH/acuris-agent-guard   # PyPI: pip install acuris-agent-guard (coming soon)
python -m acuris_agent_guard.demo
```

Prefer an isolated CLI? `pipx install git+https://github.com/Acuris-GmbH/acuris-agent-guard` works too.

The same autonomous agent, same task, same clone — one checks the merchant first:

```
task: Buy the Aurora Linen Dress for me.

AGENT A — WITHOUT Acuris
  • top result = aurora-boutique-official.shop → choosing it
  • autofill saved card + shipping address → submit payment … €149
  ✗ Payment sent. €149 gone. Goods never arrive.   (clone, 6-day-old domain)

AGENT B — WITH Acuris guard
  • pre-pay check → acuris.verify_storefront("aurora-boutique-official.shop")
    ↩ ABORT  domain_bound=False  entity_resolves=True
    reason: This domain is NOT bound to the registered company it claims — likely a clone.
  ✓ Purchase ABORTED. €149 protected.
  • fall back to aurora-linen.example → PROCEED (bound to AURORA LINEN GMBH)
  ✓ Paid the real Aurora Linen GmbH.
```

> Demo mode ships faithful, illustrative responses so it runs with no key.
> Set `ACURIS_API_KEY` (and pass `--live`) to hit the real API.

## Where it plugs into your loop

### Any MCP agent (Claude Desktop / Claude Code / others) — one config line
First install the MCP extra into a venv (`pip install "acuris-agent-guard[mcp] @
git+https://github.com/Acuris-GmbH/acuris-agent-guard"`), then point the config
at that venv's Python (use the absolute path, or `pipx`, so it resolves
regardless of the system Python):
```jsonc
"mcpServers": {
  "acuris": {
    "command": "/path/to/.venv/bin/python",
    "args": ["-m", "acuris_agent_guard.mcp_server"],
    "env": { "ACURIS_API_KEY": "your-key" }   // omit for offline demo mode
  }
}
```
Then: *"Before paying any merchant, call `verify_storefront` and abort if it is
not `safe_to_pay`."*

### Plain Python (framework-agnostic guardrail)
```python
from acuris_agent_guard import pre_pay_guard, PaymentBlocked

try:
    pre_pay_guard("aurora-boutique-official.shop", name="Aurora Linen")  # raises if unsafe
    charge_card(...)                                                      # only runs if verified
except PaymentBlocked as e:
    agent.note(str(e))   # do not pay; route to a verified seller
```

### LangChain — `integrations/langchain_guard.py`
Adds `verify_storefront` as a tool **and** wraps your real pay tool so payment
is structurally impossible unless the storefront verifies (don't rely on the
model remembering to check).

### Anthropic computer-use — `integrations/computer_use_guard.py`
Intercepts the action loop right before a "place order / pay" click; if the
storefront fails, the click never executes and the block is fed back to the
model as the tool result so it re-plans.

## The verdict

```python
from acuris_agent_guard import StorefrontVerifier
v = StorefrontVerifier().verify("aurora-boutique-official.shop", name="Aurora Linen")
v.decision        # "ABORT"
v.safe_to_pay     # False
v.reason          # "This domain is NOT bound to the registered company ..."
v.to_dict()       # full structured signals + score + evidence
```

The decision is derived from structured signals (`domain_bound`,
`entity_resolves`, `sanctions_hit`, reachability), and **fails closed** — an
unreachable/unverifiable storefront returns `REVIEW`, never a silent `PROCEED`.

## Honest scope
- A pre-pay **risk signal**, not fraud insurance, not a delivery guarantee, and
  not a certification. It catches impersonation / fabrication / sanctions — it
  cannot predict whether a *genuine* registered merchant will fail to ship.
- Domain↔entity binding is **inferred** from official registers + corroborating
  signals (TLS org, domain age, VAT), since WHOIS/RDAP is largely GDPR-redacted.
- It is not an anti-prompt-injection control; it scores the *merchant*, so wire
  it as a hard guardrail on the payment step, not an optional tool.

MIT © Acuris GmbH · built on the [Acuris](https://acuris-geo.com) trust-data API.
