---
name: aspireai-social-manager
description: Manage AspireAI news, podcasts, X posts, and announcements across the AspireAI site, WhatsApp, Discord, Meetup, and Substack. Use for scheduled or manual AspireAI publishing, target checks, duplicate prevention, and publication reports.
example-prompt: Publish the latest verified AI news to AspireAI, AI news on WhatsApp, Discord, and X.
---

# AspireAI social manager

Publish one verified content package to the configured targets. Fail closed. Do not replace a failed
publication with repeated agent turns.

## Before the first publication

1. Copy `references/config.example.json` to
   `~/.config/aspireai-social-manager/config.json` and set only non-secret options there.
2. Keep secrets in the host environment. The publisher reads:
   - `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, and `X_ACCESS_TOKEN_SECRET`;
   - `ASPIREAI_DISCORD_WEBHOOK` only when a direct Discord webhook is used.
3. Link WhatsApp in **Marketplace → Apps → WhatsApp**. Use a dedicated number when possible. Allow
   only the exact groups in `targets`.
4. Connect Discord in OpenBot, or set the Discord webhook environment value.
5. Sign in to Meetup and Substack in the dedicated OpenBot browser profile.
6. Run `python3 scripts/aspireai_publisher.py doctor`. Keep all routines paused until it succeeds.
7. Test each destination with unpublished or private content. Confirm its returned URL or message ID.

Never put a token, cookie, password, SSH private key, or webhook URL in this skill, a prompt, a
routine, Git, or the posting ledger.

## Common rules

- Use a content ID in the form `<kind>:<YYYY-MM-DD>:<edition>:<slug>`.
- Reserve each target before a post. Complete it only with the returned URL or message ID.
- If delivery is uncertain, mark it uncertain and stop. Never retry it automatically.
- Use at most one generation attempt and one correction attempt.
- Do not invent a source, quotation, date, person, product claim, or release status.
- Prefer primary sources. Use two independent sources for a material claim when no primary source
  exists.
- Include the canonical AspireAI page in social posts after the page is live.
- Do not publish a draft, test marker, local path, or internal error.
- Call `openbot.routine_report_failure` when a scheduled run cannot complete.
- End a scheduled run with `openbot.routine_no_update` when there is no material new item.

The local publisher is `scripts/aspireai_publisher.py`. Run `--help` for its exact commands.

## AI news workflow

1. Find material AI and emerging-technology news published since the previous edition.
2. Verify the event date and publication date. Prefer product documentation, company posts,
   government notices, standards bodies, and research papers.
3. Select three to five items. Remove duplicates and minor rewrites of the previous edition.
4. Write:
   - a concise AspireAI article with source links;
   - a short WhatsApp and Discord summary;
   - one X post that fits the current X limit without splitting a thread.
5. Publish the article through the restricted SSH command:
   `python3 scripts/aspireai_publisher.py post-site --content-id <id> --kind news --payload <json>`.
6. Use `openbot.messaging_list_places` and confirm the exact WhatsApp and Discord place IDs.
7. Reserve `whatsapp-news`, post once with `openbot.messaging_post`, then complete it with the
   returned message ID. Use the same process for `discord-news`.
8. Publish X with `post-x` only after the AspireAI URL is live.
9. Report every target as `completed`, `failed`, `uncertain`, or `skipped`.

## Podcast workflow

1. Select two to four verified topics that were not covered in the previous episode.
2. Write a spoken script with source links in its metadata. Do not read URLs in the narration.
3. Generate the audio with the configured podcast command:
   `python3 scripts/aspireai_publisher.py generate-podcast --content-id <id> --payload <json>`.
   The configured command can call Chatterbox or another selected model.
4. Confirm that the output file exists, has non-zero duration, and plays without an error.
5. Publish the episode page and media through `post-site`.
6. Post the canonical episode URL to the exact WhatsApp AI podcasts group and Discord podcast
   channel. Reserve and complete each target around `openbot.messaging_post`.
7. Publish one X post only after the episode URL is live.

## Announcement workflow

Announcements are manual or webhook-started. They are not part of the news and podcast schedules.

1. Confirm the event title, organizer, date, time zone, venue or online link, registration URL, and
   intended audience.
2. Create one canonical announcement package and content ID.
3. Publish to the AspireAI site when requested.
4. Use the OpenBot browser for Meetup. Stop for login, CAPTCHA, changed fields, or a missing final
   confirmation. Record the event URL after publication.
5. Post once to the configured WhatsApp and Discord announcement targets.
6. Use the Substack browser only when the user requests a Substack announcement. Confirm the
   audience and whether email delivery is on before the final Publish action.
7. Do not add people to WhatsApp groups automatically.

## Browser publication rules

- Use a dedicated browser profile.
- Re-read the title, destination, audience, date, and send-email option before the final click.
- After the click, verify the public URL or the platform's success state.
- A timeout after the final click is `uncertain`, not `failed`.
- Stop after one failed page interaction. Do not loop through selectors or refresh repeatedly.

## Native messaging ledger

Before `openbot.messaging_post`:

```sh
python3 scripts/aspireai_publisher.py reserve --content-id '<id>' --channel '<channel>'
```

After a confirmed post:

```sh
python3 scripts/aspireai_publisher.py complete --content-id '<id>' --channel '<channel>' --remote-id '<message-id>'
```

After an uncertain result:

```sh
python3 scripts/aspireai_publisher.py uncertain --content-id '<id>' --channel '<channel>' --reason '<short reason>'
```

Do not reserve the same content ID and channel again when the command refuses it.
