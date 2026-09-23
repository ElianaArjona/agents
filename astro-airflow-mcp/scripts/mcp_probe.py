"""Probe an MCP endpoint to verify the tool allowlist end to end.

Usage:
    uv run python scripts/mcp_probe.py <mcp_url> [bearer_token]

Examples:
    uv run python scripts/mcp_probe.py http://localhost:8000/mcp/
    uv run python scripts/mcp_probe.py http://localhost:8081/mcp/v1/ "$TOKEN"

Checks, in order:
1. tools/list — prints every advertised tool name.
2. tools/call list_dags — an allowed tool must execute (an Airflow auth
   error still counts as "executed"; only "unknown tool" is a failure).
3. tools/call get_variable — an excluded tool must be rejected as unknown.
4. resources and prompts — must remain available regardless of the allowlist.
"""

import asyncio
import sys

from fastmcp import Client
from fastmcp.exceptions import ToolError


async def main(url: str, token: str | None) -> None:
    kwargs = {"auth": token} if token else {}
    async with Client(url, **kwargs) as client:
        tools = sorted(t.name for t in await client.list_tools())
        print(f"tools/list -> {len(tools)} tools: {', '.join(tools)}")

        if "list_dags" in tools:
            try:
                result = await client.call_tool("list_dags", {})
                print(f"list_dags -> executed, {len(result.content[0].text)} bytes")
            except ToolError as exc:
                print(f"list_dags -> tool error (still executed): {exc}")

        try:
            await client.call_tool("get_variable", {"variable_key": "probe"})
            print("get_variable -> EXECUTED (fails the excluded-tool check if excluded)")
        except ToolError as exc:
            print(f"get_variable -> rejected: {exc}")

        resources = await client.list_resources()
        prompts = await client.list_prompts()
        print(f"resources: {len(resources)}, prompts: {len(prompts)} (both must be > 0)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
