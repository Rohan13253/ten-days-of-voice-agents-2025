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

# --- DATABASE HANDLER ---
DB_FILE = "fraud_db.json"

def load_case(username="Rohan"):
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            # Find the user
            for case in data:
                if case["username"] == username:
                    return case
    except:
        pass
    return None

def update_db(username, new_status, note):
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        
        for case in data:
            if case["username"] == username:
                case["status"] = new_status
                case["notes"] = note
                break
        
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 DATABASE UPDATED: {new_status} - {note}")
    except Exception as e:
        print(f"Error updating DB: {e}")

# --- AGENT LOGIC ---
class FraudAlertAgent(Agent):
    def __init__(self):
        # Load the case for "Rohan" automatically for this demo
        self.case = load_case("Rohan")
        
        # Build the dynamic prompt based on the DB entry
        txn = self.case['transaction']
        context_prompt = (
            f"You are an HDFC Bank Fraud Prevention Officer.\n"
            f"You are calling the customer '{self.case['username']}' about a suspicious transaction on card ending {self.case['card_last4']}.\n\n"
            f"TRANSACTION DETAILS:\n"
            f"- Merchant: {txn['merchant']}\n"
            f"- Amount: {txn['amount']}\n"
            f"- Time: {txn['time']}\n\n"
            "YOUR FLOW:\n"
            "1. Introduce yourself as HDFC Fraud Dept. Ask if you are speaking to the customer.\n"
            "2. VERIFICATION: Before discussing details, ask for their 'Year of Birth' to verify identity.\n"
            "3. If they give the wrong year (not " + self.case['security_identifier'] + "), say you cannot proceed and call 'end_call_failed'.\n"
            "4. If verified, read the transaction details clearly.\n"
            "5. Ask: 'Did you authorize this transaction?'\n"
            "6. If YES -> Call 'mark_safe'.\n"
            "7. If NO -> Call 'mark_fraud'.\n"
            "Keep your tone professional, calm, and serious."
        )

        super().__init__(instructions=context_prompt)

    @function_tool
    async def mark_safe(self, context: RunContext):
        """Call this if the customer confirms they MADE the transaction (it is safe)."""
        update_db("Rohan", "confirmed_safe", "Customer verified transaction via Voice.")
        return "Thank you. I have marked this transaction as safe. You can continue using your card. Goodbye."

    @function_tool
    async def mark_fraud(self, context: RunContext):
        """Call this if the customer says they DID NOT make the transaction (it is fraud)."""
        update_db("Rohan", "confirmed_fraud", "Customer denied transaction. Card blocked immediately.")
        return "Understood. I have blocked your card immediately to prevent further loss. You will receive a new card in 3-5 working days."

    @function_tool
    async def end_call_failed(self, context: RunContext):
        """Call this if identity verification fails."""
        update_db("Rohan", "verification_failed", "Caller failed security question.")
        return "I am sorry, but I cannot verify your identity. Please visit your nearest branch. Goodbye."

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
    # Use a professional, deep voice for the Bank Officer
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

    await session.start(agent=FraudAlertAgent(), room=ctx.room, room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()))
    
    # Start the call immediately
    await session.agent.say("Hello. This is a call from HDFC Bank Fraud Prevention. Am I speaking with Rohan?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))