# AspireAI social manager

This package creates one OpenBot agent for AspireAI news, podcasts, X posts, and announcements. It
uses the current OpenBot WhatsApp and Discord connections. It uses the paid X API directly. It sends
site content to one restricted SSH command. It uses the OpenBot browser for Meetup and Substack.

The imported routines are off. Turn them on only after the setup checks pass.

## Build and import

From the repository root:

```sh
python3 tools/aspireai-social-manager/build_import.py
```

The command writes:

```text
.openbot-build/aspireai-social-manager/aspireai-social-manager.zip
```

In OpenBot, open **Server settings → Import** and select that file. Import **AspireAI Social
Manager**.

## Configure the host

Copy the example config from the installed skill to:

```text
~/.config/aspireai-social-manager/config.json
```

Do not put secrets in that file. Set these values in the environment of the managed OpenBot service:

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`
- `ASPIREAI_DISCORD_WEBHOOK`, only when you choose a webhook instead of the OpenBot Discord app

Set `site.argv` to an SSH command with a restricted remote account. The remote account must accept
one JSON object on standard input and return one JSON object with `url` or `id`:

```json
{
  "url": "https://aspireai.example/news/example"
}
```

The account must not have an interactive shell or a general `sudo` grant. Restrict its SSH key to
the site publisher command in `authorized_keys` when possible.

Set `podcast.argv` to a local command that accepts JSON on standard input. It can call Chatterbox or
another speech model. It must check the audio and return:

```json
{
  "verified": true,
  "output": "/absolute/path/to/episode.mp3"
}
```

## Connect services

1. Open **Marketplace → Apps → WhatsApp**. Link a dedicated number. Allow only `AI news`,
   `AI podcasts`, and the selected announcement group.
2. Connect the Discord server and check the three channel names in the config.
3. Sign in to Meetup and Substack in the agent's dedicated OpenBot browser.
4. Add the X values to the managed service environment.
5. Configure and test the restricted AspireAI SSH command.
6. Configure and test the podcast command.
7. In the agent workspace, run:

   ```sh
   python3 .agents/skills/aspireai-social-manager/scripts/aspireai_publisher.py doctor
   ```

8. Run each routine with **Test run**. Keep its messaging destination unset during the first test.
9. Set each routine's destination only after the matching WhatsApp or Discord test succeeds.
10. Turn on the four twice-daily news and podcast routines. Turn on the X routines after the first
    complete day has no duplicate or uncertain post.

## Default schedule

All times use `America/Chicago`.

| Routine | Time |
| --- | --- |
| AI news morning | 7:00 AM |
| AI podcast morning | 8:00 AM |
| X morning post | 9:30 AM |
| X afternoon post | 1:30 PM |
| AI podcast afternoon | 4:00 PM |
| AI news evening | 6:00 PM |
| X evening post | 7:30 PM |

Announcements remain manual. After the workflow is stable, make a webhook routine for announcement
requests. Do not poll Meetup or Substack.

## Failure policy

- No automatic retry after a send starts.
- A timeout after send is `uncertain`.
- A completed or uncertain content ID cannot be reserved again.
- A scheduled run with no material item stays quiet.
- A failed required target fails the routine and needs a person.

The ledger is at `~/.local/share/aspireai-social-manager/posts.sqlite3` by default.
