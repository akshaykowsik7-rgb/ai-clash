import os
import uuid

from flask import Flask, render_template, request, redirect, url_for, flash

import debate_engine as engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_ROOT = os.path.join(BASE_DIR, "static", "audio")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

os.makedirs(AUDIO_ROOT, exist_ok=True)


@app.route("/", methods=["GET"])
def index():
    has_api_key = bool(os.environ.get("GEMINI_API_KEY"))
    return render_template("index.html", has_api_key=has_api_key)


@app.route("/battle", methods=["POST"])
def battle():
    mode = request.form.get("mode", "battle")
    object_a = request.form.get("object_a", "").strip()
    object_b = request.form.get("object_b", "").strip()
    rounds_raw = request.form.get("rounds", "3").strip()

    session_id = uuid.uuid4().hex[:12]
    audio_dir = os.path.join(AUDIO_ROOT, session_id)

    if mode == "demo":
        result = engine.run_demo(audio_dir)
        object_a = "കട്ടൻ ചായ (Black Tea)"
        object_b = "പഴംപൊരി (Banana Fritters)"
    else:
        if not object_a or not object_b:
            flash("Please enter both objects to start the battle.")
            return redirect(url_for("index"))

        if not os.environ.get("GEMINI_API_KEY"):
            flash("No GEMINI_API_KEY is configured on the server. Try the demo, or add a key to your .env file.")
            return redirect(url_for("index"))

        try:
            rounds = int(rounds_raw)
        except ValueError:
            rounds = 3
        rounds = max(1, min(rounds, 8))

        try:
            result = engine.run_debate(object_a, object_b, rounds, audio_dir)
        except Exception as exc:  # surface API/TTS errors instead of a 500 page
            flash(f"Something went wrong while generating the battle: {exc}")
            return redirect(url_for("index"))

    return render_template(
        "battle.html",
        object_a=object_a,
        object_b=object_b,
        turns=result["turns"],
        judge_raw=result["judge_raw"],
        session_id=session_id,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
