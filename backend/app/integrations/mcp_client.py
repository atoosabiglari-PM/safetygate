from dataclasses import dataclass
from typing import Any

from mcp import Client, StdioServerParameters


class McpClientError(RuntimeError):
    """Raised when an MCP operation cannot complete safely."""


@dataclass(frozen=True)
class McpToolDescriptor:
    name: str
    title: str | None
    description: str | None
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class McpStdioServerConfig:
    command: str
    args: tuple[str, ...] = ()
    env: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.command.strip():
            raise ValueError("MCP stdio command must be a non-empty string.")

        if any(not argument.strip() for argument in self.args):
            raise ValueError("MCP stdio arguments must be non-empty strings.")

        if any(
            not key.strip() or not value
            for key, value in self.env
        ):
            raise ValueError(
                "MCP stdio environment entries must contain "
                "non-empty keys and values."
            )


class McpStdioClientAdapter:
    """SafetyGate-owned adapter for a trusted stdio MCP server."""

    def __init__(self, config: McpStdioServerConfig) -> None:
        self._config = config

    def _server_parameters(self) -> StdioServerParameters:
        return StdioServerParameters(
            command=self._config.command,
            args=list(self._config.args),
            env=dict(self._config.env),
        )

    async def list_tools(self) -> tuple[McpToolDescriptor, ...]:
        try:
            async with Client(self._server_parameters()) as client:
                result = await client.list_tools()
        except Exception as exc:
            raise McpClientError(
                "MCP tool discovery failed."
            ) from exc

        return tuple(
            McpToolDescriptor(
                name=tool.name,
                title=tool.title,
                description=tool.description,
                input_schema=dict(tool.input_schema),
            )
            for tool in result.tools
        )

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        if not tool_name.strip():
            raise ValueError("MCP tool name must be a non-empty string.")

        try:
            async with Client(self._server_parameters()) as client:
                result = await client.call_tool(
                    tool_name,
                    arguments=arguments,
                )
        except Exception as exc:
            raise McpClientError(
                "MCP tool execution failed."
            ) from exc

        if result.is_error:
            raise McpClientError(
                "MCP tool returned an error result."
            )

        return {
            "structured_content": result.structured_content,
            "content": [
                block.model_dump(mode="json")
                for block in result.content
            ],
        }
