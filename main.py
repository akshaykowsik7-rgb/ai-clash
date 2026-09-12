import asyncio
import os
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
import edge_tts
import pygame

load_dotenv()

# Primary model with fallback for high reliability
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = "gemini-2.5-flash"

API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None

# Initialize pygame mixer for audio playback
try:
    pygame.mixer.init()
    AUDIO_PLAYBACK_AVAILABLE = True
except Exception as e:
    AUDIO_PLAYBACK_AVAILABLE = False
    print(f"⚠️ Audio device initialization notice: {e}")

# =====================================================================
# DISTINCT MALAYALAM VOICES & UNIQUE REGIONAL SLANG CHARACTERS
# Fast, natural native Kerala pacing (+20% to +22% rate)
# =====================================================================

# AGENT A: "കോഴിക്കോട്ടുകാരൻ മിഥുൻ" (Midhun)
VOICE_A = {
    "voice": "ml-IN-MidhunNeural",
    "rate": "+22%",      # Fast, snappy native Kerala speech tempo
    "pitch": "+2Hz",
    "name": "Midhun [കോഴിക്കോട് വൈബ് - Malabar Street King]",
    "character_title": "GEMINI A (കോഴിക്കോട്ടുകാരൻ മിഥുൻ)",
}

# AGENT B: "കൊച്ചിക്കാരി ശോഭന ചേച്ചി" (Sobhana)
VOICE_B = {
    "voice": "ml-IN-SobhanaNeural",
    "rate": "+20%",      # Quick, cutting, articulate delivery
    "pitch": "+4Hz",
    "name": "Sobhana [കൊച്ചി വൈബ് - Sassy Roast Queen]",
    "character_title": "GEMINI B (കൊച്ചിക്കാരി ശോഭന ചേച്ചി)",
}

# JUDGE: "പഞ്ചായത്ത് പ്രസിഡന്റ് അമ്പാടി ചേട്ടൻ" (The Umpire)
VOICE_JUDGE = {
    "voice": "ml-IN-MidhunNeural",
    "rate": "+10%",      # Natural authoritative speed
    "pitch": "-12Hz",    # Deep, booming baritone
    "name": "The Umpire [പഞ്ചായത്ത് അമ്പാടി ചേട്ടൻ]",
    "character_title": "JUDGE (അമ്പാടി ചേട്ടൻ)",
}

# =====================================================================
# SYSTEM INSTRUCTION: HIGH-OCTANE MALAYALAM COMEDY ROAST
# =====================================================================
SYSTEM_INSTRUCTION = """You are participating in a savage, hilarious, unhinged Malayalam comedy debate.
Logic is strictly banned. Facts are banned. Common sense is banned.
Your only mission is to utterly annihilate your opponent's object with the funniest,
pettiest, most absurd roasts imaginable in authentic Kerala comedy style.

RULES FOR MAXIMUM COMEDY:
- Deliver rapid, punchy comebacks like classic Malayalam cinema legends (Salim Kumar, Jagathy, Suraj, Innocent style).
- Keep replies snappy: strictly 1 or 2 punchy sentences maximum.
- Never use real hate speech or offensive slurs — keep all insults focused on the ridiculous uselessness of the OBJECT.
- ALWAYS reply ONLY in Malayalam script (മലയാളം), never in English.
"""


def ask_gemini(prompt):
    """Sends prompt to Gemini model with system instruction and model fallback."""
    if not client:
        raise ValueError("Gemini API key is not configured.")
    
    # Try primary model first, fallback if unavailable
    for model_name in [MODEL, FALLBACK_MODEL]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=1.25,
                ),
            )
            return response.text.strip()
        except Exception as e:
            if model_name != FALLBACK_MODEL:
                continue
            raise e


async def synthesize_speech_async(text, voice_config, filename):
    """Synthesizes Malayalam text using Edge Neural TTS with fast, natural pacing."""
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
            time.sleep(0.06)
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"   [Playback error: {e}]")


def speak(text, voice_config, filename):
    """Converts Malayalam text to expressive speech at natural native pace and plays it out loud."""
    clean_text = text.strip()
    if not clean_text:
        return filename

    asyncio.run(synthesize_speech_async(clean_text, voice_config, filename))
    play_audio(filename)
    return filename


def debate(object_a, object_b, rounds=3):
    os.makedirs("audio_output", exist_ok=True)
    clip_num = 0

    print("\n" + "=" * 78)
    print("🔥  SAVAGE MALAYALAM ROAST BATTLE: KOZHIKODE VS KOCHI SHOWDOWN  🔥")
    print("=" * 78)
    print(f"🟢 {VOICE_A['character_title']} defending: {object_a}")
    print(f"🔴 {VOICE_B['character_title']} defending: {object_b}")
    print(f"⚖️ {VOICE_JUDGE['character_title']} watching the comedy unfold...\n")

    # -------------------------------------------------------------
    # ROUND 1 — OPENING ROASTS
    # -------------------------------------------------------------
    print("\n" + "-" * 78)
    print("💥 ROUND 1 — OPENING SLANG SHOWDOWN")
    print("-" * 78)

    a_prompt = f"""
You are Debate AI A — "കോഴിക്കോട്ടുകാരൻ മിഥുൻ".
Personality: Ultra-confident Malabar street debater. Swaggering, loud, fast-talking.
Your characteristic slang vocabulary:
- 'ന്റെ റബ്ബേ', 'പോപ്പാ അവിടുന്ന് തള്ളാതെ', 'ഡാ മോനേ ഉസ്താദേ', 'എന്തൊരു മുത്താപ്പാ ഇത്',
  'പച്ച ഉടായിപ്പ്', 'കട്ട ചതി', 'കണ്ടം വഴി ഓടിക്കോ', 'ആക്രി സാധനം', 'തൂക്കി ഒട്ടിക്കും ഞാൻ'.

You are defending: "{object_a}"
Your opponent is defending: "{object_b}"

Savage roast "{object_b}" using your Malabar slang flair! Hype up "{object_a}" like it's a Kozhikode legend,
and destroy "{object_b}" as an utter 'ദുരന്തം'.
Reply in exactly 1 or 2 punchy, fast sentences, written ONLY in Malayalam.
"""

    b_prompt = f"""
You are Debate AI B — "കൊച്ചിക്കാരി ശോഭന ചേച്ചി".
Personality: Sassy, sarcastic Kochi roast queen. Sharp tongue, devastating eye-roll humor.
Your characteristic slang vocabulary:
- 'അയ്യോടാ പാവം മോൻ', 'എന്തൊരു വെറുപ്പീര് ദുരന്തം', 'ഷൈൻ ചെയ്യാൻ നോക്കി ചമ്മി നാറല്ലേ മോനൂട്ടാ',
  'ഇതൊക്കെ വീട്ടിൽ അമ്മ അറിഞ്ഞു വാങ്ങിയതാണോ?', 'സീൻ കോണ്ട്രാ ആക്കല്ലേ', 'ചന്ത സാധനം',
  'ഇതൊക്കെ കണ്ടാൽ തെരുവ് പട്ടി പോലും തിരിഞ്ഞു നോക്കില്ല', 'അലമ്പ് ഐറ്റം'.

You are defending: "{object_b}"
Your opponent is defending: "{object_a}"

Mock "{object_a}" with peak Kochi sarcasm and condescending laughter!
Reply in exactly 1 or 2 punchy, sharp sentences, written ONLY in Malayalam.
"""

    # Agent A Turn
    print(f"\n🟢 {VOICE_A['character_title']} ({object_a}):")
    a_argument = ask_gemini(a_prompt)
    print(f"   \"{a_argument}\"")
    clip_num += 1
    clip_path = f"audio_output/{clip_num:02d}_A_Midhun.mp3"
    print(f"   🔊 Speaking ({VOICE_A['name']})...")
    speak(a_argument, VOICE_A, clip_path)

    time.sleep(0.3)

    # Agent B Turn
    print(f"\n🔴 {VOICE_B['character_title']} ({object_b}):")
    b_argument = ask_gemini(b_prompt)
    print(f"   \"{b_argument}\"")
    clip_num += 1
    clip_path = f"audio_output/{clip_num:02d}_B_Sobhana.mp3"
    print(f"   🔊 Speaking ({VOICE_B['name']})...")
    speak(b_argument, VOICE_B, clip_path)

    time.sleep(0.4)

    # -------------------------------------------------------------
    # DEBATE ROUNDS
    # -------------------------------------------------------------
    for round_number in range(2, rounds + 1):
        print("\n" + "-" * 78)
        print(f"💥 ROUND {round_number}")
        print("-" * 78)

        # Gemini A responds
        a_prompt = f"""
You are Debate AI A (കോഴിക്കോട്ടുകാരൻ മിഥുൻ).
Defending: "{object_a}"
Opponent defending: "{object_b}"

Your opponent just said this about your object:
"{b_argument}"

Fire back instantly with your fast Malabar street swagger ('പോപ്പാ തള്ളല്ലേ', 'ന്റെ റബ്ബേ', 'സീൻ ആക്കല്ലേ അളിയാ', 'കണ്ടം വഴി ഓട്')!
Tear apart "{object_b}" with hilarious, illogical comedy logic.
Reply in exactly 1 or 2 punchy sentences, written ONLY in Malayalam.
"""
        print(f"\n🟢 {VOICE_A['character_title']} ({object_a}):")
        a_argument = ask_gemini(a_prompt)
        print(f"   \"{a_argument}\"")
        clip_num += 1
        clip_path = f"audio_output/{clip_num:02d}_A_Midhun.mp3"
        print(f"   🔊 Speaking ({VOICE_A['name']})...")
        speak(a_argument, VOICE_A, clip_path)

        time.sleep(0.3)

        # Gemini B responds
        b_prompt = f"""
You are Debate AI B (കൊച്ചിക്കാരി ശോഭന ചേച്ചി).
Defending: "{object_b}"
Opponent defending: "{object_a}"

Your opponent just bragged:
"{a_argument}"

Laugh condescendingly at his ridiculous boast! Hit back with sharp Kochi sarcasm ('അയ്യോടാ മോൻ വലിയ ആളായല്ലോ', 'വെറും അലമ്പ്', 'ചമ്മി നാറല്ലേ', 'പച്ചത്തെമ്മാടിത്തരം')!
Completely humiliate "{object_a}".
Reply in exactly 1 or 2 punchy sentences, written ONLY in Malayalam.
"""
        print(f"\n🔴 {VOICE_B['character_title']} ({object_b}):")
        b_argument = ask_gemini(b_prompt)
        print(f"   \"{b_argument}\"")
        clip_num += 1
        clip_path = f"audio_output/{clip_num:02d}_B_Sobhana.mp3"
        print(f"   🔊 Speaking ({VOICE_B['name']})...")
        speak(b_argument, VOICE_B, clip_path)

        time.sleep(0.4)

    # -------------------------------------------------------------
    # FINAL JUDGMENT
    # -------------------------------------------------------------
    print("\n" + "=" * 78)
    print("⚖️  THE FINAL JUDGMENT — പഞ്ചായത്ത് പ്രസിഡന്റ് അമ്പാടി ചേട്ടൻ  ⚖️")
    print("=" * 78)

    judge_prompt = f"""
You are the debate judge: "പഞ്ചായത്ത് പ്രസിഡന്റ് അമ്പാടി ചേട്ടൻ".
Two hilarious AIs just fought a savage Malayalam slang roast battle:

Midhun (Kozhikode style) defended "{object_a}" and roasted "{object_b}":
{a_argument}

Sobhana (Kochi style) defended "{object_b}" and roasted "{object_a}":
{b_argument}

Judge who gave the funnier, more savage, more ridiculously petty Malayalam slang roast.
Be dramatic and hilarious like a bewildered Kerala local umpire.
Use funny expressions like 'എന്റെ മാതാവേ ഇവന്മാരുടെ തള്ളൽ കേട്ട് കിളി പോയി', 'രണ്ടിനും ഓസ്കാർ കൊടുക്കണം തരികിടയ്ക്ക്'.

Format your response strictly as:
WINNER: [Gemini A / Gemini B / DRAW]
SCORE:
Gemini A: X/10
Gemini B: X/10
REASON:
[Provide 2-3 hilarious Malayalam sentences explaining your verdict with comedy slang.]

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

    print("\n" + "=" * 78)
    print("🎉  DEBATE FINISHED — ALL AUDIO CLIPS SAVED IN /audio_output  🎉")
    print("=" * 78)


def run_demo():
    """Runs a fast-paced, highly expressive Malayalam roast battle showcasing unique characters and slangs."""
    os.makedirs("audio_output", exist_ok=True)
    print("\n" + "=" * 78)
    print("⚡ FAST-PACED MALAYALAM COMEDY ROAST BATTLE (NATIVE PACE) ⚡")
    print("   Topic: കട്ടൻ ചായ (Black Tea) vs പഴംപൊരി (Banana Fritters)")
    print("=" * 78)

    demo_dialogues = [
        (
            VOICE_A["character_title"],
            VOICE_A,
            "ഡാ മോനേ ഉസ്താദേ, പോപ്പാ അവിടുന്ന് തള്ളാതെ! ന്റെ റബ്ബേ, എണ്ണയിൽ മുങ്ങി ശ്വാസം മുട്ടി ചത്ത നിന്റെ ഈ പഴംപൊരി ഏത് നൂറ്റാണ്ടിലെ ആക്രിയാടാ? കട്ടൻ ചായ അടിച്ചാൽ തലച്ചോറ് റോക്കറ്റ് പോലെ പായും!",
            "demo_01_A_Midhun.mp3",
        ),
        (
            VOICE_B["character_title"],
            VOICE_B,
            "അയ്യോടാ പാവം മോൻ, ഷൈൻ ചെയ്യാൻ നോക്കി ചമ്മി നാറല്ലേ! നിന്റെ കട്ടൻ ചായ കണ്ടാൽ ഓവുചാലിലെ വെള്ളം തിളപ്പിച്ചു വെച്ച പോലെ ഉണ്ട്! പഴംപൊരിയുടെ സുവർണ്ണ മൊഞ്ച് നിന്റെ ഈ ചന്ത സാധനത്തിന് സ്വപ്നം കാണാൻ പറ്റുമോടാ?",
            "demo_02_B_Sobhana.mp3",
        ),
        (
            VOICE_A["character_title"],
            VOICE_A,
            "എന്തൊരു മുത്താപ്പാ ഇത്! നിന്റെ ആ കൊഴുത്ത പഴംപൊരി തിന്നാൽ കൊളസ്ട്രോൾ കൂടി നേരെ കണ്ടം വഴി ഓടേണ്ടി വരും! ഇത് പച്ച ഉടായിപ്പ്, കട്ടൻ ചായ ആണ് ഇവിടുത്തെ കിടുക്കാച്ചി ഐറ്റം!",
            "demo_03_A_Midhun.mp3",
        ),
        (
            VOICE_B["character_title"],
            VOICE_B,
            "പോടാപ്പാ സീൻ കോണ്ട്രാ ആക്കാതെ! കട്ടൻ ചായയിൽ ഇടാൻ അല്പം പഞ്ചസാര വാങ്ങാൻ പോലും വകയില്ലാത്ത നീയാണോ എന്നെ പഠിപ്പിക്കുന്നത്? എന്തൊരു വെറുപ്പീര് അലമ്പ് ദുരന്തം!",
            "demo_04_B_Sobhana.mp3",
        ),
        (
            VOICE_JUDGE["character_title"],
            VOICE_JUDGE,
            "എന്റെ മാതാവേ! ഇവന്മാരുടെ തള്ളൽ കേട്ട് എന്റെ കിളി മാത്രമല്ല, നാട്ടിലെ സകല കാക്കയും പറന്നുപോയി! എങ്കിലും ആ കട്ടൻ ചായയെ ഓവുചാൽ വെള്ളമെന്ന് വിളിച്ച് നാണം കെടുത്തിയ ശോഭന ചേച്ചിയാണ് ഇന്നത്തെ താരം!",
            "demo_05_JUDGE.mp3",
        ),
    ]

    for speaker, voice_cfg, text, fname in demo_dialogues:
        print(f"\n🗣️ {speaker}:")
        print(f"   \"{text}\"")
        path = os.path.join("audio_output", fname)
        print(f"   🔊 Speaking ({voice_cfg['name']})...")
        speak(text, voice_cfg, path)
        time.sleep(0.3)

    print("\n" + "=" * 78)
    print("✨ Fast-paced native Malayalam demo completed! Slangs & voices verified!")
    print("=" * 78 + "\n")


def main():
    print("=" * 78)
    print("   🎙️  GEMINI SAVAGE MALAYALAM ROAST BATTLE WITH NATIVE TTS  🎙️")
    print("=" * 78)

    if not os.environ.get("GEMINI_API_KEY"):
        print("\n⚠️  GEMINI_API_KEY not found in environment or .env file.")
        print("Options:")
        print("1. Run Demo Battle (Fast native pace, unique slangs & playback without API key)")
        print("2. Enter GEMINI_API_KEY now")
        choice = input("\nEnter choice (1 or 2, default 1): ").strip()

        if choice == "2":
            key = input("Enter your GEMINI_API_KEY: ").strip()
            if key:
                os.environ["GEMINI_API_KEY"] = key
                global client
                client = genai.Client(api_key=key)
            else:
                print("No key entered. Running fast demo instead...\n")
                run_demo()
                return
        else:
            run_demo()
            return

    print("\nAssign one object/product to each AI:")
    print("🟢 GEMINI A: കോഴിക്കോട്ടുകാരൻ മിഥുൻ (Malabar Street King)")
    print("🔴 GEMINI B: കൊച്ചിക്കാരി ശോഭന ചേച്ചി (Sassy Roast Queen)\n")

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
    if len(sys.argv) > 1 and sys.argv[1] in ["--demo", "-d", "demo"]:
        run_demo()
    else:
        main()