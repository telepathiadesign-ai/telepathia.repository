# Brainstorm synthesis — srv945584, 2026-10-02

## 1. The shape I'd recommend: **"One Card, One Till"**

Hybrid of **Proposal 1 (One Card, Zero Approvals)** and **Proposal 3 (Till Before Backlog)** — they tied at 64 points across the three judges and they fix opposite halves: P1 removes decisions (132 of the 152 waiting items are `risk=low`, 0 are high — verified on the box today), P3 says what "working" means in a number. Alone, P1 perfects a queue for a product with 2 scans in September; alone, P3 hangs on 20 DMs you have avoided since July. Grafted in: P4's security-first hour, heartbeat/self-test and RAM guard; P5's "deliver where the human actually shows up" (typed MCP tools, screenshots on cards, a git remote); P2's attention meter and backpressure.

```
VPS srv945584 — what runs
├── products
│   ├── foodlabel.service :8000 (127.0.0.1 + tunnel) + foodlabel-preview.service :8001 (active today; hostname not yet in cloudflared config)
│   ├── tradernews + worker + 2 tg timers (kept until the "mothball?" card is answered)
│   └── docker: freqtrade xs/xls/bot5 (paper — KEEP: BTC RISK-ON 2026-10-01, xs 19 trades since Aug 20, 7 open, +91 USDT), umami
├── crew — foodlabel/agents via cron, lock: max 2 `claude -p`, MemoryHigh=3G on user-0.slice
│   ├── 06:50 steward.py   audit + daily `claude -p 'OK'` self-test + heartbeat files + regenerates MACHINE.md table
│   ├── 07:00 triage.py    risk=low → approved automatically · cap 10 · proposers skip the day when >10 wait
│   ├── */3h executor.py   builds approved → preview slot, BEFORE/AFTER screenshot (visual.py's Chromium)
│   ├── Mon   product.py + visual.py (weekly, ≤3 proposals) · till.py 09:15 = THE card
│   └── paused: enrich.py, editorial.py (resume when queue <50 and external scans >50/mo)
├── doors: ssh · vscode-tunnel · vps-mcp :3000 (+ typed tools foodlabel_board/approve/ship/undo, enrich_approve)
├── bots: CLAW @SnoAdmin_bot (you) · @hi_duke_bot (public channel) — nothing else
└── ops: regime-watch 00:30 · Sun 04:00 hygiene (now also clears ~14 GB) · hourly oauth sync

Elsewhere
├── private GitHub remote for foodlabel (first off-box backup; graph-guard CI later)
└── Claude app / cloud session → vps-mcp → "where are we", "approve 3, reject 112"

You touch
├── Monday: one till card — 5 numbers + kill date 2026-12-31 · what landed [Ship all] [Undo #n] · ≤1 question, 7-day default
├── Any day: "where are we" in the Claude app → same STATUS.md the pinned CLAW card renders
└── Sometimes: one photo of a real label → becomes a test fixture
```

## 2. What's redundant today

| Group | Members | Keep | Drop |
|---|---|---|---|
| Telegram bots to one chat id | 6 tokens: CLAW, ClaudeTelegram, vps-bot, well-bot, hermes, @hi_duke_bot | CLAW + @hi_duke_bot | ClaudeTelegram, vps-bot, well-bot (export vault first), hermes — after `vps-notify.sh`, `regime-watch.sh`, `Aegent/notify.py` use `openclaw message send` |
| Doors into the box | vps-mcp, openclaw, hermes, ClaudeTelegram, vps-bot, claude-proxy, ttyd, code-server :9090, ssh, vscode-tunnel | vps-mcp (token-in-path, constant-time compare, `/etc/vps-mcp.env` 0600 — read today), openclaw, ssh, vscode-tunnel | ttyd, nginx :8080/:8082 blocks, code-server, hermes + claude-proxy (one chain), ClaudeTelegram, vps-bot |
| Idea writers | product, editorial, enrich, visual, monetize-agent, Aegent scout, report, hermes cron | product + visual weekly; enrich + editorial paused; till.py replaces report | monetize-agent (99 sections, 148 "Idea 1", never read a foodlabel doc), scout, hermes cron |
| Health checks | steward, vps-notify 08:00, ops.py 6h, tradernews ops_healthcheck 6h, hermes cron | steward (daily) + ops.py (6h); feed check folded into steward | 08:00 green push, ops_healthcheck push, hermes cron |
| "Where are we" | lab TUI, FreqUI ×3, code-server, Umami, STATUS.md, board.py, hermes vault, MACHINE.md | STATUS.md (steward-generated) + Umami + pinned CLAW card | lab, hermes vault; FreqUI via ssh port-forward only |
| Claude switchers | claude-proxy, claude-api/claude-sub, claw-mode.py, 2 billing paths in openclaw.json | claw-mode.py + hourly oauth sync | claude-proxy, `/root/bin/claude-api`, `claude-sub`; one billing path |
| Vaults | WELL, hermes_brain, tradernews/vault, MEMORY.md, MONETIZE.md | MEMORY.md, STATUS.md, OPSLOG.md; rename tradernews/vault → data | hermes_brain; MONETIZE.md → MONETIZE-archive.md + one-page MONEY.md |

**Dead or broken (evidence):** Aegent scout — 13 "claude binary not found" vs 64 digests, last 3 runs failed, failures line up with Claude Code auto-update windows (symlink recreated 09:30 today); when it works, "0 opportunities". Hermes — 124 of 124 cron runs "shell tools unavailable"; claude-proxy's 15 requests in 30 d are all that job. nginx :8082 → 502, nothing on 8081. ttyd — `ttyd -W /bin/bash`, no credential, public plain HTTP. ClaudeTelegram — 0 messages ever handled, no allow-list, root `claude -p` with Bash for anyone. vps-bot — 0 replies in 60 d, token printed in 57k log lines, sole Ollama consumer (0 requests in 30 d). well-bot — last note 2026-07-21, "open to ALL users", 324 MB log. 4 stale worktrees (not 3) + #112 in review 66 days. `/root/mcp-vps` superseded this morning. **The tap loop itself:** last human CLAW command 2026-05-10; 4 of 152 waiting items carry a card id (all July: #43, #52, #70, #94), 148 never did; all 36 approvals typed via CLI. **The product:** scan_log 85 (Jul) → 14 (Aug) → 2 (Sep).

## 3. What to build on top (ranked)

**For aditif users**
1. **Drain the 369** — 1 day. One card "284 drafts claim no flag → approve all safe" (`approve_enrich.py --approve-safe`), then 85 flag drafts in batches; graph goes 118 → ~400 assessed at zero model cost. Biggest content gain per tap on the box.
2. **Shareable verdict card** as og:image on `/s/<id>` + "Trimite pe WhatsApp" — 2 days. The only growth lever that needs no outreach; measurable in Umami referrers (100% direct today).
3. **"Cere evaluare"** on every neevaluat additive → enrich.py priority — 1 day. Demand sets research order and gives a reason to come back (the gate).
4. **WILD: Scan the shelf** — 4 days. One shelf photo → "cel mai curat de aici". Filmable demo; prototype only after 1–2.

**Sellable**
5. **XSMomentumRegime pack at €59, as-is** — 1 weekend, no code. Bots keep running so the README cites a live forward record, not a frozen one.
6. **Pro gate** (3 free scans/day → Lemon Squeezy link → webhook flips `pro=1`) — one executor run, ~150 lines on `users.db` + `usage_counters.json`. The single pre-approved money item.
7. **WILD: "Ochi"** — visual.py sold as a weekly mobile UX critique to RO e-shops, €49/mo — 3 days. Sells your judgement, not traffic you lack.

**Makes the machine better**
8. **Typed MCP tools** on `/opt/vps-mcp/server.mjs` — 1.5 days. "Where are we" and "approve 3, reject 112" work in the Claude app, where approvals actually happened; never "check Telegram".

## 4. Two serious alternatives

**Thin Box, GitHub Spine (P5).** Box keeps products + tunnel + MCP; every agent becomes a cloud Routine; every proposal arrives as an already-built PR with screenshots; your only button is Merge. Choose it if, after 8 weeks, taps stay at 0 and you'd rather live in GitHub mobile — or if the box swaps again despite the lock. Cost: six weekends before money, and `graph-guard.yml` is worth stealing today regardless.

**One Manifest, One Door, One Card (P4).** `fleet.yaml` generates systemd timers with heartbeats, RAM slices, Cloudflare Access, a generated FLEET.md. Choose it if something fails silently again (another Aegent) or you add a second real tenant. Cost: a framework one non-engineer must keep sole; nothing changes for a stranger in 90 days.

## 5. Is there a better way to set this up?

Routines gain you a readable transcript per run, no OAuth-copy cron, no binary vanishing mid-update, zero RAM on the box, and a Monday brief in the Claude app. You lose CLAW tap cards and locality: build, preview, screenshots and tests all need the box, so every Routine would run through vps-mcp anyway. And a failed Routine is as silent as a failed cron: of your 4 Routines, 2 ended **ABANDONED** on 2026-09-28 (Ukraine board, Frontier Book); 2 succeeded. Keeping things exactly as-is is not an option: 9 daily `claude -p` with no lock is the August swap storm waiting.

**Recommendation:** keep the hand-rolled crew for anything that touches the box, with three guards (lock: max 2 `claude -p`; `MemoryHigh=3G` on user-0.slice; daily `claude -p 'OK'` self-test in steward). Move the *reading* side to where you are: typed MCP tools plus exactly one Routine — Monday "where are we" that calls `foodlabel_board` and posts in the Claude app as a second rendering of till.py. Review on 2026-12-31: if CLAW taps are still 0, drop CLAW and move to P5.

## 6. First weekend

1. **Prove one CLAW tap end to end** (board_card.py → tap → `foodlabel approve N` in backlog.json). Payoff: you learn whether the control surface works before switching anything off.
2. **Hour one, second SSH session open:** `docker rm -f ttyd`; delete the nginx :8080 and :8082 server blocks; bind code-server to 127.0.0.1. Payoff: public root shell gone; nothing you use daily changes.
3. **Stop, don't delete:** `systemctl disable --now vps-bot ollama hermes-gateway claude-proxy well-bot` (export WELL/vault first); comment out monetize-agent 09:00, Aegent 08:00 (before the fresh symlink revives it), vps-notify 08:00 (keep Sunday hygiene). Payoff: 3 anonymous doors closed, RAM back, undo is one `enable`.
4. **Repoint** vps-notify.sh, regime-watch.sh, Aegent/notify.py to `openclaw message send`; then disable claude-telegram and revoke its token at @BotFather. Payoff: "two Telegram surfaces" becomes literally true.
5. **Git remote** for foodlabel (private, credential helper, not token-in-URL); rotate the tokens in `/root/tradingbot/.git/config` and `/root/Aegent/.git/config`; commit STATUS.md/FOUNDRY.md. Payoff: first off-box backup; steward goes green.
6. **Board amnesty:** reject #112 (STATUS.md's own advice), park #11/#12/#18/#74/#103, prune 4 worktrees, bulk-park the 152 as `pile-2026-10`, pre-approve one item (Pro gate), hard-cap 10 in backlog.py. Payoff: executor finally has work; the wall is gone.
7. **Drain the 369:** one tap, "approve all 284 flag-free". Payoff: 118 → ~400 assessed, zero cost.
8. **Sunday:** triage auto-lane (risk=low → approved → preview, [Ship][Undo]); pause enrich/editorial; add the lock and MemoryHigh. Payoff: 152 can never form again.

## 7. Open questions for you

1. Who is the first paying stranger — a parent scanning a kids' snack, or a dietitian writing client reports? (Decides Pro gate vs dietitian desk.)
2. tradernews: mothball, or keep the channel timers only? A judge counted 2 channel members — give it a date, not drift.
3. What is the kill number on 2026-12-31 — 1 paying user, 5 trials, or 10 strangers who scanned twice?
4. Would *you* forward a red-chip verdict card to a WhatsApp group? If not, who would — that person designs the share card.