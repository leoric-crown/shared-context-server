we should think about adding authentication and token refresh events as well as memory setting and getting events to the chat history / logs in our ui

right now, all sessions are active or at least we have no clear way of identifying inactive sessions - we need to think more about session lifecycle management in general.

in dashboard: we are limiting query to 50 results, but we also need to display a total count of sessions (right now if we have more than 50, the ui says 50 sessions)

display all timestamps in webui in local time, not utc

can we also realtime update the number of active session in dashboard?
this might(?) require some actual state management, so we may want to consider moving away from this prototype with raw html and css and to using a proper web frontend framework

we'll also want basic CRUD for sessions and messages directly from WebUI
being able to edit messages posted by AI or post new User messages to fix mistakes or clarify on the fly without stopping it could be useful?

This will probably require we set up integration with auth so that webui is properly authenticated with
admin role and privileges

we need to think of edge cases (like very long messages) and how to handle/display them

apply markdown rendering to agent's responses
apply code syntax highlighting for fenced code blocks

feature: provide a way to flag/star a session as important
feature: building on the above, provide a way to tag sessions

let's get a proper logo / favicon? - to quickly identify SCS WebUI browser tabs
