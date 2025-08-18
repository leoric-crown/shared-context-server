we should also think about adding authentication and token refresh events and memory setting and getting events to the chat history / logs in our ui

in dashboard: we are limiting query to 50 results, but we also need to display a total count of sessions (right now we have more than 50, but the ui says 50 sessions)
in dashboard: created seems to always display just now (probably timezone issues?) look into this - it may have been fixed by recent datetime changes


display all timestamps in webui in local time, not utc
can we also show more precision? 2 decimals on seconds?

can we also realtime update the number of active session in dashboard?
this might(?) require some actual state management, so we may want to consider moving away from this prototype with raw html and css and to using a proper web frontend framework

we'll also want basic CRUD for sessions and messages directly from WebUI
being able to edit messages posted by AI or post new User messages to fix mistakes or clarify on the fly without stopping it could be useful?

This will probably require we set up integration with auth so that webui is properly authenticated with
admin role and privileges

we need to think of edge cases (like very long messages) and how to handle them

feature: provide a way to flag a session as important
feature: building on the above, provide a way to tag sessions
