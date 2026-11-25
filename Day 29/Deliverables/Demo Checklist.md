# Demo Practice Checklist

Two lists: what to do before the demo, and what to do while rehearsing. Print
both, or keep this open on a second screen.

---

## A. Ten minutes before

### Service checks

- [ ] `ollama serve` is running in its own terminal and has not been closed
- [ ] `ollama list` shows `qwen2.5:3b` (or whichever model the dashboard is set to)
- [ ] `curl http://localhost:11434/api/tags` returns JSON
- [ ] The dashboard is running: `curl http://localhost:8520/_stcore/health`
      returns `ok`
- [ ] The browser tab is open and the page has finished rendering
- [ ] Only one dashboard instance is running, on the port you plan to show

### Warm-up

- [ ] Run one question end to end before the audience arrives, so the model is
      loaded and the embedding model is cached
- [ ] Confirm the warm-up run appears under the Report tab
- [ ] Note the warm-up run folder in `output/` as the fallback artifact

### Content checks

- [ ] `docs/` contains `company_info.txt`, `ai_agents.txt`, `local_ai_tools.txt`
- [ ] The documents folder field in the sidebar reads `docs`
- [ ] Source mode is `Local documents`
- [ ] The model field matches the model you pulled
- [ ] The example question is copied to a text file or clipboard, not retyped

### Machine checks

- [ ] Laptop is on mains power, not battery
- [ ] Sleep and display timeout are disabled for the session
- [ ] Notifications are off (Windows: Focus assist, do not disturb)
- [ ] Screen resolution is readable for the room; browser zoom at 100 to 125
- [ ] Second monitor arrangement is correct if you are presenting on a projector
- [ ] Audio and screen share are tested if remote
- [ ] Other resource-heavy apps are closed

### Fallbacks ready

- [ ] Recent successful run folder open in Explorer
- [ ] A terminal open with the warm-up report printing, ready to switch to
- [ ] [DEMO.md](DEMO.md) open on a second screen or phone
- [ ] The deck open on the slide after the demo, so returning is one click

---

## B. Rehearsal checklist

Run this three times. Each pass has a different goal.

### Pass 1: content and timing

- [ ] Demo completed in under 3 minutes 30 seconds
- [ ] Every claim in the narration matches the screen
- [ ] The answer on screen (18 paid leave days) was said out loud, not just shown
- [ ] The citation `[2]` was traced to `company_info.txt` on screen
- [ ] No dead air longer than 15 seconds during the run
- [ ] The transition back to slides is rehearsed, not improvised

### Pass 2: failure handling

- [ ] Practised the fallback: switch to the saved run and narrate from it
- [ ] Practised the fallback: narrate from the terminal output
- [ ] Know the one-sentence explanation for "Ollama is not responding"
- [ ] Know the one-sentence explanation for "no sources retrieved"
- [ ] Know what to say if a run takes twice as long as expected
- [ ] Recovery commands are within reach: health check, restart on a new port

### Pass 3: with an audience

- [ ] One person watched without interrupting
- [ ] They could state the problem the project solves afterwards
- [ ] They could explain why the writer does not see raw sources
- [ ] They asked at least two questions, and each was answered in under 30 seconds
- [ ] Nothing was read verbatim from a slide

### Quality bar

- [ ] No emoji on any slide or in any output shown
- [ ] No "um" filler longer than a second in the recorded run
- [ ] No apology for model speed, latency, or hardware
- [ ] No slide with more than five lines of body text
- [ ] Opening sentence names the problem, not the technology
- [ ] Closing sentence is the refusal principle, not a feature list

---

## C. During the demo

- [ ] State the question before typing it
- [ ] Narrate the coordinator, research, and analyzer stages as they appear
- [ ] Say the number out loud when the report appears
- [ ] Show one citation resolving to a real file
- [ ] Show the critic score and verdict
- [ ] Show the saved run folder only if time allows
- [ ] Stop at the planned point even if there is more to show

If something fails:

- [ ] Name the cause in one sentence
- [ ] Switch to the fallback without commenting on your own reaction
- [ ] Continue the narration from where the fallback starts
- [ ] Do not retry the live path in front of the audience

---

## D. After the demo

- [ ] Stop the dashboard, or leave it running if questions may need it
- [ ] Return to the deck for the closing slide
- [ ] Have the appendix slides ready for backend and artifact questions
- [ ] Note anything that broke, to fix before the next run of the demo
- [ ] Save any new run folders worth keeping as examples

---

## E. Known risks and the answer

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Model cold start delays first output | High if no warm-up | Warm-up run in section A |
| Run exceeds the demo slot | Medium with a 3B model on CPU | Hard stop, fall back to saved run |
| Ollama not running on the demo machine | Low if checked | Start it, or fall back to a saved run |
| Dashboard port already taken | Medium | Start on `--server.port 8521`, check health first |
| Wrong model name in the sidebar | Medium | Confirm with `ollama list` |
| Empty `docs/` because of the wrong working directory | Low | Start Streamlit from the project folder |
| Projector changes colours | Low | The light theme is deliberate; check contrast once on the projector |
| Question answered from general knowledge, not documents | Low | The question chosen is answered verbatim in `company_info.txt` |

---

## F. One-line recovery commands

```powershell
# services
ollama serve
curl http://localhost:11434/api/tags
curl http://localhost:8520/_stcore/health

# restart dashboard on another port
python -m streamlit run app.py --server.port 8521

# inspect what was saved
Get-ChildItem output | Sort-Object LastWriteTime -Descending | Select-Object -First 3
```

Git Bash equivalents: `ls -t output | head -3`, `grep` instead of `findstr`, and
`taskkill //F //PID <pid>` for a stale server.
