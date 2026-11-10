# Sentinels and Hanu

Sentinels is the user's agent collection. Hanu is the main assistant and
coordinator. OpenBot is the platform that runs them.

The existing host was renamed Sentinels and its existing Chief agent was renamed
Hanu. These are display-name changes: the host identity, iPhone pairing, agent
identity, workspace, model, instructions and chats stay in place. The other
agents keep their names and settings.

## Apply the names on another checkout

The names are saved in the local app database, not as global defaults for all
OpenBot users. In Server settings > General, change Server name to Sentinels.
Open the existing coordinator's Agent settings and change Agent name to Hanu.
Keep its existing ID and workspace. Other agents and new checkouts are not
renamed automatically. Generate the shortcut with that checkout's host and
agent IDs; do not copy another device's identifiers or pairing link.

## Ask Hanu on the iPhone Action Button

The first version opens Hanu's existing chat. It does not record audio or submit
a task automatically. Use the chat's microphone or keyboard to give the task.
Select Sentinels in the paired phone app before using this shortcut; the current
mobile link handler opens an agent on the selected server.

1. On the iPhone, open Shortcuts and create a shortcut named **Ask Hanu**.
2. Add the **URL** action. Enter the local Hanu chat link in this form:
   `openbot://live-activity?server=<host-id>&agent=<agent-id>`.
3. Add **Open URLs** after it. Save and run the shortcut once. Confirm that it
   opens Hanu in OpenBot.
4. In Settings > Action Button, select Shortcut > Choose a Shortcut > Ask Hanu.
5. Keep Tailscale connected and the Mac awake. Press and hold the Action Button
   to open Hanu.

See Apple's [Action Button instructions](https://support.apple.com/en-gb/guide/shortcuts/apdfea15680b/ios).

The link contains identifiers only, not credentials. It does not sign a phone in
or grant server access. A paired, signed-in phone is still required. Keep the
actual device identifiers and generated shortcuts in ignored `.openbot/` state.
Do not use a pairing link as the shortcut URL.

## Generate a shortcut file

The optional generator creates a two-action binary plist for Apple's signing
tool. Run it with the existing host and agent identifiers:

```sh
python3 scripts/create-hanu-shortcut.py --server HOST_ID --agent AGENT_ID
shortcuts sign --mode anyone \
  --input '.openbot/Ask Hanu.unsigned.shortcut' \
  --output '.openbot/Ask Hanu.shortcut'
```

Signing requires the Mac to be signed into iCloud and sends the shortcut to Apple
for validation. Anyone mode avoids embedding contact information. Do not put
credentials, prompt text or private files in the shortcut. On the configured Mac,
signing stopped because iCloud was not signed in. No signed or imported shortcut
was verified; manual creation on the iPhone is the available path.

Checked: saved Sentinels and Hanu display names, unchanged existing identifiers,
valid generated binary plist, and the current mobile handler's chat route. The
user confirmed manual shortcut setup on the iPhone. An automatic microphone
start is not implemented; the shortcut opens the chat.

A future version can add explicit voice capture and task submission through the
mobile app's authenticated connection. It must not send commands merely because
another app opened an unsigned URL.
