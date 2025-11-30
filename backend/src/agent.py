import logging
import json
import os
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

# --- 1. LOAD CATALOG ---
CATALOG_FILE = "acp_catalog.json"
ORDER_FILE = "orders.json"

def load_catalog():
    try:
        with open(CATALOG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading catalog: {e}. Creating empty list.")
        return []

PRODUCTS = load_catalog()
# Convert to string for LLM context
CATALOG_CONTEXT = json.dumps(PRODUCTS, indent=2)

# --- 2. COMMERCE AGENT ---
class CommerceAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are 'InstaShop AI', a smart shopping assistant.\n"
                f"CATALOG:\n{CATALOG_CONTEXT}\n\n"
                "YOUR FLOW:\n"
                "1. BROWSE: Answer questions about products/prices.\n"
                "2. CART: Use 'add_to_cart' when user wants an item. DO NOT checkout yet.\n"
                "3. REVIEW: If user asks 'what is in my cart', read the items.\n"
                "4. CHECKOUT: Only call 'checkout_and_pay' when user says 'place order' or 'buy it all'.\n"
                "5. Be concise."
            )
        )
        # In-memory cart state
        self.cart = []

    @function_tool
    async def add_to_cart(self, context: RunContext, product_name: str, quantity: int):
        """Add an item to the shopping cart."""
        print(f"🛒 ADDING TO CART: {product_name} x {quantity}")
        
        # Fuzzy match
        selected = None
        for p in PRODUCTS:
            if product_name.lower() in p['name'].lower():
                selected = p
                break
        
        if not selected:
            return f"Error: '{product_name}' not found in catalog."

        self.cart.append({
            "name": selected['name'],
            "qty": quantity,
            "price": selected['price'],
            "currency": selected['currency']
        })
        
        return f"Added {quantity}x {selected['name']} to cart. Say 'Checkout' to finish."

    @function_tool
    async def checkout_and_pay(self, context: RunContext):
        """Finalize the order and save to file."""
        print("💳 CHECKING OUT...")
        if not self.cart:
            return "Your cart is empty."
        
        total = sum(item['qty'] * item['price'] for item in self.cart)
        currency = self.cart[0]['currency']
        
        order = {
            "order_id": f"ORD-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": self.cart,
            "total_amount": total,
            "currency": currency,
            "status": "CONFIRMED"
        }

        # Save to file safely
        history = []
        if os.path.exists(ORDER_FILE):
            try:
                with open(ORDER_FILE, "r") as f:
                    history = json.load(f)
            except:
                history = []
        
        history.append(order)
        
        with open(ORDER_FILE, "w") as f:
            json.dump(history, f, indent=2)
            
        # Clear cart
        self.cart = []
        return f"Order placed! ID: {order['order_id']}. Total: {total} {currency}."

    @function_tool
    async def check_cart(self, context: RunContext):
        """List items currently in the cart."""
        if not self.cart:
            return "Cart is empty."
        
        summary_list = []
        for i in self.cart:
            summary_list.append(f"{i['qty']}x {i['name']}")
            
        return f"Cart contains: {', '.join(summary_list)}"

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    print(f"🚀 CONNECTED TO ROOM: {ctx.room.name}")
    
    # Safe Voice (Matthew)
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

    await session.start(agent=CommerceAgent(), room=ctx.room, room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()))
    await session.agent.say("Hi! Welcome to InstaShop. What can I get for you?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))