import logging
import json
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
    tokenize,
    function_tool, # <--- Added this
    RunContext     # <--- Added this
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# --- DAY 2: BARISTA PERSONA & TOOLS ---

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a friendly barista at 'CyberCafe'.
            Your goal is to take a COMPLETE coffee order from the customer.
            You must collect exactly these 5 pieces of information:
            1. Drink Type (Latte, Espresso, etc.)
            2. Size (Small, Medium, Large)
            3. Milk Choice (Oat, Almond, Dairy, etc.)
            4. Extras (Sugar, syrup, or say 'none')
            5. Customer Name

            DO NOT assume any information. Ask friendly clarifying questions for any missing fields.
            Example: If they say 'I want a Latte', ask 'Great! What size would you like?'
            Once you have ALL 5 fields, call the 'save_order' tool to save the order to the system.
            After saving, thank the customer by name and end the conversation.""",
        )

    # --- THE TOOL TO SAVE THE ORDER ---
    @function_tool
    async def save_order(
        self, 
        context: RunContext, 
        drink_type: str, 
        size: str, 
        milk: str, 
        extras: str, 
        name: str
    ):
        """
        Call this function ONLY when you have collected ALL 5 order details from the customer.
        
        Args:
            drink_type: The type of drink (e.g. Latte, Cappuccino)
            size: The size of the drink (Small, Medium, Large)
            milk: The milk choice (Whole, Oat, Almond, None)
            extras: Any extras (Sugar, Syrup, None)
            name: The customer's name
        """
        
        order_data = {
            "drinkType": drink_type,
            "size": size,
            "milk": milk,
            "extras": [extras],
            "name": name
        }
        
        logger.info(f"📝 SAVING ORDER: {order_data}")
        print(f"✅ ORDER SAVED TO FILE: {order_data}")

        # Save to a local file
        with open("order.json", "w") as f:
            json.dump(order_data, f, indent=2)

        return "Order has been successfully saved to the kitchen system."


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(
                model="gemini-2.5-flash",
            ),
        tts=murf.TTS(
                voice="en-US-matthew", 
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))