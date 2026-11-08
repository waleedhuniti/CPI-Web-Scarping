# Starting the work on the laptop (a new local Claude Code session)

A cloud session cannot be moved to the laptop, and it cannot open the laptop's folders (they show "not available"). So: start a NEW
session on the laptop and give it this prompt. The repository carries the rules (`CLAUDE.md`) and everything built so far.

1. On the laptop: install/update the Claude desktop app, Python 3.10+ (Add to PATH) and Git.
2. Create the folder `Desktop\cpi`, open it as the folder of a new Claude Code session (local, on this computer).
3. Paste:

````text
Continue the CPI price-collection work on this laptop. Everything is in the repo https://github.com/waleedhuniti/CPI-Web-Scarping, branch claude/sleepy-lamport-dwu4iw. Clone it into repo\ inside this folder (git clone --branch claude/sleepy-lamport-dwu4iw ...), open it, read CLAUDE.md (its rules bind you) and docs/routines/laptop/README_ar.md and docs/routines/laptop/daily_laptop.md.

Why we are here: Carrefour UAE refuses our requests from the cloud servers (HTTP 403 / empty pages since 30 Oct 2026). This laptop is on the office network; the plan is to run the whole daily collection (TrendX, CPI basket, product catalogue) from here, with the same code the panel stores. We do not use stealth, proxies or any bypass; if Carrefour refuses this laptop too, we report it as blocked and stop.

Do, in order, and tell me the result of each:
1. Check that ArtifactData and Artifact tools are available in this session (ToolSearch "select:ArtifactData"). Tell me if not.
2. Run `python scripts/pc/carrefour_pc.py --test` from repo\ (20 Carrefour barcode pages, paced at 2.5 s, stops after 5 refusals). Report how many pages were read and the state in barcode\carrefour_status.json. Run it only once.
3. If Carrefour read the pages (state ok): show me the scheduled-task steps from README_ar.md and create the scheduled task "Daily collection" if this app lets you (daily 08:30 Asia/Dubai, folder = this one, prompt = the text inside the ````text block of daily_laptop.md), otherwise tell me exactly what to click. If Carrefour refused: stop and tell me; do not retry.
4. Do not turn off the cloud routines yourself; the cloud session that built this will do it after the first successful run here.
````
