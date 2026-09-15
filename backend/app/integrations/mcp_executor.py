import asyncio
from typing import Any

from app.core.authorization.tool_gateway import ToolExecutor
from app.integrations.mcp_client import (
    McpStdioClientAdapter,
    McpStdioServerConfig,
)


def build_stdio_mcp_executor(
    config: McpStdioServerConfig,
) -> ToolExecutor:
    """Build a synchronous SafetyGate tool executor backed by MCP."""

    adapter = McpStdioClientAdapter(config)

    def execute(
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        return asyncio.run(
            adapter.call_tool(
                tool_name,
                arguments,
            )
        )

    return execute
