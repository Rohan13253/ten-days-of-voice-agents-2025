import logging
import json
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    tokenize,
    function_tool,
    RunContext,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
load_dotenv(".env.local")

# --- LOAD CONTENT ---
CONTENT_FILE = "day4_tutor_content.json"
def load_content():
    try:
        with open(CONTENT_FILE, "r") as f:
            return json.load(f)
    except:
        return []

COURSE_CONTENT = load_content()
CONTENT_TEXT = json.dumps(COURSE_CONTENT, indent=2)


# --- 1. BASE AGENT ---
class TutorBaseAgent(Agent):
    def __init__(self, instructions: str):
        super().__init__(instructions=instructions)

# --- 2. THE 3 AGENT PERSONAS ---

class LearnAgent(TutorBaseAgent):
    def __init__(self):
        super().__init__(
            instructions=(
                f"You are MATTHEW, a Lecturer. Syllabus: {CONTENT_TEXT}\n"
                "1. Introduce yourself as Matthew.\n"
                "2. Explain Variables or Loops.\n"
                "CRITICAL ROUTING INSTRUCTIONS:\n"
                "- If the user says 'quiz me' or 'test me' -> You MUST call 'transfer_to_quiz'.\n"
                "- If the user says 'let me teach', 'I will explain', or 'switch to student' -> You MUST call 'transfer_to_teach_back'."
            )
        )

    @function_tool
    async def transfer_to_quiz(self, context: RunContext):
        """Call this if the user wants a Quiz."""
        return QuizAgent()

    @function_tool
    async def transfer_to_teach_back(self, context: RunContext):
        """Call this if the user wants to Teach (Active Recall)."""
        return TeachBackAgent()


class QuizAgent(TutorBaseAgent):
    def __init__(self):
        super().__init__(
            instructions=(
                f"You are ALICIA, a strict Quiz Master. Syllabus: {CONTENT_TEXT}\n"
                "1. Introduce yourself as Alicia.\n"
                "2. Ask hard questions based on the syllabus.\n"
                "CRITICAL ROUTING INSTRUCTIONS:\n"
                "- If user says 'stop', 'learn', 'explain' -> Call 'transfer_to_learn'.\n"
                "- If user says 'let me teach' -> Call 'transfer_to_teach_back'."
            )
        )

    @function_tool
    async def transfer_to_learn(self, context: RunContext):
        """Transfer to Learn Mode."""
        return LearnAgent()

    @function_tool
    async def transfer_to_teach_back(self, context: RunContext):
        """Transfer to Teach-Back Mode."""
        return TeachBackAgent()


class TeachBackAgent(TutorBaseAgent):
    def __init__(self):
        super().__init__(
            instructions=(
                f"You are KEN, a confused Student. Syllabus: {CONTENT_TEXT}\n"
                "1. Introduce yourself as Ken.\n"
                "2. Act confused. Say 'I don't get it. Can you explain Variables/Loops to me?'\n"
                "3. Listen to the user's explanation and give feedback.\n"
                "CRITICAL ROUTING INSTRUCTIONS:\n"
                "- If user says 'quiz me' -> Call 'transfer_to_quiz'.\n"
                "- If user says 'explain to me' -> Call 'transfer_to_learn'."
            )
        )

    @function_tool
    async def transfer_to_learn(self, context: RunContext):
        """Transfer to Learn Mode."""
        return LearnAgent()

    @function_tool
    async def transfer_to_quiz(self, context: RunContext):
        """Transfer to Quiz Mode."""
        return QuizAgent()


# --- 3. ENTRYPOINT ---
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    await ctx.connect()

    # We use ONE stable voice (Matthew) for stability
    initial_tts = murf.TTS(
        voice="en-US-matthew", 
        style="Conversation",
        tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
        text_pacing=True
    )

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=initial_tts,
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
    )

    # Start with Learn Agent
    await session.start(
        agent=LearnAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))