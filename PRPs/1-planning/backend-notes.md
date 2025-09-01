create_session should also require the initial message (this will avoid any sessions with 0 messages)

we also need smarter fetching mechanisms:
- we could build a new tool (get_session_updates / get_new_messages / or something like that) that fetches new messages since last time this token requested messages.

however, we must consider how this pattern would work if the same token is reused across multiple agent calls.
we may want to consider adding guidance in usage_guidance to always provide a fresh token to a new agent call.
this is specially important in the current subagents implementation of claude code.
OR simply allow callers to override this behaviour with a parameter fetch_all = true (default=false), fresh agents should be smart enough to use this as they would not have any messages in their context window.

this would require a new table / tracking mechanism for token requests per session so that we can easily select the messages to return.

search by sender could use some smart logic to translate 'cursor analyst'/'cursor_analyst' -> cursor-analyst [all case insensitive] (i.e. make it possible to find messages by sender if we provide a semantically nearly identical agent name?) - also/alternatively enforce a format for sender identities? kebab-case or snake_case?
