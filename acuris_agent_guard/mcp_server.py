"""MCP server exposing `verify_storefront` so ANY MCP-capable agent (Claude
Desktop, Claude Code, and other MCP clients) gains a pre-pay merchant check
with one config-file line.

Run:
    pip install "acuris-agent-guard[mcp]"
    python -m acuris_agent_guard.mcp_server          # stdio

Claude Desktop / Claude Code config (mcpServers):
    {
      "acuris": {
        "command": "python",
        "args": ["-m", "acuris_agent_guard.mcp_server"],
        "env": { "ACURIS_API_KEY": "your-key (omit for offline demo mode)" }
      }
    }

Then tell the agent: "Before paying any merchant, call verify_storefront and
abort if it is not safe_to_pay."
"""

from __future__ import annotations

from typing import Optional

from .client import StorefrontVerifier

try:
    from mcp.server.fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "The MCP SDK is required: pip install 'acuris-agent-guard[mcp]' "
        "(or pip install mcp). Original import error: %s" % e
    )

mcp = FastMCP("acuris-agent-guard")
_verifier = StorefrontVerifier()


@mcp.tool()
def verify_storefront(
    url: str,
    name: Optional[str] = None,
    vat: Optional[str] = None,
    lei: Optional[str] = None,
    country: Optional[str] = None,
) -> dict:
    """Verify a merchant/storefront BEFORE paying it.

    Checks whether the domain belongs to a real, operating, sanctions-clean
    registered legal entity (address valid, company exists, website bound to
    that entity, sanctions clear). Call this before any payment/checkout action
    and DO NOT pay if `safe_to_pay` is false.

    Args:
        url: the storefront domain or URL the agent is about to pay.
        name/vat/lei: the entity the storefront claims to be (provide at least
            one so domain↔entity binding can be judged).
        country: ISO-3166 alpha-2 or alpha-3 hint, optional.

    Returns a verdict dict: {decision: PROCEED|ABORT|REVIEW, safe_to_pay: bool,
        reason, signals{domain_bound, entity_resolves, sanctions_hit, ...}}.
    """
    v = _verifier.verify(url, name=name, vat=vat, lei=lei, country=country)
    out = v.to_dict()
    out["safe_to_pay"] = v.safe_to_pay
    return out


def main():
    mcp.run()


if __name__ == "__main__":
    main()
