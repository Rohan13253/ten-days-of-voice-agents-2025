import logging
import json
from datetime import datetime
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

# --- 1. LOAD KNOWLEDGE BASE ---
def load_faq():
    try:
        with open("day5_zomato_faq.json", "r") as f:
            return json.load(f)
    except:
        return []

FAQ_DATA = load_faq()
FAQ_TEXT = json.dumps(FAQ_DATA, indent=2)

# --- 2. THE SDR AGENT ---
class ZomatoSDR(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are 'Matthew', a Zomato Sales Representative.\n"
                "Your goal is to help restaurant owners list their business on Zomato.\n\n"
                f"USE THIS KNOWLEDGE BASE FOR ANSWERS:\n{FAQ_TEXT}\n\n"
                "YOUR TASKS:\n"
                "1. Greet the user warmly.\n"
                "2. Answer their questions about Zomato (Cost, Delivery, Documents).\n"
                "3. CRITICAL: You must collect these 4 pieces of info to create a lead:\n"
                "   - Name\n"
                "   - Restaurant Name\n"
                "   - Phone Number\n"
                "   - City\n"
                "4. Once you have ALL 4, call the 'capture_lead' tool immediately.\n"
                "5. Keep your answers short and professional."
            )
        )

    @function_tool
    async def capture_lead(self, context: RunContext, name: str, restaurant_name: str, phone: str, city: str):
        """
        Call this tool ONLY when you have collected Name, Restaurant Name, Phone, and City.
        """
        lead_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "restaurant": restaurant_name,
            "phone": phone,
            "city": city,
            "status": "Qualified"
        }
        
        # Save to JSON file
        filename = "zomato_leads.json"
        existing_leads = []
        
        try:
            with open(filename, "r") as f:
                existing_leads = json.load(f)
        except:
            pass # File doesn't exist yet, start empty

        existing_leads.append(lead_data)
        
        with open(filename, "w") as f:
            json.dump(existing_leads, f, indent=2)
            
        print(f"✅ LEAD SAVED: {lead_data}")
        return "Perfect! I have saved your details. Our onboarding team will call you within 24 hours."

# --- 3. STARTUP LOGIC ---
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    await ctx.connect()

    # Using the SAFE Voice (Matthew) + SAFE STT (Nova-2)
    tts = murf.TTS(
        voice="en-US-matthew",
        style="Conversation",
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

    await session.start(
        agent=ZomatoSDR(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )
    
    await session.agent.say("Hello! Welcome to Zomato Partner Support. Are you looking to list your restaurant?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))