# Malayalam Roast Battle — Flask Front End

A web front end for the Gemini-vs-Gemini Malayalam roast battle: fill in two
objects, pick a round count, and get a full comedy debate with distinct
Malayalam TTS voices for each speaker, playable right in the browser.

## What changed vs. the CLI script

- No `pygame`/local speaker playback — audio is written to
  `static/audio/<battle-id>/` and played through `<audio>` tags in the browser.
- No blocking `input()` prompts — everything comes from a web form.
- Core logic (Gemini calls + Edge-TTS synthesis) lives in `debate_engine.py`
  and is unchanged in substance from the original script, just reorganized
  into functions that return data instead of printing/playing.
- A **Demo** mode reproduces the original `run_demo()` fixed dialogue, so you
  can test voices without a Gemini API key.

## Setup

```bash
cd roast_battle
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste in your real GEMINI_API_KEY
```

## Run

```bash
python app.py
```

Then open http://localhost:5000 in your browser.

- If `GEMINI_API_KEY` is set, you can start a live battle (choose both
  objects and a round count).
- If it isn't set, the battle form is disabled and only **Run Instant Demo**
  is available.

## Project layout

```
roast_battle/
├── app.py              # Flask routes
├── debate_engine.py     # Gemini calls + Edge-TTS synthesis (core logic)
├── requirements.txt
├── .env.example
├── templates/
│   ├── base.html
│   ├── index.html       # setup form
│   └── battle.html      # results page with per-line audio players
└── static/
    ├── css/style.css
    └── audio/<battle-id>/  # generated mp3s, one folder per battle run
```

## Notes / things worth doing next

- Each battle run creates a new folder under `static/audio/`; nothing cleans
  these up automatically — add a cron job or startup cleanup if you'll run
  this a lot.
- The whole debate runs synchronously inside the `/battle` request, so a
  5-round battle can take a while to respond (multiple Gemini calls + TTS
  synthesis in sequence). For a snappier UI, consider moving `run_debate`
  into a background task/queue and polling or streaming progress to the
  client.
- `MODEL = "gemini-3.6-flash"` was carried over as-is from your original
  script — double check that's the model name you intend to call.
