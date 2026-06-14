"""Acuris storefront verifier client — the one call you put in your agent's loop.

    from acuris_agent_guard import StorefrontVerifier
    v = StorefrontVerifier()                 # demo mode (no key) — runs offline
    verdict = v.verify("aurora-boutique-official.shop", name="Aurora Linen")
    if not verdict.safe_to_pay:
        abort(verdict.reason)

Modes:
  - demo  (default when no API key): returns faithful fixtures, zero setup.
  - live  (ACURIS_API_KEY set, or api_key=...): calls POST /storefront-verify.
Only the Python stdlib is used, so the core has no dependencies.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

from .fixtures import demo_response
from .verdict import StorefrontVerdict, decide

DEFAULT_BASE_URL = "https://api.acuris-geo.com"
USER_AGENT = "acuris-agent-guard/0.1.1"


class StorefrontVerifier:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 8.0,
        mode: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("ACURIS_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # mode: "live" | "demo". Default to live iff a key is present.
        self.mode = mode or ("live" if self.api_key else "demo")

    def verify(
        self,
        url_or_domain: str,
        *,
        name: Optional[str] = None,
        vat: Optional[str] = None,
        lei: Optional[str] = None,
        country: Optional[str] = None,
    ) -> StorefrontVerdict:
        """Verify a storefront. `name`/`vat`/`lei` is the entity the storefront
        claims to be (at least one recommended so binding can be judged)."""
        if self.mode == "demo":
            return decide(demo_response(url_or_domain))
        return decide(self._call_live(url_or_domain, name=name, vat=vat, lei=lei, country=country))

    # -- internal ---------------------------------------------------------
    def _call_live(self, url_or_domain, *, name, vat, lei, country) -> dict:
        body = {"domain": url_or_domain}
        if name:
            body["name"] = name
        if vat:
            body["vat"] = vat
        if lei:
            body["lei"] = lei
        if country:
            body["country"] = country
        data = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        if self.api_key:
            headers["X-Acuris-Key"] = self.api_key
        req = urllib.request.Request(
            f"{self.base_url}/storefront-verify", data=data, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode("utf-8"))
            except Exception:
                return {"domain": url_or_domain, "error": f"http_{e.code}",
                        "layers": {"coherence": {"reachable": False, "state": "error"},
                                   "compliance": {"default_action": None}}}
        except Exception as e:  # network/timeout — fail to REVIEW, never silently PROCEED
            return {"domain": url_or_domain, "error": str(e),
                    "layers": {"coherence": {"reachable": False, "state": "error"},
                               "compliance": {"default_action": None}}}
