make sure to remove the deprecation warnings:
2025-08-12 17:50:00,854 - __main__ - INFO - 📤 Server: 2025-08-12 17:50:00,854 - mcp.server.lowlevel.server - INFO - Warning: DeprecationWarning: Context.get_http_request() is deprecated and will be removed in a future version. Use get_http_request() from fastmcp.server.dependencies instead. See https://gofastmcp.com/patterns/http-requests for more details.
2025-08-12 17:50:10,726 - __main__ - INFO - 📤 Server: 2025-08-12 17:50:10,726 - mcp.server.lowlevel.server - INFO - Warning: DeprecationWarning: Context.get_http_request() is deprecated and will be removed in a future version. Use get_http_request() from fastmcp.server.dependencies instead. See https://gofastmcp.com/patterns/http-requests for more details.
2025-08-12 17:50:10,773 - __main__ - INFO - 📤 Server: 2025-08-12 17:50:10,773 - mcp.server.lowlevel.server - INFO - Warning: DeprecationWarning: Context.get_http_request() is deprecated and will be removed in a future version. Use get_http_request() from fastmcp.server.dependencies instead. See https://gofastmcp.com/patterns/http-requests for more details.
2025-08-12 17:50:10,816 - __main__ - INFO - 📤 Server: 2025-08-12 17:50:10,816 - mcp.server.lowlevel.server - INFO - Warning: DeprecationWarning: Context.get_http_request() is deprecated and will be removed in a future version. Use get_http_request() from fastmcp.server.dependencies instead. See https://gofastmcp.com/patterns/http-requests for more details.
2025-08-12 17:50:10,855 - __main__ - INFO - 📤 Server: 2025-08-12 17:50:10,855 - mcp.server.lowlevel.server - INFO - Warning: DeprecationWarning: Context.get_http_request() is deprecated and will be removed in a future version. Use get_http_request() from fastmcp.server.dependencies instead. See https://gofastmcp.com/patterns/http-requests for more details.
2025-08-12 17:50:10,897 - __main__ - INFO - 📤 Server: 2025-08-12 17:50:10,897 - mcp.server.lowlevel.server - INFO - Warning: DeprecationWarning: Context.get_http_request() is deprecated and will be removed in a future version. Use get_http_request() from fastmcp.server.dependencies instead. See https://gofastmcp.com/patterns/http-requests for more details.
2025-08-12 17:50:17,353 - __main__ - INFO - 📤 Server: 2025-08-12 17:50:17,353 - mcp.server.lowlevel.server - INFO - Warning: DeprecationWarning: Context.get_http_request() is deprecated and will be removed in a future version. Use get_http_request() from fastmcp.server.dependencies instead. See https://gofastmcp.com/patterns/http-requests for more details.
2025-08-12 17:50:17,394 - __main__ - INFO - 📤 Server: 2025-08-12 17:50:17,394 - mcp.server.lowlevel.server - INFO - Warning: DeprecationWarning: Context.get_http_request() is deprecated and will be removed in a future version. Use get_http_request() from fastmcp.server.dependencies instead. See https://gofastmcp.com/patterns/http-requests for more details.
2025-08-12 17:50:17,434 - __main__ - INFO - 📤 Server: 2025-08-12 17:50:17,434 - mcp.server.lowlevel.server - INFO - Warning: DeprecationWarning: Context.get_http_request() is deprecated and will be removed in a future version. Use get_http_request() from fastmcp.server.dependencies instead. See https://gofastmcp.com/patterns/http-requests for more details.
2025-08-12 17:50:22,777 - __main__ - INFO - 📤 Server: 2025-08-12 17:50:22,777 - mcp.server.lowlevel.server - INFO - Warning: DeprecationWarning: Context.get_http_request() is deprecated and will be removed in a future version. Use get_http_request() from fastmcp.server.dependencies instead. See https://gofastmcp.com/patterns/http-requests for more details.
also look into this message:
 /Users/Ricardo_Leon1/TestIO/shared-context-server/.venv/lib/python3.12/site-packages/websockets/
    legacy/server.py:1178: DeprecationWarning: remove second argument of ws_handler
      warnings.warn("remove second argument of ws_handler", DeprecationWarning)


in dashboard: created seems to always display just now (probably timezone issues?) look into this - it may have been fixed by recent datetime changes


display all timestamps in webui in local time, not utc
can we also show more precision? 2 decimals on seconds?

can we also realtime update the number of active session in dashboard?
this might(?) require some actual state management, so we may want to consider moving away from this prototype with raw html and css and to using a proper web frontend framework

we'll also want basic CRUD for sessions and messages directly from WebUI
being able to edit messages posted by AI to fix mistakes or clarify on the fly without stopping it could be useful?

This will probably require we set up integration with auth so that webui is properly authenticated with
admin role and privileges

we need to think of edge cases (like very long messages) and how to handle them
