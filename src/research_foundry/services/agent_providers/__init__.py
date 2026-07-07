"""Agent providers package — re-exports from :mod:`.base` and concrete providers."""

from research_foundry.services.agent_providers.base import (
    BaseProvider,
    ResearchAgentProvider,
    all_providers,
    get_provider,
    register,
)

# Concrete provider imports trigger module-level register() calls.
from research_foundry.services.agent_providers.claude_agent_sdk_provider import (  # noqa: F401
    ClaudeAgentSDKProvider,
)
from research_foundry.services.agent_providers.openai_agents_provider import (  # noqa: F401
    OpenAIAgentsProvider,
)

__all__ = [
    "ResearchAgentProvider",
    "BaseProvider",
    "register",
    "get_provider",
    "all_providers",
    "ClaudeAgentSDKProvider",
    "OpenAIAgentsProvider",
]
