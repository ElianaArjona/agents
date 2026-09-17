"""Configuration helpers for restricting the MCP tools exposed by the server."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def parse_allowed_tools(value: str | None) -> frozenset[str] | None:
    """Parse the comma-separated ASTRO_MCP_ALLOWED_TOOLS setting.

    An unset value means no restriction. An explicitly empty value or an empty
    entry is a configuration error, never a fallback to unrestricted access.
    Names are case-sensitive; whitespace and duplicate names are ignored.

    This only validates the list format. Tool names must also be checked against
    the server's registered tools before applying the policy.
    """
    if value is None:
        return None

    names = [name.strip() for name in value.split(",")]
    if any(not name for name in names):
        raise ValueError(
            "ASTRO_MCP_ALLOWED_TOOLS must be a comma-separated list of tool names "
            "with no empty entries. Unset it to allow all tools."
        )

    return frozenset(names)


async def apply_tool_allowlist(server: "FastMCP", allowed_tools: frozenset[str] | None) -> None:
    """Validate and apply a static tool allowlist before serving requests.

    FastMCP visibility controls filter both discovery and invocation. Resources
    and prompts are unaffected. Call after tools have been registered.
    """
    if allowed_tools is None:
        return

    registered_tools = {tool.name for tool in await server.list_tools(run_middleware=False)}
    unknown = allowed_tools - registered_tools
    if unknown:
        raise ValueError(
            "Unknown tool names in ASTRO_MCP_ALLOWED_TOOLS: " + ", ".join(sorted(unknown))
        )

    # Separate disable/enable calls keep the restriction scoped to tools.
    # FastMCP's enable(only=True) also disables resources and prompts.
    server.disable(components={"tool"})
    if allowed_tools:
        server.enable(names=set(allowed_tools), components={"tool"})
