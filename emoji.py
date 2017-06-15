"""Define emojis used by the client."""
# If you cannot ❌ read 📖 this, stop ⏹ and don't save 🚫 this file

# This file lists emojis used by the client as reactions to provide
# "buttons" the user can click on to trigger certain actions.

START_SRV = '▶'
STOP_SRV = '⏹'
KILL_SRV = '💀'
RESTART_SRV = '🔁'
ACCEPT_EULA = '✅'
CHAT_START = '✉'
CHAT_STOP = '🔇'
CHAT_REPLY = '📩'

TRIGGERS = {
    'eula': [ACCEPT_EULA],
    'start': [START_SRV],
    'control': [STOP_SRV, KILL_SRV, RESTART_SRV],
    'chat': [CHAT_REPLY, CHAT_STOP],
    'chat_init': [CHAT_START]
}
