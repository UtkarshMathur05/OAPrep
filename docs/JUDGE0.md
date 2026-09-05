# Judge0 Setup

Judge0 runs the user's code. `POST /verify` is the only thing that touches it,
and the frontend never does.

**You do not need to set anything up.** The default in `.env.example` is the
public instance, and it is verified working:

```bash
JUDGE0_URL=https://ce.judge0.com
JUDGE0_API_KEY=
JUDGE0_API_HOST=
```

The three options below are in the order you should try them.

---

## Option 1 — Public CE instance (current default)

Zero setup, no key, no account.

```bash
curl https://ce.judge0.com/about
```

**Trade-off:** shared, aggressively rate-limited, and it goes down. Fine for
development and probably fine for the demo. It is why `MAX_TEST_CASES = 5` and
why submissions go through the batch endpoint — one request per run, not one
per test case.

If it starts refusing requests, move to Option 2.

---

## Option 2 — RapidAPI (recommended demo insurance)

A private quota on a hosted instance. ~15 minutes.

1. Sign up at [rapidapi.com](https://rapidapi.com)
2. Subscribe to **Judge0 CE** — the free tier is a few hundred requests/day,
   far more than a demo needs
3. Copy the key from the endpoint page
4. Put it in `.env`:

```bash
JUDGE0_URL=https://judge0-ce.p.rapidapi.com
JUDGE0_API_KEY=<your key>
JUDGE0_API_HOST=judge0-ce.p.rapidapi.com
```

`judge_service._headers()` adds `X-RapidAPI-Key`/`X-RapidAPI-Host` automatically
when both are set, and sends no auth headers when they are blank. No code change.

Verify:

```bash
curl -s localhost:8000/verify -H 'Content-Type: application/json' \
  -d '{"problem_id":"minimum-path-sum","code":"print(7)","language":"python"}'
```

**Do this before the demo, not during it.** One free key removes the single
likeliest live failure.

---

## Option 3 — Self-hosting ⚠️ not recommended for this hackathon

Judge0 sandboxes untrusted code with `isolate`, which needs **cgroup v1**.

**This machine runs cgroup v2** (`/sys/fs/cgroup` is `cgroup2fs`), as do all
current Fedora-based systems including Nobara. Making Judge0 work means:

```bash
# add to the kernel command line, then REBOOT
systemd.unified_cgroup_hierarchy=0
```

A reboot and a kernel parameter change, mid-hackathon, to sandbox code that a
free hosted instance already runs. Beyond that you would be running Judge0's own
server, workers, Postgres and Redis — Redis and extra services that CLAUDE.md
§22 explicitly rules out.

Only worth it if both hosted options fail **and** you have hours to spare. You
will not.

---

## How the backend uses it

```
POST /verify
  -> resolve problem_id (uuid or slug)
  -> load <= 5 test cases
  -> POST {JUDGE0_URL}/submissions/batch     one request, all cases
  -> poll GET /submissions/batch until every status.id > 2
  -> compare stdout to expected_output, both rstrip'd
  -> save to `submissions`
  -> VerifyResponse
```

Details that bit during implementation, confirmed against the live API:

* `time` is a **string** in seconds (`"0.011"`); `memory` is an **int in KB**.
* `stdout` always ends with a newline — hence `rstrip()` on both sides.
* The batch endpoint returns **201** and does **not** support `wait=true`.
  It must be polled; status ids 1 and 2 mean queued/processing.
* **Judge0 reports `Accepted` when the program merely ran.** We never send it an
  `expected_output`, so correctness is decided in `_aggregate` — a run can be
  `Accepted` to Judge0 and `Wrong Answer` to us.
* On failure `actual_output` falls back to stderr/compile output, so the UI can
  show *why* a case failed.

## Languages

Python only (`judge_service.LANGUAGE_IDS = {"python": 71}`).

Judge0 speaks stdin/stdout while coding problems are function-signature shaped,
so each additional language needs its own driver that parses stdin, calls the
function and prints the result. One language, one template. Other languages
return a readable message, not an error.

Full id list: `curl https://ce.judge0.com/languages`

## When it fails

Every failure degrades rather than breaking the demo:

| Failure | Result |
| --- | --- |
| Network error / timeout | `status: "Judge0 unavailable: ..."`, 0 passed |
| Does not settle in ~14s | same, via `TimeoutException` |
| Unsupported language | readable message, no exception |
| Problem has no test cases | `status: "No test cases for this problem"`, 0/0 |

Last resort: `USE_MOCK_AI=true` returns a canned `Accepted 12/12`, so the flow
still demos end to end.
