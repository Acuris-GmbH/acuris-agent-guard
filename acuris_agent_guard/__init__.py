"""acuris-agent-guard — verify the merchant before your AI agent pays.

One pre-pay check that answers: is this storefront a real, operating,
sanctions-clean legal entity that actually controls the domain it claims?
Plugs into LangChain, CrewAI, Anthropic computer-use, or any MCP-capable agent.
"""

from .client import StorefrontVerifier
from .guard import PaymentBlocked, pre_pay_guard
from .verdict import ABORT, PROCEED, REVIEW, StorefrontVerdict, decide

__version__ = "0.1.0"
__all__ = [
    "StorefrontVerifier",
    "pre_pay_guard",
    "PaymentBlocked",
    "StorefrontVerdict",
    "decide",
    "PROCEED",
    "ABORT",
    "REVIEW",
]
