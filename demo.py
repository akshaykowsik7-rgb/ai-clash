import asyncio
import os
import random
import sys
import time

# Ensure UTF-8 output on Windows consoles for Malayalam text and emojis
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
import edge_tts
import pygame
from pydub import AudioSegment

load_dotenv()

# gemini-1.5-flash and gemini-2.0-flash-lite have both been shut down.
# gemini-2.5-flash is the current Flash-tier model and what the free tier
# gives you access to.
MODEL = "gemini-3.6-flash"
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None

# Free-tier RPM is low and project-specific (often single digits for
# Flash models). This is the minimum gap enforced between Gemini calls
# so a single debate run doesn't blow through the per-minute limit.
# Raise this if you still see 429 errors; lower it if you're on a paid tier.
MIN_SECONDS_BETWEEN_CALLS = 7
_last_call_time = 0.0

# Initialize pygame mixer for audio playback
try:
    pygame.mixer.init()
    AUDIO_PLAYBACK_AVAILABLE = True
except Exception as e:
    AUDIO_PLAYBACK_AVAILABLE = False
    print(f"⚠️ Audio device initialization notice: {e}")

# Gap (in milliseconds) inserted between speaker turns when the individual
# clips are stitched into one continuous "conversation" track.
CONVERSATION_GAP_MS = 350

# =====================================================================
# DISTINCT MALAYALAM VOICES & PERSONAS
# =====================================================================
# Agent A: Midhun (Male) - Energetic, cocky Kerala street-smart debater
VOICE_A = {
    "voice": "ml-IN-MidhunNeural",
    "rate": "+12%",
    "pitch": "+2Hz",
    "name": "Midhun (Male - Street Slang Roaster)",
}

# Agent B: Sobhana (Female) - Sassy, sharp, sarcastic comedy roaster
VOICE_B = {
    "voice": "ml-IN-SobhanaNeural",
    "rate": "+10%",
    "pitch": "+4Hz",
    "name": "Sobhana (Female - Sassy Roast Queen)",
}

# Judge: Midhun (Male) modulated to be deep, dramatic, and booming
VOICE_JUDGE = {
    "voice": "ml-IN-MidhunNeural",
    "rate": "-5%",
    "pitch": "-15Hz",
    "name": "The Umpire (Deep & Dramatic)",
}

# =====================================================================
# SYSTEM INSTRUCTION WITH AUTHENTIC MALAYALAM SLANG & ROAST CULTURE
# =====================================================================
SYSTEM_INSTRUCTION = """You are a savage, unhinged, hilarious Malayalam comedy debater.
Logic is strictly banned. Facts are banned. Common sense is banned.
Your only goal is to completely destroy your opponent's object with the pettiest,
most absurd, most illogical roast possible in authentic Kerala comedy style.

USE HILARIOUS MALAYALAM STREET SLANG AND COMEDY TROPES:
- Use iconic colloquial slang naturally: 'ഡാ മോനേ', 'പോടാപ്പാ', 'തള്ളല്ലേ തള്ളല്ലേ',
  'എന്തര് തേങ്ങയാടാ ഇത്', 'വെറും അലമ്പ്', 'ദുരന്തം', 'സീൻ കോണ്ട്രാ', 'ഊള സാധനം',
  'കണ്ടം വഴി ഓടിക്കോ', 'പച്ച ഉടായിപ്പ്', 'ആക്രി സാധനം', 'വെറുപ്പീര്', 'തേപ്പ്',
  'ഇതൊക്കെ കണ്ടാൽ തെരുവ് പട്ടി പോലും തിരിഞ്ഞു നോക്കില്ല', 'ഷൈൻ ചെയ്യാൻ നോക്കല്ലേ'.
- Act like a classic Malayalam cinema comedy character (inspired by Salim Kumar / Suraj / Jagathy roast styles).
- Never use real hate speech, obscenities, or slurs — keep the insult entirely focused
  on how ridiculously pathetic and useless the OBJECT is.
- ALWAYS reply ONLY in Malayalam script (മലയാളം), never in English.
- Keep replies punchy, dramatic, and exactly 1 to 2 sentences."""


def ask_gemini(prompt, max_retries=5):
    """Sends prompt to Gemini model with system instruction.

    Paces requests to respect free-tier RPM and retries with exponential
    backoff (plus jitter) if the API returns a 429 rate-limit error.
    """
    if not client:
        raise ValueError("Gemini API key is not configured.")

    global _last_call_time

    for attempt in range(max_retries):
        # Enforce a minimum gap since the last successful call.
        elapsed = time.time() - _last_call_time
        if elapsed < MIN_SECONDS_BETWEEN_CALLS:
            time.sleep(MIN_SECONDS_BETWEEN_CALLS - elapsed)

        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=1.25,
                ),
            )
            _last_call_time = time.time()
            return response.text.strip()

        except genai_errors.ClientError as e:
            is_rate_limit = "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e)
            if is_rate_limit and attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"   ⏳ Rate limited. Waiting {wait:.1f}s before retry "
                      f"({attempt + 1}/{max_retries})...")
                time.sleep(wait)
                continue
            raise

    raise RuntimeError("Exceeded max retries calling Gemini API.")


async def synthesize_speech_async(text, voice_config, filename):
    """Synthesizes Malayalam text using Edge Neural TTS with custom rate & pitch."""
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice_config["voice"],
        rate=voice_config["rate"],
        pitch=voice_config["pitch"],
    )
    await communicate.save(filename)


def play_audio(filename):
    """Plays audio file through speakers and waits for completion."""
    if not AUDIO_PLAYBACK_AVAILABLE or not os.path.exists(filename):
        return
    try:
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.08)
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"   [Playback error: {e}]")


def speak(text, voice_config, filename):
    """Converts Malayalam text to expressive speech and plays it out loud."""
    # Ensure text is not empty
    clean_text = text.strip()
    if not clean_text:
        return filename

    # Synthesize to MP3
    asyncio.run(synthesize_speech_async(clean_text, voice_config, filename))

    # Play aloud
    play_audio(filename)
    return filename


def combine_audio_clips(clip_paths, output_path, gap_ms=CONVERSATION_GAP_MS):
    """Stitches a list of individual turn clips into ONE continuous audio file,
    with a short pause between speakers, so the result plays back like a real
    back-and-forth conversation instead of a folder of separate clips you have
    to click through one by one.
    """
    existing = [p for p in clip_paths if p and os.path.exists(p)]
    if not existing:
        return None

    gap = AudioSegment.silent(duration=gap_ms)
    combined = AudioSegment.empty()
    for i, path in enumerate(existing):
        try:
            clip = AudioSegment.from_file(path)
        except Exception as e:
            print(f"   ⚠️ Skipping {path} while stitching ({e})")
            continue
        combined += clip
        if i < len(existing) - 1:
            combined += gap

    combined.export(output_path, format="mp3")
    return output_path


def debate(object_a, object_b, rounds=5):
    os.makedirs("audio_output", exist_ok=True)
    clip_num = 0
    conversation_clips = []

    print("\n" + "=" * 75)
    print("🔥  GEMINI VS GEMINI — SAVAGE MALAYALAM ROAST BATTLE (WITH TTS)  🔥")
    print("=" * 75)
    print(f"🟢 GEMINI A ({VOICE_A['name']}) defending: {object_a}")
    print(f"🔴 GEMINI B ({VOICE_B['name']}) defending: {object_b}")
    print(f"⚖️ JUDGE ({VOICE_JUDGE['name']}) is watching the drama...\n")

    # -------------------------------------------------------------
    # ROUND 1 — OPENING ROASTS
    # -------------------------------------------------------------
    print("\n" + "-" * 75)
    print("💥 ROUND 1 — OPENING SLANG ROASTS")
    print("-" * 75)

    a_prompt = f"""
You are Debate AI A (Voice: Midhun, arrogant Kerala street roaster).
You are defending: "{object_a}"
Your opponent is defending: "{object_b}"

Savage roast "{object_b}" right out of the gate! Use hilarious Malayalam slang
(e.g., 'ഡാ മോനേ', 'എന്തര് തേങ്ങയാടാ ഇത്', 'തള്ളല്ലേ', 'ആക്രി സാധനം').
Explain with complete comedy exaggeration why "{object_b}" is a useless 'ദുരന്തം'
compared to "{object_a}".
Reply in exactly 1 or 2 punchy sentences, written ONLY in Malayalam.
"""

    b_prompt = f"""
You are Debate AI B (Voice: Sobhana, sassy, sharp Kerala comedy queen).
You are defending: "{object_b}"
Your opponent is defending: "{object_a}"

Clap back savagely at "{object_a}"! Use sassy, mocking Malayalam slang
(e.g., 'അയ്യേ', 'വെറും അലമ്പ്', 'എന്തൊരു വെറുപ്പീര്', 'കണ്ടം വഴി ഓട്').
Make "{object_a}" sound like the most embarrassing piece of junk in Kerala history.
Reply in exactly 1 or 2 punchy sentences, written ONLY in Malayalam.
"""

    # Agent A Turn
    print(f"\n🟢 GEMINI A [Midhun] ({object_a}):")
    a_argument = ask_gemini(a_prompt)
    print(f"   \"{a_argument}\"")
    clip_num += 1
    clip_path = f"audio_output/{clip_num:02d}_A_Midhun.mp3"
    print(f"   🔊 Speaking ({VOICE_A['name']})...")
    speak(a_argument, VOICE_A, clip_path)
    conversation_clips.append(clip_path)

    time.sleep(0.4)

    # Agent B Turn
    print(f"\n🔴 GEMINI B [Sobhana] ({object_b}):")
    b_argument = ask_gemini(b_prompt)
    print(f"   \"{b_argument}\"")
    clip_num += 1
    clip_path = f"audio_output/{clip_num:02d}_B_Sobhana.mp3"
    print(f"   🔊 Speaking ({VOICE_B['name']})...")
    speak(b_argument, VOICE_B, clip_path)
    conversation_clips.append(clip_path)

    time.sleep(0.6)

    # -------------------------------------------------------------
    # DEBATE ROUNDS
    # -------------------------------------------------------------
    for round_number in range(2, rounds + 1):
        print("\n" + "-" * 75)
        print(f"💥 ROUND {round_number}")
        print("-" * 75)

        # Gemini A responds
        a_prompt = f"""
You are Debate AI A (Midhun). You are defending: "{object_a}".
Your opponent is defending: "{object_b}".

Your opponent just said this about your object:
"{b_argument}"

Destroy them! Call out their ridiculous claim with heavy Malayalam comedy slang
('ഡാ മോനേ ദിനേശാ', 'സീൻ കോണ്ട്രാ', 'ഊളത്തരം', 'തള്ളലിന് ഒരു പരിധിയില്ലേ').
Roast "{object_b}" even harder with absurd, made-up comedy logic.
Reply in exactly 1 or 2 punchy sentences, written ONLY in Malayalam.
"""
        print(f"\n🟢 GEMINI A [Midhun] ({object_a}):")
        a_argument = ask_gemini(a_prompt)
        print(f"   \"{a_argument}\"")
        clip_num += 1
        clip_path = f"audio_output/{clip_num:02d}_A_Midhun.mp3"
        print(f"   🔊 Speaking ({VOICE_A['name']})...")
        speak(a_argument, VOICE_A, clip_path)
        conversation_clips.append(clip_path)

        time.sleep(0.4)

        # Gemini B responds
        b_prompt = f"""
You are Debate AI B (Sobhana). You are defending: "{object_b}".
Your opponent is defending: "{object_a}".

Your opponent just bragged:
"{a_argument}"

Laugh in their face! Mock them with peak Malayalam sarcasm
('അയ്യോടാ', 'പച്ച ഉടായിപ്പ്', 'ഇതൊക്കെ കേട്ടാൽ നാണക്കേട് കൊണ്ട് ചത്തുപോകും', 'കണ്ടം വഴി വിട്ടോ').
Prove why "{object_a}" is absolute garbage.
Reply in exactly 1 or 2 punchy sentences, written ONLY in Malayalam.
"""
        print(f"\n🔴 GEMINI B [Sobhana] ({object_b}):")
        b_argument = ask_gemini(b_prompt)
        print(f"   \"{b_argument}\"")
        clip_num += 1
        clip_path = f"audio_output/{clip_num:02d}_B_Sobhana.mp3"
        print(f"   🔊 Speaking ({VOICE_B['name']})...")
        speak(b_argument, VOICE_B, clip_path)
        conversation_clips.append(clip_path)

        time.sleep(0.6)

    # -------------------------------------------------------------
    # FINAL JUDGMENT
    # -------------------------------------------------------------
    print("\n" + "=" * 75)
    print("⚖️  THE FINAL JUDGMENT — KERALA PANCHAYAT STYLE")
    print("=" * 75)

    judge_prompt = f"""
You are an impartial, hilarious Malayalam debate judge.
Two AIs just argued fiercely in Malayalam:

Gemini A defended "{object_a}" and roasted "{object_b}":
{a_argument}

Gemini B defended "{object_b}" and roasted "{object_a}":
{b_argument}

Decide who landed the funniest, most absurd, and most savage Malayalam roast.
Real logic and facts count AGAINST them — the dumber and funnier the slang roast, the better!

Format your response strictly as:
WINNER: [Gemini A / Gemini B / DRAW]
SCORE:
Gemini A: X/10
Gemini B: X/10
REASON:
[Provide 2-3 hilarious Malayalam sentences explaining your verdict with comedy slang like 'ഇരുവർക്കും നല്ല ഉടായിപ്പ് ഉണ്ട്', 'എന്നാലും ആ തള്ളൽ കിടുക്കി', etc.]

Keep WINNER, SCORE, and REASON labels in English, but write all reason text strictly in Malayalam.
"""

    judgment = ask_gemini(judge_prompt)
    print(f"\n⚖️ JUDGE VERDICT:\n{judgment}")

    # Extract Malayalam explanation for TTS
    reason_text = judgment
    if "REASON:" in judgment:
        reason_text = judgment.split("REASON:")[-1].strip()

    clip_num += 1
    judge_audio_path = f"audio_output/{clip_num:02d}_JUDGE.mp3"
    print(f"\n   🔊 Judge Speaking ({VOICE_JUDGE['name']})...")
    speak(reason_text, VOICE_JUDGE, judge_audio_path)
    conversation_clips.append(judge_audio_path)

    # -------------------------------------------------------------
    # STITCH EVERYTHING INTO ONE CONTINUOUS CONVERSATION TRACK
    # -------------------------------------------------------------
    print("\n🎬 Stitching all turns into one continuous conversation track...")
    full_path = "audio_output/00_full_conversation.mp3"
    combine_audio_clips(conversation_clips, full_path)
    print(f"   ✅ Full conversation saved: {full_path}")
    print("   🔊 Playing the full conversation start to finish...")
    play_audio(full_path)

    print("\n" + "=" * 75)
    print("🎉  DEBATE FINISHED — ALL AUDIO CLIPS SAVED IN /audio_output  🎉")
    print("=" * 75)


def run_demo():
    """Runs an instant demo roast battle using pre-recorded authentic Malayalam dialogues to test TTS & slang."""
    os.makedirs("audio_output", exist_ok=True)
    print("\n" + "=" * 75)
    print("⚡ RUNNING EXPRESSIVE MALAYALAM TTS DEMO BATTLE ⚡")
    print("   Topic: കട്ടൻ ചായ (Black Tea) vs പഴംപൊരി (Banana Fritters)")
    print("=" * 75)

    demo_dialogues = [
        (
            "GEMINI A (Midhun)",
            VOICE_A,
            "ഡാ മോനേ, നിന്റെ പഴംപൊരി എണ്ണയിൽ മുങ്ങി ശ്വാസം മുട്ടി ചത്ത ഒരു ദുരന്തം സാധനമാണ്! കട്ടൻ ചായ കുടിച്ചാൽ തലച്ചോറ് റോക്കറ്റ് പോലെ പായും!",
            "demo_01_A.mp3",
        ),
        (
            "GEMINI B (Sobhana)",
            VOICE_B,
            "അയ്യേ തള്ളല്ലേ മോനേ! നിന്റെ കട്ടൻ ചായ കണ്ടാൽ ഓവുചാലിലെ വെള്ളം തിളപ്പിച്ചു വെച്ച പോലെ ഉണ്ട്! പഴംപൊരിയുടെ സുവർണ്ണ ഭംഗി നിനക്ക് മനസ്സിലാവില്ല!",
            "demo_02_B.mp3",
        ),
        (
            "GEMINI A (Midhun)",
            VOICE_A,
            "ഓഹോ, വലിയ ഷൈൻ ചെയ്യണ്ട! നിന്റെ പഴംപൊരി തിന്നാൽ കൊളസ്ട്രോൾ കൂടി നേരെ കണ്ടം വഴി ഓടേണ്ടി വരും! കട്ടൻ ചായ ആണ് ഇവിടുത്തെ കിടുക്കാച്ചി ഐറ്റം!",
            "demo_03_A.mp3",
        ),
        (
            "GEMINI B (Sobhana)",
            VOICE_B,
            "പോടാപ്പാ ഊളത്തരം പറയാതെ! നിന്റെ കട്ടൻ ചായയിൽ അല്പം പഞ്ചസാര ഇടാൻ പോലും ഗതിയില്ലാത്ത നീയാണോ എന്നെ ഉപദേശിക്കുന്നത്? വെറും അലമ്പ്!",
            "demo_04_B.mp3",
        ),
        (
            "JUDGE (The Umpire)",
            VOICE_JUDGE,
            "രണ്ടിന്റെയും തള്ളൽ കേട്ട് എന്റെ കിളി പോയി! എങ്കിലും ആ പഴംപൊരിയെ ഓവുചാൽ വെള്ളമെന്ന് വിളിച്ച ആ ശ്വാസതടസ്സമില്ലാത്ത റോസ്റ്റിന് ശോഭന ചേച്ചി ജയിച്ചിരിക്കുന്നു!",
            "demo_05_JUDGE.mp3",
        ),
    ]

    demo_clips = []
    for speaker, voice_cfg, text, fname in demo_dialogues:
        print(f"\n🗣️ {speaker}:")
        print(f"   \"{text}\"")
        path = os.path.join("audio_output", fname)
        print(f"   🔊 Speaking ({voice_cfg['name']})...")
        speak(text, voice_cfg, path)
        demo_clips.append(path)
        time.sleep(0.5)

    # Stitch the whole demo into one continuous conversation file so it plays
    # back start-to-finish like a real exchange, instead of five separate
    # clips you'd have to open and press play on one at a time.
    print("\n🎬 Stitching demo turns into one continuous conversation track...")
    full_demo_path = os.path.join("audio_output", "00_full_conversation_demo.mp3")
    combine_audio_clips(demo_clips, full_demo_path)
    print(f"   ✅ Full demo conversation saved: {full_demo_path}")
    print("   🔊 Playing the full demo conversation start to finish...")
    play_audio(full_demo_path)

    print("\n" + "=" * 75)
    print("✨ Demo completed successfully! Voices are realistic, expressive, and working!")
    print("=" * 75 + "\n")


def main():
    print("=" * 75)
    print("   🎙️  GEMINI MALAYALAM ROAST BATTLE WITH EXPRESSIVE TTS  🎙️")
    print("=" * 75)

    if not os.environ.get("GEMINI_API_KEY"):
        print("\n⚠️  GEMINI_API_KEY not found in environment or .env file.")
        print("Options:")
        print("1. Run Demo Battle (Tests Malayalam voices, slang, & playback without API key)")
        print("2. Enter GEMINI_API_KEY now")
        choice = input("\nEnter choice (1 or 2, default 1): ").strip()

        if choice == "2":
            key = input("Enter your GEMINI_API_KEY: ").strip()
            if key:
                os.environ["GEMINI_API_KEY"] = key
                global client
                client = genai.Client(api_key=key)
            else:
                print("No key entered. Running demo instead...\n")
                run_demo()
                return
        else:
            run_demo()
            return

    # If API key is present or provided
    print("\nAssign one object/product to each AI. They will roast each")
    print("other in savage Malayalam slang with different expressive voices!\n")

    object_a = input("Object/product for GEMINI A (e.g., കട്ടൻ ചായ, പൊട്ടിയ കുട): ").strip()
    object_b = input("Object/product for GEMINI B (e.g., പഴംപൊരി, തുരുമ്പിച്ച സൈക്കിൾ): ").strip()

    if not object_a or not object_b:
        print("Please enter both objects to start the battle. Running demo battle instead...")
        run_demo()
        return

    rounds_input = input("Number of rounds (default 3): ").strip()
    if rounds_input.isdigit() and int(rounds_input) > 0:
        rounds = int(rounds_input)
    else:
        rounds = 3

    debate(object_a, object_b, rounds)


if __name__ == "__main__":
    # Check if user requested direct demo via command line argument
    if len(sys.argv) > 1 and sys.argv[1] in ["--demo", "-d", "demo"]:
        run_demo()
    else:
        main()