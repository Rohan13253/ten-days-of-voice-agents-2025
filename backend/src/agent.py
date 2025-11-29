import logging
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
)
from livekit.plugins import murf, deepgram, google, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
load_dotenv(".env.local")

class GameMasterAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a Cyberpunk Game Master running a 5-Step Heist. Start when user says Hello.\n"
                "### MISSION STEPS ###\n"
                "1. START: 'Wake up, V. You are at the locked service door. Do you [HACK IT] or [KICK IT]?'\n"
                "2. LOBBY: 'You enter the lobby. Two guards are blocking the path. Do you [SNEAK PAST] or [FIGHT THEM]?'\n"
                "3. ELEVATOR: 'You reach the elevator, but it needs a keycard. Do you [SEARCH THE GUARD] or [OVERRIDE THE PANEL]?'\n"
                "4. LASERS: 'The elevator opens on Floor 99. A laser grid blocks the hallway. Do you [SLIDE UNDER] or [USE SMOKE BOMB]?'\n"
                "5. SERVER ROOM: 'You made it. The Golden Datachip is hovering in the server rack. Do you [GRAB IT]?'\n"
                "6. FINISH: 'MISSION COMPLETE. You escape into the night with the data.'\n"
                "Keep descriptions punchy and noir-style."
            )
        )

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
    tts = murf.TTS(
        voice="en-US-matthew", 
        style="Narration",
        tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
        text_pacing=True
    )

    session = AgentSession(
        stt=deepgram.STT(model="nova-2"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=tts,
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
    )

    await session.start(agent=GameMasterAgent(), room=ctx.room, room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()))

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))