"""Server-rendered observability dashboard.

Plain HTML (no template engine, no JS build step) so the demo runs from the same FastAPI
process: a run list and a per-run page that shows the full step trace — latency, cost,
inputs/outputs, errors — plus a button to deterministically replay the run and diff it
against the original.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any

_STYLE = """
<style>
  :root { color-scheme: light dark; }
  body { font: 14px/1.5 system-ui, sans-serif; margin: 0; padding: 2rem; max-width: 1000px; }
  h1 { font-size: 1.3rem; } h2 { font-size: 1.05rem; margin-top: 1.8rem; }
  a { color: #2563eb; text-decoration: none; } a:hover { text-decoration: underline; }
  table { border-collapse: collapse; width: 100%; margin-top: .5rem; }
  th, td { text-align: left; padding: .4rem .6rem; border-bottom: 1px solid #8884; vertical-align: top; }
  th { font-weight: 600; }
  code, pre { font-family: ui-monospace, monospace; font-size: 12.5px; }
  pre { background: #8881; padding: .5rem .7rem; border-radius: 6px; overflow-x: auto; margin: .2rem 0; }
  .pill { display: inline-block; padding: .1rem .5rem; border-radius: 999px; font-size: 12px; background: #8882; }
  .pill.completed { background: #16a34a33; } .pill.awaiting_approval { background: #d9770633; }
  .pill.rejected, .pill.error { background: #dc262633; }
  .muted { color: #888; } .err { color: #dc2626; }
  button { font: inherit; padding: .4rem .9rem; border: 1px solid #8886; border-radius: 6px;
           background: #2563eb; color: #fff; cursor: pointer; }
  #replay-out { margin-top: .6rem; }
</style>
"""


def _page(title: str, body: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>{_STYLE}</head><body>{body}</body></html>"
    )


def _ts(value: Any) -> str:
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return "—"


def _pill(status: str | None) -> str:
    s = status or "—"
    return f"<span class='pill {html.escape(s)}'>{html.escape(s)}</span>"


def render_run_list(runs: list[dict[str, Any]]) -> str:
    rows = []
    for r in runs:
        msg = html.escape((r.get("user_message") or "")[:80])
        replay = (
            f" <span class='muted'>↩ {html.escape(r['replay_of'][:8])}</span>"
            if r.get("replay_of")
            else ""
        )
        rows.append(
            f"<tr><td><a href='/dashboard/runs/{html.escape(r['id'])}'>"
            f"<code>{html.escape(r['id'])}</code></a>{replay}</td>"
            f"<td class='muted'>{_ts(r.get('created_at'))}</td>"
            f"<td>{html.escape(r.get('intent') or '—')}</td>"
            f"<td>{_pill(r.get('status'))}</td>"
            f"<td>{msg}</td></tr>"
        )
    table = (
        "<table><thead><tr><th>Run</th><th>Time (UTC)</th><th>Intent</th>"
        "<th>Status</th><th>Message</th></tr></thead><tbody>"
        + ("".join(rows) or "<tr><td colspan='5' class='muted'>No runs yet.</td></tr>")
        + "</tbody></table>"
    )
    body = f"<h1>Runs</h1><p class='muted'>{len(runs)} most recent.</p>{table}"
    return _page("Runs · langgraph-support-rag", body)


def _pre(value: Any) -> str:
    if value is None:
        return "<span class='muted'>—</span>"
    text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
    return f"<pre>{html.escape(text)}</pre>"


def render_run_detail(data: dict[str, Any], replays: list[dict[str, Any]]) -> str:
    run = data["run"]
    run_id = run["id"]
    steps = data["steps"]

    meta = [
        f"<tr><th>ID</th><td><code>{html.escape(run_id)}</code></td></tr>",
        f"<tr><th>Created</th><td>{_ts(run.get('created_at'))} UTC</td></tr>",
        f"<tr><th>Intent</th><td>{html.escape(run.get('intent') or '—')}</td></tr>",
        f"<tr><th>Status</th><td>{_pill(run.get('status'))}</td></tr>",
        f"<tr><th>Message</th><td>{html.escape(run.get('user_message') or '')}</td></tr>",
        f"<tr><th>Response</th><td>{html.escape(run.get('final_response') or '—')}</td></tr>",
    ]
    if run.get("replay_of"):
        meta.append(
            f"<tr><th>Replay of</th><td><a href='/dashboard/runs/{html.escape(run['replay_of'])}'>"
            f"<code>{html.escape(run['replay_of'])}</code></a></td></tr>"
        )
    meta_table = "<table>" + "".join(meta) + "</table>"

    total_cost = sum(s.get("cost_usd") or 0.0 for s in steps)
    total_latency = sum(s.get("latency_ms") or 0.0 for s in steps)
    step_rows = []
    for s in steps:
        err = f"<div class='err'>{html.escape(s['error'])}</div>" if s.get("error") else ""
        step_rows.append(
            f"<tr><td>{s.get('step_index')}</td><td>{html.escape(s.get('step_type') or '')}</td>"
            f"<td>{html.escape(s.get('name') or '')}</td>"
            f"<td>{(s.get('latency_ms') or 0):.1f}</td>"
            f"<td>{(s.get('cost_usd') or 0):.4f}</td>"
            f"<td>{_pre(s.get('input'))}{_pre(s.get('output'))}{err}</td></tr>"
        )
    trace = (
        "<h2>Trace</h2>"
        f"<p class='muted'>{len(steps)} steps · {total_latency:.0f} ms · ${total_cost:.4f}</p>"
        "<table><thead><tr><th>#</th><th>Type</th><th>Name</th><th>ms</th><th>$</th>"
        "<th>Input / Output</th></tr></thead><tbody>" + "".join(step_rows) + "</tbody></table>"
    )

    replay_rows = "".join(
        f"<li><a href='/dashboard/runs/{html.escape(r['id'])}'><code>{html.escape(r['id'])}</code></a>"
        f" · {_pill(r.get('status'))} · {_ts(r.get('created_at'))}</li>"
        for r in replays
    )
    replay_list = f"<h2>Replays</h2><ul>{replay_rows}</ul>" if replays else ""

    # Replay button: POSTs to the JSON endpoint and shows the match/diff result inline.
    replay_widget = f"""
      <h2>Deterministic replay</h2>
      <p class='muted'>Re-runs the graph with this run's recorded LLM outputs and diffs the result.</p>
      <button onclick="replayRun()">Replay this run</button>
      <pre id="replay-out" class="muted">—</pre>
      <script>
        async function replayRun() {{
          const out = document.getElementById('replay-out');
          out.textContent = 'Replaying…';
          try {{
            const res = await fetch('/runs/{html.escape(run_id)}/replay', {{ method: 'POST' }});
            const data = await res.json();
            out.textContent = (data.comparison && data.comparison.match ? '✅ match — ' : '⚠️ diff — ')
              + JSON.stringify(data, null, 2);
          }} catch (e) {{ out.textContent = '❌ ' + e; }}
        }}
      </script>
    """

    body = (
        f"<p><a href='/dashboard'>← all runs</a></p><h1>Run <code>{html.escape(run_id)}</code></h1>"
        + meta_table + trace + replay_list + replay_widget
    )
    return _page(f"Run {run_id}", body)
