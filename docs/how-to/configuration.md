# :material-cog:{.scale-in-center} Configuration

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOUDINI_HOST` | `localhost` | Houdini host address |
| `HOUDINI_PORT` | `8100` | Houdini hwebserver port |
| `FXHOUDINIMCP_PORT` | `8100` | Port for the Houdini plugin to listen on |
| `FXHOUDINIMCP_AUTOSTART` | `1` | Set to `0` to disable auto-start |
| `MCP_TRANSPORT` | `stdio` | MCP transport (`stdio` or `streamable-http`) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Auto-Start

The Houdini plugin auto-starts when the UI is ready via `uiready.py`, which
stacks cleanly with other Houdini packages. Startup registers the MCP endpoints,
starts Houdini's `hwebserver` when needed, and verifies that `mcp.health`
answers from the current Houdini process before reporting readiness. Disable
auto-start by setting:

``` shell
export FXHOUDINIMCP_AUTOSTART=0
```

You can still toggle the server manually using the **MCP Server** shelf tool.

If an assistant cannot reach Houdini, use `get_houdini_connection_status` to
return structured diagnostics without raising a tool error. If port `8100` is
owned by a different Houdini process, either close that process or set both
`FXHOUDINIMCP_PORT` and `HOUDINI_PORT` to a matching free port.

## Transport Modes

### stdio (Default)

The AI client spawns the MCP server as a child process. Communication happens over stdin/stdout. This is the simplest setup, no ports or networking required on the MCP side.

### streamable-http

Runs the MCP server as an HTTP endpoint. Useful for remote or shared setups:

``` shell
export MCP_TRANSPORT=streamable-http
python -m fxhoudinimcp
```

## Custom Port

If Houdini's hwebserver is already bound to port 8100, configure a different port:

1. Set `FXHOUDINIMCP_PORT` in your Houdini environment
2. Set `HOUDINI_PORT` in your MCP client config to match
