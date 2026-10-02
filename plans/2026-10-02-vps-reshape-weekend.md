# VPS reshape — executable plan (weekend 1)

**For:** a Claude Code session (Opus or Sonnet) with the `VPS_MCP` tools connected.
**Box:** `srv945584` · `148.230.109.154` · Ubuntu 24.04 · 2 vCPU · 7.8 GB RAM.
**Owner:** one person, a product designer. Decisions below marked **[OWNER]** were already taken by them on 2026-10-02; do not re-ask them. Anything else: decide technically, state it in one line, keep going.
**Written:** 2026-10-02 from a live audit of the box. Facts here were verified that day; re-verify anything that looks different before acting on it.

---

## 0. Read this first

### What this plan is for
The box runs one real product (aditif, the food-label scanner at `eticheta.telepathiadesign.com`) plus an agent crew ("Foundry"), a paused-to-be news site, three paper trading bots, and a pile of dead or redundant bots and doors. This weekend: close the public holes, stop what's dead, pause tradernews, unblock the Foundry board, and ship the one content win that costs nothing (369 researched additive entries waiting for approval). Nothing user-facing on aditif changes except more additives being covered.

### Owner decisions already made **[OWNER]**
1. aditif serves both parents and dietitians with **one** Pro tier (unlimited scans, saved lists, PDF report). Design the share card for the parent.
2. **tradernews is paused**, not deleted. Keep the data and the domain.
3. 31 Dec is a **review date, not a kill date**. No kill number. Don't add hard deadlines anywhere.
4. The trading bots **stay running** (BTC flipped risk-on on 2026-09-30; the long-only strategy is finally in its intended regime).

### Non-negotiable rules (from `/root/WAYS_OF_WORKING.md` and this plan)
- **Stop, don't delete.** Every service change this weekend is `systemctl disable --now` or a commented cron line. Deletion is a later weekend, after a week of nothing missing.
- **Back up before you touch.** Any file you edit: `cp FILE FILE.bak-$(date +%Y%m%d-%H%M)` first. The repo already uses this convention.
- **Log every change:** `oplog "what you did"` (appends to `/root/OPSLOG.md`). It's on PATH at `/usr/local/bin/oplog`.
- **Keep a second SSH session open** for the whole of Phase 1 so a mistake in nginx/code-server can't lock you out.
- **`free -h` before anything heavy.** Max 2 concurrent `claude -p`. If swap climbs over 1.5 GB, stop and wait.
- **Verify in the product, not the terminal.** After every phase, `curl -s -o /dev/null -w '%{http_code}' https://eticheta.telepathiadesign.com` must be 200, and the preview on :8001 must still answer.
- **Never end with uncommitted work.** Phase 4 creates the remote; after that, commit at the end of every phase.
- **Report in user-facing terms** at the end, with what broke if anything did.

### How to connect
Use `mcp__VPS_MCP__run_command` (runs as root, default cwd `/root`, 120 s default timeout, max 1800). `mcp__VPS_MCP__read_file` / `write_file` / `edit_file` for files. All the `/root/.profile: /root/bin: Is a directory` stderr noise is harmless; ignore it.

---

## 1. Ground truth (verified 2026-10-02)

| Thing | State |
|---|---|
| aditif usage | scans/month: Jun 148 · Jul 85 · Aug 14 · **Sep 2** (`/root/foodlabel/scan_log.jsonl`) |
| Foundry board | `/root/foodlabel/backlog.json`: 201 tasks · 152 `awaiting_approval` (132 low-risk, 20 medium, 0 high) · 1 `review` (#112, built 2026-07-28) · 5 stale `in_progress` (#11 #12 #18 #74 #103) · 6 `parked` · 36 `done` |
| Enrich queue | `pending_enrich.jsonl` 369 lines · `pending_flags.jsonl` 2 · quarantine 3 |
| Steward | FAIL: uncommitted `FOUNDRY.md`, `STATUS.md` · WARN: branch `foundry/task-112` unmerged · 4 stale worktrees under `foodlabel/.claude/worktrees/` |
| foodlabel git | **no remote** (`git remote -v` empty) |
| Public holes | docker `ttyd` (`ttyd -W /bin/bash`, no auth) via nginx `:8080/terminal/` · code-server `bind-addr: 0.0.0.0:9090` (password auth) also via `:8080/code/` · nginx `:8082` → `127.0.0.1:8081` which is dead (502) · foodlabel `:8000` bound `0.0.0.0` · FreqUI ×3 on `:8080/bot-*/` with a weak default password (see `/root/tradingbot/BOTS.md` on the box; do not copy it into any repo) |
| nginx | `/etc/nginx/sites-enabled/mcp` (mcp.telepathiadesign.com → :3000, keep) · `/etc/nginx/sites-enabled/tradernews` (the :8080 and :8082 server blocks) |
| cloudflared | `/root/.cloudflared/config.yml`: tradernews→:5000, eticheta→:8000, analytics→:3001. Service `cloudflared-tradernews` |
| tradernews | `tradernews.service` (:5000), `tradernews-worker.service`, timers `tradernews-tg-brief.timer`, `tradernews-tg-alert.timer`; crons `30 4 * * * ops_backup.sh`, `10 */6 * * * ops_healthcheck.py` |
| Dead/broken bots | `vps-bot` (0 replies/60 d, token in 57k log lines, sole Ollama user) · `well-bot` (last note 2026-07-21, vault 356 KB at `/root/WELL/vault`) · `hermes-gateway` (124/124 cron runs failed) · `claude-proxy` (:8765, only Hermes used it) · `claude-telegram` (0 handled messages, runs `claude -p` as root for any sender) · Aegent `scout.py` cron (`claude binary not found`) · `monetize-agent.sh` cron (4135-line `MONETIZE.md`, same 5 ideas since June) · `/root/HermesTelegram` empty · nginx :8082 block |
| Token dependency | `/root/ops/vps-notify.sh`, `/root/ops/regime-watch.sh`, `/root/Aegent/notify.py` all read `BOT_TOKEN` from **`/root/ClaudeTelegram/.env`**. Do not retire that token before Phase 3 repoints them. |
| Token leak | `/root/Aegent/.git/config` has a GitHub token in the remote URL |
| Telegram surfaces | CLAW (openclaw gateway, user service, :18789; `openclaw message send --channel telegram --target <chat> --message "..."`) · ClaudeTelegram · vps-bot · well-bot · hermes · `@hi_duke_bot` (tradernews channel) |
| Keep as-is | `vps-mcp.service` (:3000, this control channel) · `openclaw-gateway` · `vscode-tunnel` · ssh · `foodlabel.service` · `foodlabel-preview.service` (:8001) · umami + umami-db · freqtrade_xs / xls / bot5 · `monarx-agent` · `regime-watch` cron · Sunday hygiene cron · hourly `openclaw-sync-claude-oauth.sh` |
| Board CLI | `python3 agents/backlog.py {list,show,add,move,approve,reject,park,unpark,render,stats}` · `python3 agents/approve_enrich.py --list | --show <E> | --approve-safe | <E...>` · `python3 agents/steward.py` · `python3 agents/board_card.py` |

---

## 2. Phases

Run in order. Each phase ends with a verify block and an `oplog` line. Phases 1–3 are reversible with the single command noted. Expected total: 3–5 hours of agent time.

### Phase 0 — Snapshot (10 min)
```bash
mkdir -p /root/backups/reshape-2026-10-02 && cd /root/backups/reshape-2026-10-02
crontab -l > crontab.before
systemctl list-units --type=service --state=running --no-legend > services.before
ss -tlnp > ports.before
cp /etc/nginx/sites-enabled/tradernews nginx-tradernews.before
cp ~/.config/code-server/config.yaml code-server.before
cp /root/foodlabel/backlog.json backlog.json.before
cp /root/.cloudflared/config.yml cloudflared.before
free -h > free.before; oplog "reshape: phase 0 snapshot in /root/backups/reshape-2026-10-02"
```

### Phase 1 — Close the public doors (30 min) · **open a second SSH session first**
Rollback for the whole phase: `cp /root/backups/reshape-2026-10-02/nginx-tradernews.before /etc/nginx/sites-enabled/tradernews && nginx -t && systemctl reload nginx; docker start ttyd; cp .../code-server.before ~/.config/code-server/config.yaml && systemctl restart code-server@root`.

1. **Web shell:** `docker stop ttyd` (not `rm`; remove next weekend).
2. **nginx:** edit `/etc/nginx/sites-enabled/tradernews` (backup first). Delete the entire `listen 8082` server block (its backend `:8081` is dead). In the `listen 8080` block delete the `location /terminal/` and `location /code/` stanzas. Leave `/bot-xs/`, `/bot-xls/`, `/bot5/`, `/news/` and `/` for now (the owner may still open FreqUI; it has a password). `nginx -t && systemctl reload nginx`.
3. **code-server:** in `~/.config/code-server/config.yaml` set `bind-addr: 127.0.0.1:9090`, then `systemctl restart code-server@root`. The owner's VS Code path is the **vscode-tunnel** (unchanged) and Remote-SSH; code-server stays reachable only by SSH port-forward.
4. **foodlabel bind:** check `grep -n "0.0.0.0\|host=" /root/foodlabel/server.py` and the unit `systemctl cat foodlabel`. If the app binds `0.0.0.0:8000`, change it to `127.0.0.1` (cloudflared reaches localhost). Restart and verify the public URL. If the bind is set in the unit's `ExecStart`, use a drop-in: `systemctl edit foodlabel`. **If anything about this step is unclear, skip it and note it**; it's the only step in Phase 1 that touches the live product.
5. **Verify:**
   ```bash
   for u in https://eticheta.telepathiadesign.com http://127.0.0.1:8001/ https://mcp.telepathiadesign.com http://148.230.109.154:8080/bot-xs/; do echo "$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 $u) $u"; done
   curl -s -o /dev/null -w '%{http_code}\n' --max-time 5 http://148.230.109.154:8080/terminal/   # expect 404
   curl -s -o /dev/null -w '%{http_code}\n' --max-time 5 http://148.230.109.154:9090/            # expect 000 (refused)
   ss -tlnp | grep -E ':9090|:8082'   # 9090 must show 127.0.0.1; 8082 gone
   ```
   Expect eticheta 200, preview 200, mcp 404 (that's its normal root response), bot-xs 200.
6. `oplog "reshape: phase 1 — ttyd stopped, nginx :8082 + /terminal/ + /code/ removed, code-server bound to localhost"`

### Phase 2 — Stop what's dead (20 min)
Rollback: `systemctl enable --now <unit>`; uncomment the cron line.

1. **Export the WELL vault first:** `tar czf /root/backups/reshape-2026-10-02/well-vault.tgz -C /root/WELL vault` (356 KB).
2. **Services:** `systemctl disable --now vps-bot well-bot hermes-gateway claude-proxy ollama`. Ollama only served vps-bot (0 requests in 30 d); stopping it frees RAM headroom.
   Do **not** touch `claude-telegram` yet (Phase 3).
3. **Crons:** `crontab -e` is interactive, so do it by file: `crontab -l > /tmp/cron.new`, then with `sed -i` prefix these three lines with `# PAUSED 2026-10-02: ` — the `monetize-agent.sh` line (09:00), the `Aegent/scout.py` line (08:00), and the `vps-notify.sh` **08:00 daily** line (keep the Sunday 04:00 `--hygiene` line). Then `crontab /tmp/cron.new && crontab -l | grep -c PAUSED` → expect 3.
4. **MONETIZE.md:** `mv /root/MONETIZE.md /root/MONETIZE-archive.md`. Create a new one-page `/root/MONEY.md` holding only the owner decisions from section 0 and the current priority list (Pro gate, strategy pack, share card). Update the `MONETIZE.md` reference in `/root/CLAUDE.md` to point at `MONEY.md` (+ archive).
5. **Verify:** `systemctl is-active vps-bot well-bot hermes-gateway claude-proxy ollama` → all `inactive`. `free -h` → available should rise. `curl` the eticheta URL again → 200.
6. `oplog "reshape: phase 2 — stopped vps-bot well-bot hermes claude-proxy ollama; paused monetize/Aegent/daily-health crons; MONETIZE.md archived → MONEY.md"`

### Phase 3 — One Telegram surface (45 min)
Goal: everything that pushes to the owner goes through CLAW (openclaw). Then ClaudeTelegram can be retired.

1. Find the owner's chat id and confirm the send command works: read `/root/foodlabel/agents/notify.py` and `/root/openclaw/config.json` for the target. Test: `openclaw message send --channel telegram --target <chat> --message "reshape: CLAW test ✅"`. If this fails, **stop Phase 3 here**, leave ClaudeTelegram running, note it in the report, continue with Phase 4.
2. Repoint the three scripts to that command instead of raw `curl` to `api.telegram.org`:
   - `/root/ops/vps-notify.sh` lines ~19–35 (the `BOT_TOKEN` read + `sendMessage` curl)
   - `/root/ops/regime-watch.sh` lines ~74–76
   - `/root/Aegent/notify.py` (`BOT_TOKEN` + requests call) — it's paused anyway, but repoint so nothing still depends on ClaudeTelegram's `.env`.
   Backup each, keep the message text identical, test each with a dry message.
3. `systemctl disable --now claude-telegram`. Leave `/root/ClaudeTelegram/.env` in place this weekend (revoking the token at @BotFather is an **owner** action; put it in the report as a one-tap ask).
4. **Verify:** `grep -rl "ClaudeTelegram/.env\|api.telegram.org" /root/ops /root/Aegent /root/foodlabel/agents` → should list nothing active (tradernews' own bot is paused in Phase 5 and uses its own token). Trigger `/root/ops/regime-watch.sh --notify` manually and confirm a CLAW message arrives.
5. `oplog "reshape: phase 3 — notifiers repointed to openclaw; claude-telegram stopped"`

### Phase 4 — Git safety (30 min)
1. **Aegent token:** `git -C /root/Aegent remote set-url origin https://github.com/telepathiadesign-ai/Aegent.git` (strip the token). Report that the old token should be revoked on GitHub (**owner** action).
2. **foodlabel remote:** the repo has no `origin`. Ask the GitHub MCP (`mcp__github__*`) to create a **private** repo `telepathiadesign-ai/foodlabel` if it doesn't exist; add it as origin **without a token in the URL** (use `gh auth` / credential helper if present on the box: `git config --global credential.helper` — if none, configure `store` with a fine-grained token the owner supplies, or skip the push and report). Commit the two uncommitted files first:
   ```bash
   cd /root/foodlabel && git add FOUNDRY.md STATUS.md && git commit -m "docs: sync FOUNDRY/STATUS after reshape audit"
   ```
   Check `.gitignore` covers `.env`, `*.sqlite`, `users.db`, `backlog.json`, `*.jsonl`, `__pycache__` **before** the first push. `git push -u origin master` (branch name: check `git branch --show-current`).
3. **Worktrees:** `git -C /root/foodlabel worktree list`; for each under `.claude/worktrees/` that is not `foundry-task-112`: `git worktree remove --force <path>`. Leave task-112's branch until Phase 5 decides it.
4. **Verify:** `python3 agents/steward.py` → "Working tree" check should pass. `git status --short` clean.
5. `oplog "reshape: phase 4 — Aegent token stripped, foodlabel pushed to private remote, stale worktrees pruned"`

### Phase 5 — Board amnesty + pause tradernews (40 min)
1. **tradernews pause [OWNER]:** `systemctl disable --now tradernews-tg-brief.timer tradernews-tg-alert.timer tradernews-worker tradernews`. Comment out the two tradernews cron lines (`ops_backup.sh`, `ops_healthcheck.py`) with the same `# PAUSED 2026-10-02:` prefix. Replace the public page: simplest is a static "Trader Intel is paused" HTML served by a tiny `python3 -m http.server` unit on :5000, or point the cloudflared `tradernews.telepathiadesign.com` ingress to `http_status:503`. Pick the one that takes 5 minutes; a 503 is acceptable. Do **not** delete `/root/tradernews`.
2. **#112:** `git -C /root/foodlabel log -1 --stat foundry/task-112`. It's 66 days stale against a master that moved. `python3 agents/backlog.py reject 112` with a note "stale; superseded by enrich drain", and `git branch -D foundry/task-112` only **after** the remote push in Phase 4 succeeded (so the branch is recoverable from reflog/remote).
3. **Stale in-progress:** `for i in 11 12 18 74 103; do python3 agents/backlog.py park $i; done`.
4. **The 152:** bulk-park with a tag so they're findable: check `backlog.py park --help` for a note/tag option; if none, park them in a loop and record the ids in `/root/foodlabel/pile-2026-10.txt`. Keep **unparked**: any task whose title matches the landing-page fixes (#19, #96, #93 are already parked — unpark #19 and #96, they match the desktop layout problems seen 2026-10-02) and anything tagged `bug` with `risk=medium`. Target: ≤10 tasks in `awaiting_approval` afterwards.
5. **Pre-approve one money item:** `backlog.py add` a task "Pro gate: 3 free scans/day, then payment link; webhook sets pro=1 in users.db" type `product`, risk `medium`, then `backlog.py approve <id>`. The executor's next 3-hourly run will build it in a worktree and send the diff; it will **not** go live without the owner's `merge`.
6. **Cap:** in `agents/backlog.py` (or `product.py`), add a guard: if `awaiting_approval` count ≥ 10, `product.py` logs "queue full, skipping" and exits 0. Keep the change ≤15 lines; back up the file first.
7. `python3 agents/backlog.py render` → regenerates `BACKLOG.md`. `python3 agents/backlog.py stats`.
8. **Verify:** stats show ≤10 awaiting, 1 approved, #112 rejected. `curl https://tradernews.telepathiadesign.com` → 503 or the paused page. eticheta → 200.
9. `oplog "reshape: phase 5 — tradernews paused; board amnesty (152→≤10 awaiting, #112 rejected, Pro gate approved); product.py queue cap 10"`

### Phase 6 — Drain the 369 (30 min, zero model cost)
The enrich agent has 369 drafted additive entries (`pending_enrich.jsonl`) that were never approved. `approve_enrich.py --approve-safe` bulk-approves every draft that makes **no safety flag**; flagged ones need a human.
1. `cd /root/foodlabel && cp graph.json graph.json.bak-$(date +%Y%m%d-%H%M)` (the bak convention exists).
2. `python3 agents/approve_enrich.py --list | tail -5` to see counts. Then `python3 agents/approve_enrich.py --approve-safe`.
3. Count what's left: `wc -l pending_enrich.jsonl`. Do **not** approve flagged drafts; list their E-numbers in the report for the owner (it's a content/safety judgement = owner's).
4. **Verify in the product:** pick 3 newly approved E-numbers from the run output; `curl -s http://127.0.0.1:8000/<the additive detail route>` or open the preview on :8001 and confirm they render as assessed, not "neevaluat". Then `systemctl restart foodlabel` only if the app caches `graph.json` at start (check `server.py` for how it loads the graph). Re-check eticheta → 200.
5. `oplog "reshape: phase 6 — approve-safe drained N enrich drafts; graph assessed count X→Y"`

### Phase 7 — Guards + weekly rhythm (45 min)
1. **Concurrency lock:** wrap every `claude -p` cron in `flock`. Simplest: a wrapper `/root/bin/claude-slot` that does `flock -w 600 /run/lock/claude-slot-$((RANDOM%2)) "$@"` … or cleaner, `sem`-style with two lock files: try lock A, else lock B, else wait. Then prefix the Foundry cron lines (`product.py`, `editorial.py`, `enrich.py`, `executor.py build`, `visual.py`) with it. Keep `steward.py` and `ops.py` unlocked (no LLM).
2. **RAM guard:** `systemctl set-property user-0.slice MemoryHigh=3G` (persisted under `/etc/systemd/system.control/`). Verify with `systemctl show user-0.slice -p MemoryHigh`.
3. **Steward self-test:** in `agents/steward.py` add one check: run `claude -p 'reply OK' --max-turns 1` with a 60 s timeout; FAIL if it doesn't print OK. This is what would have caught Aegent's broken binary. ≤20 lines, backup first. Also add a check that `/root/Aegent` and `/root/ops` crons marked PAUSED are still paused (drift guard).
4. **Weekly cadence:** change cron so `product.py` and `visual.py` run **Mondays only** (`30 6 * * 1`, `20 6 * * 1`), `editorial.py` and `enrich.py` get the `# PAUSED` prefix (resume when scans > 50/month), `triage.py` stays daily, `executor.py build` stays 3-hourly, `steward.py` daily.
5. **Monday card:** `report.py` already runs Mon 09:15. Edit its message to lead with 5 numbers: scans this week · unique scanners · repeat scanners · additives assessed / total · tasks shipped. Then "awaiting you: N" and the single open question if any. Send via CLAW. No kill date, no deadline wording **[OWNER]**.
6. **Verify:** `crontab -l` reads cleanly; `python3 agents/steward.py` passes; `python3 agents/report.py --dry-run` (add the flag if missing) prints the card.
7. `oplog "reshape: phase 7 — claude -p lock, MemoryHigh=3G, steward self-test, weekly product/visual, Monday 5-number card"`

### Phase 8 — Docs + report (20 min)
1. Regenerate the service table in `/root/MACHINE.md` from `systemctl` + `ss` + `docker ps` output (it currently claims 5 bots, Traefik/n8n, :8082 live). Mark paused things as paused with the date. Update `/root/CLAUDE.md` project table (tradernews → PAUSED, Aegent → PAUSED, MONEY.md).
2. Update `/root/foodlabel/STATUS.md`: board numbers after amnesty, graph coverage after drain, 31 Dec = review date (not kill).
3. Commit + push foodlabel. `oplog "reshape: phase 8 — docs regenerated"`.
4. **Final report to the owner**, in this shape, in the chat (not Telegram):
   - What's now closed/stopped (one line each), and the single command that undoes each.
   - aditif: additives assessed before → after; board: awaiting before → after; what the executor is building (Pro gate).
   - RAM before/after.
   - **Three one-tap asks:** revoke the ClaudeTelegram token at @BotFather · revoke the leaked Aegent token on GitHub · look at the ≤N flagged enrich drafts (list the E-numbers).
   - Anything skipped and why.

---

## 3. Do NOT do this weekend
- Delete any directory, container, service file or Telegram bot. Stop only.
- Touch `freqtrade_*`, `umami*`, `vps-mcp`, `openclaw-gateway`, `vscode-tunnel`, `cloudflared-tradernews`, `monarx-agent`, sshd.
- Merge anything into foodlabel `master` that changes the UI. The executor builds; the owner merges.
- Approve flagged enrich drafts.
- Add kill dates, kill numbers or deadline language anywhere **[OWNER]**.
- Rewrite the Foundry crew into a new framework, move it to Routines, or build `fleet.yaml`. Those are later-weekend options, recorded in the brainstorm synthesis (`plans/2026-10-02-vps-brainstorm-synthesis.md`).

## 4. Next weekends (not now; for orientation)
- **W2:** delete what's been stopped a week with nothing missed; typed MCP tools (`foodlabel_board`, `approve`, `ship`, `undo`) on `/opt/vps-mcp/server.mjs`; share card (`/s/<id>` + og:image + "Trimite pe WhatsApp"), designed for a parent.
- **W3:** Pro gate review + merge; "Cere evaluare" button on unassessed additives; FreqUI behind Cloudflare Access or SSH-only.
- **W4:** XSMomentumRegime strategy pack packaging (no code) if the owner wants it.
- **31 Dec:** review — are strangers scanning twice? Then decide on CLAW vs the "thin box, GitHub spine" shape.
