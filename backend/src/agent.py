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

# --- 1. LOAD CATALOG ---
def load_catalog():
    try:
        with open("grocery_catalog.json", "r") as f:
            return json.load(f)
    except:
        return []

CATALOG = load_catalog()
CATALOG_TEXT = json.dumps(CATALOG, indent=2)

RECIPES = {
    "sandwich": ["Whole Wheat Bread", "Peanut Butter", "Fruit Jam"],
    "pasta": ["Pasta Packet", "Tomato Pasta Sauce", "Cheddar Cheese Block"],
    "omelette": ["Farm Fresh Eggs (6pcs)", "Onions (1kg)", "Salted Chips"]
}

class GroceryAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are 'Swiggy Genie', a grocery assistant.\n"
                f"CATALOG:\n{CATALOG_TEXT}\n"
                "1. Add items to cart when asked.\n"
                "2. If user asks for 'ingredients for X', call 'add_recipe_bundle'.\n"
                "3. If user asks 'what is in my cart' or 'what did you add', YOU MUST call 'check_cart'.\n"
                "4. If user says 'checkout' or 'done', call 'place_order'."
            )
        )
        self.cart = []

    @function_tool
    async def add_to_cart(self, context: RunContext, item_name: str, quantity: int):
        print(f"🛒 ADDING: {item_name}")
        item_details = next((x for x in CATALOG if x['name'].lower() == item_name.lower()), None)
        price = item_details['price'] if item_details else 0
        self.cart.append({"item": item_name, "qty": quantity, "price": price})
        return f"Added {quantity} {item_name}."

    @function_tool
    async def add_recipe_bundle(self, context: RunContext, dish_name: str):
        print(f"🍳 BUNDLING: {dish_name}")
        dish_key = dish_name.lower()
        found_key = next((k for k in RECIPES.keys() if k in dish_key), None)
        
        if not found_key: return "No recipe found."
            
        items_to_add = RECIPES[found_key]
        added_list = []
        for item in items_to_add:
            cat_item = next((x for x in CATALOG if x['name'] == item), None)
            price = cat_item['price'] if cat_item else 0
            self.cart.append({"item": item, "qty": 1, "price": price})
            added_list.append(item)
            
        return f"Success! I have added these ingredients for {dish_name}: {', '.join(added_list)}."

    @function_tool
    async def check_cart(self, context: RunContext):
        """Use this to see what is in the cart."""
        print("👀 CHECKING CART")
        if not self.cart: return "Your cart is empty."
        
        # Create a nice summary string
        summary = ", ".join([f"{x['qty']} x {x['item']}" for x in self.cart])
        return f"Here is your cart: {summary}"

    @function_tool
    async def place_order(self, context: RunContext):
        print("✅ PLACING ORDER")
        if not self.cart: return "Cart is empty."
        
        total = sum(x['qty'] * x['price'] for x in self.cart)
        order_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": self.cart,
            "total": total,
            "status": "Placed"
        }
        with open("current_order.json", "w") as f:
            json.dump(order_data, f, indent=2)
        
        self.cart = []
        return f"Order placed! Total is {total} rupees. Saved to invoice."

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
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

    await session.start(agent=GroceryAgent(), room=ctx.room, room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()))
    await session.agent.say("Hi! Swiggy Genie here. What do you need?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))