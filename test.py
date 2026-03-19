from storage.memory import (
    save_session_preferences,
    get_session_preferences,
    merge_session_preferences,
)

session_id = "demo-session"

save_session_preferences(session_id, {
    "interests": ["museums", "wine bars"],
    "travel_style": "romantic"
})

print(get_session_preferences(session_id))

print(merge_session_preferences(session_id, {
    "pace": "relaxed"
}))

print(get_session_preferences(session_id))