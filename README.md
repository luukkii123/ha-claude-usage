# Claude Usage — Home Assistant integration

Shows the **rolling usage limits of a claude.ai subscription** as sensors in
Home Assistant. It polls the Anthropic Messages API with a minimal probe call
and reads the `anthropic-ratelimit-unified-*` response headers — the same headers
Claude Code itself uses.

## What you get

| Sensor | Meaning |
| --- | --- |
| `Five-hour utilization` | Fraction of the 5-hour rolling limit used (0–100 %) |
| `Seven-day utilization` | Fraction of the 7-day rolling limit used (0–100 %) |
| `Five-hour reset` | When the 5-hour window resets (timestamp) |
| `Seven-day reset` | When the 7-day window resets (timestamp) |
| `Five-hour status` | `active` / `warning` / `rate_limited` |
| `Seven-day status` | `active` / `warning` / `rate_limited` |
| `Overall status` | `active` / `warning` / `rate_limited` |

## How it works

Every poll interval the integration sends a `POST` to
`https://api.anthropic.com/v1/messages` with `model=claude-haiku-4-5`,
`max_tokens=1` and a single-character prompt. That call costs practically nothing
but returns the rate-limit state of your subscription in the response **headers**
(the body is never read).

## ⚠️ Undocumented and subject to change

The `anthropic-ratelimit-unified-*` headers are **not documented** by Anthropic.
They were reverse-engineered from the Claude CLI and can change or disappear at
any time without notice. The integration therefore parses defensively: a missing
or malformed header leaves the corresponding sensor `unknown` instead of failing.

## Get a token

The integration authenticates with the **OAuth token from your claude.ai login** —
not an `sk-ant-api…` API key, which reports API-tier limits rather than the
subscription limits this integration targets.

1. Log in to Claude Code / claude.ai on the machine you use.
2. Read the token:
   - **Linux / Windows:** `~/.claude/.credentials.json` → `claudeAiOauth.accessToken`
   - **macOS:** Keychain item `Claude Code-credentials`
3. Paste it into the integration's config flow.

The token is stored in Home Assistant's config entry — **never** in this repo.

## Known limitations

- **No auto-refresh.** A claude.ai OAuth token is short-lived. When it expires
  the API answers `401`; the integration reports an error, and you re-enter the
  token via *Settings → Devices & Services → Claude Usage → Configure*.
- **Probe call counts.** Each poll is one (minimal) request. The default interval
  is 300 s; a lower interval raises your request count.

## HACS installation

Add this repository to HACS as a **custom repository** of category
**Integration** (see `hacs.json`).

## Disclaimer

Not affiliated with Anthropic. Uses an unofficial, undocumented endpoint.
