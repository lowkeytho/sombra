# =========================
# IMPORTS
# =========================
import discord
from discord.ext import commands, tasks
import json, os, random
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

DATA_FILE = "players.json"
WORLD_FILE = "world.json"

PAUSED = False

# =========================
# LOCATIONS / WORLD
# =========================

LOCATIONS = {
    "Medellin": {"profit_mult": 1.0, "heat_mult": 1.0},
    "Miami": {"profit_mult": 1.3, "heat_mult": 1.4},
    "Los Angeles": {"profit_mult": 1.5, "heat_mult": 1.6},
    "New York": {"profit_mult": 1.6, "heat_mult": 1.7},
    "Chicago": {"profit_mult": 1.4, "heat_mult": 1.5},
    "Mexico City": {"profit_mult": 1.2, "heat_mult": 1.3},
    "Bogota": {"profit_mult": 1.1, "heat_mult": 0.9},
    "Sinaloa": {"profit_mult": 1.2, "heat_mult": 1.0}
}

CITY_CARTELS = {
    "Sinaloa": "Sinaloa Cartel",
    "Medellin": "Medellin Cartel",
    "Bogota": "Norte del Valle",
    "Mexico City": "Federation",
    "Miami": "Vice Syndicate",
    "Los Angeles": "LA Familia",
    "New York": "East Coast Network",
    "Chicago": "Midwest Outfit"
}

# =========================
# DATA HELPERS
# =========================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    return json.load(open(DATA_FILE))

def save_data(data):
    with open(DATA_FILE + ".tmp", "w") as f:
        json.dump(data, f, indent=4)
    os.replace(DATA_FILE + ".tmp", DATA_FILE)

def load_world():
    if not os.path.exists(WORLD_FILE):
        return {
            "cartels": {
                k: {
                    "name": v,
                    "power": random.randint(70, 90),
                    "aggression": random.randint(40, 70),
                    "strategy": "balanced",
                    "target": None,
                    "adaptation": 0,
                    "personality": random.choice(["aggressive", "greedy", "strategic", "cautious"])
                }
                for k, v in CITY_CARTELS.items()
            },
            "relations": {},
            "territories": {
                city: {
                    "owner": None,
                    "control": 0,
                    "conflict": False,
                    "defense": 0
                }
                for city in ["Los Angeles","Miami","New York","Chicago"]
            }
        }
    return json.load(open(WORLD_FILE))

def save_world(world):
    with open(WORLD_FILE + ".tmp", "w") as f:
        json.dump(world, f, indent=4)
    os.replace(WORLD_FILE + ".tmp", WORLD_FILE)

def sanitize_world(world):
    world.setdefault("territories", {})
    world.setdefault("cartels", {})

    for city, t in world["territories"].items():
        t.setdefault("owner", None)
        t.setdefault("control", 0)
        t.setdefault("defense", 0)
        t.setdefault("conflict", False)

    for cartel in world["cartels"].values():
        cartel.setdefault("name", "Unknown")
        cartel.setdefault("power", 50)
        cartel.setdefault("strategy", "balanced")

# =========================
# PLAYER
# =========================

def create_player():
    return {
        "name": "",
        "cartel": None,

        "cash": 5000,
        "bank": 10000,
        "heat": 10,
        "dea": 0,

        "location": "Medellin",
        "day": 1,

        "trigger_world_event": False,

        "in_prison": False, 
        "sentence": 0,

        "supply": 0,

        "community_support": 0,   # reduces informants / DEA pressure
        "intel_level": 0,         # improves detection accuracy

        "reputation": 0,
        "rank": "Street Runner",
        
        "npc_memory": {},

        "crew": [],
        "inventory": {
            "low": 0,
            "pure": 0,
            "high": 0
        },

        "memory": [],
        "dea_stage": "low",
        "war_stage": 0,

        "hierarchy": {
            "underboss": None,
            "lieutenants": [],
            "capos": []
        },

        "assets": {
            "warehouse": 0,
            "safehouse": 0,
            "vehicles": 0,
            "lab": 0
        },

        "firepower": 0, 

        "businesses": [],
        "npc_relations": {},

        "partner": None,
        "kids": [],

        "stress": 0,
        "style": "neutral"
    }

def ensure_player(p):
    if not isinstance(p, dict):
        return create_player()

    default = create_player()

    if p.get("cash", 0) == 0:
        p["cash"] = 5000

    if p.get("bank", 0) == 0:
        p["bank"] = 10000

    for key, value in default.items():
        if key not in p:
            p[key] = value

    return p

# =========================
# NPC GENERATION
# =========================

def update_memory(p, user_input, ai_reply):
    entry = {
        "input": user_input,
        "result": ai_reply[:100]
    }

    p["memory"].append(entry)

    # personality impact tracking
    if "threat" in user_input.lower():
        p["style"] = "aggressive"

    elif "help" in user_input.lower():
        p["style"] = "diplomatic"

    elif "family" in user_input.lower():
        p["style"] = "loyal"

    if len(p["memory"]) > 10:
        p["memory"].pop(0)

def generate_npc(role):
    base_name = random.choice([
        "Javier","Luis","Mateo","Carlos","Diego","Andres","Miguel","Santiago","Juan","Emilio",
        "Rafael","Fernando","Ricardo","Manuel","Alejandro","Eduardo","Victor","Hector","Tomas","Cesar",
        "Julian","Nicolas","Esteban","Cristian","Alonso","Marco","Raul","Orlando","Adrian","Bruno",
        "Marcus","Dante","Vincent","Tony","Salvatore","Luca","Nico","Roman","Alex","Victor",
        "Andre","Leon","Isaac","Noah","Ethan","Zane","Kai","Miles","Jax","Rico"
    ])

    nickname = random.choice(["", "", "", "El Toro", "El Flaco", "Ghost", "Scar", "Viper"])

    return {
        "name": f"{base_name} {nickname}".strip(),
        "role": role,
        "loyalty": random.randint(40, 90),
        "personality": random.choice(["loyal","greedy","paranoid","ambitious"]),
        "style": random.choice(["calm","aggressive","cold"]),
        "assigned_city": None,

        # 🔥 NEW SYSTEM
        "level": 1,
        "xp": 0,

        "skills": {
            "combat": random.randint(1, 10),
            "business": random.randint(1, 10),
            "stealth": random.randint(1, 10),
            "loyalty": random.randint(1, 10)
        }
    }

def gain_xp(npc, amount):
    npc["xp"] += amount

    if npc["xp"] >= npc["level"] * 50:
        npc["xp"] = 0
        npc["level"] += 1

        # stat growth
        skill = random.choice(list(npc["skills"].keys()))
        npc["skills"][skill] += 1

def update_npc_memory(p, npc_name, user_input):
    if npc_name not in p["npc_memory"]:
        p["npc_memory"][npc_name] = {
            "history": [],
            "attitude": "neutral"
        }

    memory = p["npc_memory"][npc_name]

    memory["history"].append(user_input)

    if len(memory["history"]) > 5:
        memory["history"].pop(0)

    # attitude shift
    text = user_input.lower()

    if "threat" in text or "kill" in text:
        memory["attitude"] = "hostile"

    elif "respect" in text or "trust" in text:
        memory["attitude"] = "loyal"

    elif "ignore" in text:
        memory["attitude"] = "distant"

# -------------------------
# WAR ENGINE
# -------------------------

def world_war_tick(world):
    territories = world["territories"]

    for city in territories:
        t = territories[city]
        t.setdefault("defense", 0)
        t.setdefault("control", 0)
        t.setdefault("owner", None)
        t.setdefault("conflict", False)

        t["defense"] = max(0, t["defense"] - 2)

    for city, data in territories.items():

        if random.randint(1,100) < 30:
            data["conflict"] = True

        if data["conflict"]:
            data["control"] = max(0, data["control"] - random.randint(5,15))

            if data["control"] == 0:
                data["owner"] = random.choice(list(CITY_CARTELS.values()))
                data["conflict"] = False

def cartel_ai(world, p):
    territories = world["territories"]

    for cartel_name, cartel in world["cartels"].items():

        if cartel["name"] == p.get("cartel"):
            continue

        strategy = cartel.get("strategy", "balanced")

        # 🎯 pick player-owned cities only
        player_cities = [
            city for city, t in territories.items()
            if t["owner"] == p.get("cartel")
        ]

        if not player_cities:
            continue

        city = random.choice(player_cities)

        defense = territories[city].get("defense", 0)

        base_damage = random.randint(10, 30)

        # 🧠 STRATEGY MODIFIERS
        if strategy == "economic_attack":
            base_damage += 5
            p["cash"] = max(0, p["cash"] - random.randint(1000, 3000))

        elif strategy == "territory_war":
            base_damage += 10

        elif strategy == "direct_conflict":
            base_damage += 15

        elif strategy == "lay_low":
            continue  # no attack

        # 📈 adaptation scaling
        base_damage += cartel.get("adaptation", 0) // 5

        damage = max(0, base_damage - defense)

        territories[city]["control"] = max(0, territories[city]["control"] - damage)

        return cartel["name"], city, damage, strategy

    return None

def analyze_player(p, world):
    profile = {
        "wealth": p["cash"] + p["bank"],
        "heat": p["heat"],
        "territories": 0,
        "style": p.get("style"),
        "firepower": p.get("firepower", 0)
    }

    for t in world["territories"].values():
        if t["owner"] == p.get("cartel"):
            profile["territories"] += 1

    return profile

def evolve_cartels(world, p):
    profile = analyze_player(p, world)

    for cartel in world["cartels"].values():

        cartel.setdefault("name", "Unknown")
        cartel.setdefault("power", 50)
        cartel.setdefault("aggression", 50)
        cartel.setdefault("strategy", "balanced")
        cartel.setdefault("target", None)
        cartel.setdefault("adaptation", 0)
        cartel.setdefault("personality", "balanced")

        # skip player cartel
        if cartel["name"] == p.get("cartel"):
            continue

        personality = cartel.get("personality")

        if personality == "aggressive":
            cartel["strategy"] = "direct_conflict"

        elif personality == "greedy":
            cartel["strategy"] = "economic_attack"

        elif personality == "strategic":
            if profile["territories"] >= 2:
                cartel["strategy"] = "territory_war"

        elif personality == "cautious":
            if profile["heat"] > 60:
                cartel["strategy"] = "lay_low"

        # 🧠 ADAPT STRATEGY
        # 🧠 ADAPT STRATEGY (MODIFIER, not override)

        if personality == "aggressive":
            if profile["firepower"] > 30:
                cartel["strategy"] = "direct_conflict"

        elif personality == "greedy":
            if profile["wealth"] > 30000:
                cartel["strategy"] = "economic_attack"

        elif personality == "strategic":
            if profile["territories"] >= 2:
                cartel["strategy"] = "territory_war"

        elif personality == "cautious":
            if profile["heat"] > 60:
                cartel["strategy"] = "lay_low"

        # fallback if nothing triggered
        if cartel["strategy"] == "balanced":
            if profile["territories"] >= 2:
                cartel["strategy"] = "territory_war"
            elif profile["wealth"] > 50000:
                cartel["strategy"] = "economic_attack"
            elif profile["heat"] > 80:
                cartel["strategy"] = "lay_low"
            elif profile["firepower"] > 50:
                cartel["strategy"] = "direct_conflict"

        # 🎯 TARGET PLAYER
        cartel["target"] = p.get("cartel")

        # 📈 SCALE DIFFICULTY OVER TIME
        cartel["adaptation"] += 1

async def war_map_event(guild, p, world):
    territories = world["territories"]

    for city, data in territories.items():

        if data["conflict"]:
            await trigger_scene(
                guild,
                p,
                "City War",
                f"{city} is under heavy conflict."
            )

        if data["owner"] != p.get("cartel") and data["control"] == 0:
            await trigger_scene(
                guild,
                p,
                "Territory Lost",
                f"You lost control of {city}."
            )

async def cartel_attack_event(guild, p, world):
    result = cartel_ai(world, p)

    if not result:
        return

    cartel_name, city, damage, strategy = result

    await trigger_scene(
        guild,
        p,
        "RIVAL ATTACK",
        f"{cartel_name} ({strategy}) hit {city} (-{damage} control)"
    )

# =========================
# SCENE SYSTEM
# =========================

async def trigger_scene(guild, player, title, text):
    channel = discord.utils.get(guild.text_channels, name="rp")
    if not channel:
        return

    name = player.get("cartel", player["name"])

    thread = await channel.create_thread(
        name=f"{title} - {name}",
        type=discord.ChannelType.public_thread
    )

    await thread.send(f"**{name}** — {text}")

# -------------------------

async def send_news(guild, text):
    channel = discord.utils.get(guild.text_channels, name="news")
    if not channel:
        return

    timestamp = datetime.now().strftime("%H:%M")

    msg = await channel.send(f"[{timestamp}] 📰 {text}")

    # reactions for interaction
    await msg.add_reaction("⚔️")  # act
    await msg.add_reaction("👀")  # observe
    await msg.add_reaction("💰")  # exploit

    return msg

# =========================
# BASIC COMMANDS
# =========================

@bot.command()
async def start(ctx):
    data = load_data()
    uid = str(ctx.author.id)

    data[uid] = create_player()
    data[uid]["name"] = ctx.author.name

    save_data(data)

    await ctx.send("Game started.")

@bot.command()
async def buy(ctx, amount: int):
    data = load_data()
    p = data[str(ctx.author.id)]

    price = amount * random.randint(150, 300)

    if p["cash"] < price:
        await ctx.send("Not enough cash.")
        return

    p["cash"] -= price
    p["supply"] += amount

    p["heat"] += 3

    save_data(data)

    await ctx.send(f"Bought {amount} units for ${price}")

@bot.command()
async def cartel(ctx, *, name):
    data = load_data()
    uid = str(ctx.author.id)

    data[uid]["cartel"] = name

    save_data(data)

    await ctx.send(f"Cartel created: {name}")

@bot.command()
async def guide(ctx):
    embed = discord.Embed(
        title="🧠 CARTEL SIM — FULL GUIDE",
        description="Build your empire. Survive. Dominate.",
        color=0x00ff99
    )

    embed.add_field(
        name="🚀 START",
        value="""
!start → create profile  
!cartel <name> → create cartel  
!actions → view empire  
""",
        inline=False
    )

    embed.add_field(
        name="💰 MONEY / DRUG FLOW",
        value="""
!buy <amount> → buy raw supply  
!produce → turn supply into product  
!smuggle → move product (risk heat)  
!sell → sell product (gain cash + rep)  
!launder → convert cash → bank (clean money)  
""",
        inline=False
    )

    embed.add_field(
        name="🏙️ TERRITORY",
        value="""
!travel <city> → move location  
!invade <city> → attempt takeover  
!defend <lt> <city> → assign defense  
""",
        inline=False
    )

    embed.add_field(
        name="🔫 CREW / POWER",
        value="""
!hire <role> → hire crew (needs guns)  
!buyguns <amount> → increase firepower  
!connections → view hierarchy  
""",
        inline=False
    )

    embed.add_field(
        name="🏢 ASSETS",
        value="""
!warehouse → increase storage  
!lab → produce drugs  
!business <type> → passive income + laundering boost  
""",
        inline=False
    )

    embed.add_field(
        name="🧠 INTEL / CONTROL",
        value="""
!intel → scan loyalty  
!investigate <name> → deeper scan  
!interrogate <name> → force loyalty shift  
!execute <name> → eliminate lieutenant  
!replace <role> → recruit new lieutenant  
""",
        inline=False
    )

    embed.add_field(
        name="👨‍👩‍👧 LIFE / RP",
        value="""
!meet → meet partner  
!date_accept → accept relationship  
!kid → have child  

Respond in RP threads to make decisions:
fight / flee / bribe / hide
""",
        inline=False
    )

    embed.add_field(
        name="⚠️ SYSTEMS (PASSIVE)",
        value="""
• DEA raids (heat-based)  
• Cartel wars  
• Territory conflicts  
• Betrayals (low loyalty NPCs)  
• Underboss / lieutenant actions  
• Family risks  
• World events  
""",
        inline=False
    )

    embed.add_field(
        name="🏆 WIN / LOSE",
        value="""
Win → control 3+ territories + $50k bank  
Lose → lose all money + product  
!rebuild → restart  
""",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    await ctx.send(
        "**🧠 CORE LOOP**\n"
        "buy → produce → smuggle → sell → launder\n\n"

        "**💰 ECONOMY**\n"
        "!buy, !produce, !smuggle, !sell, !launder\n\n"

        "**⚔️ EXPANSION**\n"
        "!hire, !buyguns, !invade, !defend\n\n"

        "**🧠 CONTROL**\n"
        "!intel, !investigate, !interrogate, !execute, !replace\n\n"

        "**👥 NPC SYSTEM**\n"
        "NPCs have skills (combat/business/stealth)\n"
        "They level up and can betray you\n\n"

        "**🌎 WORLD SYSTEMS**\n"
        "DEA raids, cartel wars, betrayals, events\n\n"

        "**📊 VIEW**\n"
        "!actions → full empire view\n"
        "!connections → hierarchy\n\n"

        "Use !guide for full breakdown."
    )

# -------------------------

async def dea_event(guild, p, world):
    if p["dea"] > 150 and not p.get("in_prison"):

        await trigger_scene(
            guild,
            p,
            "DEA RAID",
            "Federal agents storm your operation. You are arrested."
        )

        p["in_prison"] = True
        p["sentence"] = random.randint(2, 5)

        p["cash"] = int(p["cash"] * 0.3)
        p["bank"] = int(p["bank"] * 0.5)

        p["heat"] = 0
        p["dea"] = 0

        # lose territory
        territories = world["territories"]

        for city in territories:
            if territories[city]["owner"] == p.get("cartel"):
                territories[city]["owner"] = None
                territories[city]["control"] = 0

        save_world(world)

# --------------------------

async def npc_world_actions(guild, p, world):
    territories = world["territories"]

    for lt in p["hierarchy"].get("lieutenants", []):
        name = lt["name"]
        loyalty = lt["loyalty"]
        city = lt.get("assigned_city")

        if not city or city not in territories:
            continue

        # 🔥 HIGH LOYALTY = EXPANSION
        if loyalty > 70 and random.randint(1,100) < 40:
            if p.get("firepower", 0) < len(p["crew"]):
                continue  # can't expand without weapons
            gain = random.randint(10, 25)
            territories[city]["control"] += gain

            await send_news(
                guild,
                f"{name} strengthened your control in {city} (+{gain} control)"
            )

        # ⚠️ LOW LOYALTY = DAMAGE
        elif loyalty < 30 and random.randint(1,100) < 40:
            loss = random.randint(5, 20)
            territories[city]["control"] = max(0, territories[city]["control"] - loss)

            await send_news(
                guild,
                f"{name} destabilized your operation in {city} (-{loss} control)"
            )

        # 💀 VERY LOW = BETRAYAL ACTION
        elif loyalty < 15 and random.randint(1,100) < 25:
            territories[city]["owner"] = random.choice(list(CITY_CARTELS.values()))
            territories[city]["control"] = random.randint(20, 60)

            await trigger_scene(
                guild,
                p,
                "LIEUTENANT BETRAYAL",
                f"{name} flipped control of {city} to another cartel."
            )

        gain_xp(lt, 10)

# -------------------------

async def family_risk(guild, p):

    if not p["kids"] or not p["partner"]:
        return

    if random.randint(1,100) < 20:

        await trigger_scene(
            guild,
            p,
            "Family Threat",
            "Your family is in danger due to your actions."
        )

        p["stress"] += 10

        # possible consequence
        if random.randint(1,100) < 30:
            p["cash"] = int(p["cash"] * 0.7)

# =========================
# ECONOMY SYSTEM
# =========================

def produce_cocaine(p):
    labs = p["assets"].get("lab", 0)

    if labs <= 0:
        return

    if p["supply"] <= 0:
        return  # no raw material

    used = min(p["supply"], labs * 10)
    p["supply"] -= used

    low = int(used * random.uniform(0.4, 0.6))
    pure = int(used * random.uniform(0.2, 0.4))
    high = int(used * random.uniform(0.1, 0.2))

    p["inventory"]["low"] += low
    p["inventory"]["pure"] += pure
    p["inventory"]["high"] += high

# =========================
# TERRITORY SYSTEM
# =========================

def territory_gain(p, world):
    loc = p["location"]

    territories = world["territories"]

    if loc not in territories:
        return

    gain = random.randint(5, 15)

    # lieutenant bonus (city-specific)
    for lt in p["hierarchy"].get("lieutenants", []):
        if lt.get("assigned_city") == loc:
            gain += 5

    territories[loc]["control"] += gain

    if territories[loc]["control"] >= 100:
        territories[loc]["owner"] = p.get("cartel", p["name"])


def passive_income(p, world):
    total = 0

    territories = world["territories"]

    owner_name = p.get("cartel") or p.get("name")

    for city, t in territories.items():
        if t["owner"] == owner_name:
            total += 2000

    p["bank"] += total


# =========================
# SELL SYSTEM
# =========================

def calculate_profit(p, sold_low, sold_pure, sold_high):
    loc = LOCATIONS[p["location"]]

    prices = {
        "low": 200,
        "pure": 400,
        "high": 700
    }

    total = (
        sold_low * prices["low"] +
        sold_pure * prices["pure"] +
        sold_high * prices["high"]
    )

    # location multiplier
    total = int(total * loc["profit_mult"])

    # capo bonus
    capo_bonus = len(p["hierarchy"].get("capos", [])) * 0.1
    total = int(total * (1 + capo_bonus))

    for capo in p["hierarchy"].get("capos", []):
        total += capo["skills"]["business"] * 50

    return total

# -------------------------
# TIME SYSTEM
# -------------------------

def daily_tick(p):
    if p.get("in_prison"):
        p["sentence"] -= 1

        if p["sentence"] <= 0:
            p["in_prison"] = False
            p["heat"] = 20
        return

    p["day"] += 1

    # passive heat decay
    p["heat"] = max(0, p["heat"] - 2)

    # passive income from businesses (future use)
    for biz in p["businesses"]:
        p["bank"] += biz.get("income", 0)

    # stress increase
    p["stress"] += 1

    # global world event chance
    if random.randint(1, 100) < 50:
        p["trigger_world_event"] = True

# =========================
# COMMANDS — ECONOMY
# =========================

@bot.command()
async def produce(ctx):
    data = load_data()
    world = load_world()
    p = data[str(ctx.author.id)]
    
    if p.get("in_prison"):
        daily_tick(p)
        save_data(data)
        await ctx.send("You're in prison. Time passes...")
        return
    
    ok, deficit = check_firepower(p)

    if not ok:
        p["heat"] += deficit
        p["stress"] += deficit
        await ctx.send(f"⚠️ You're under-armed by {deficit} weapons.")

    produce_cocaine(p)

    await run_hierarchy_systems(ctx.guild, p, world)
    await check_raid(ctx.guild, p)

    update_dea(p)
    await dea_event(ctx.guild, p, world)

    await family_risk(ctx.guild, p)

    escalate_war(p)
    await war_event(ctx.guild, p, world)

    update_betrayal_chain(p)
    await betrayal_progression(ctx.guild, p)

    world_war_tick(world)
    await war_map_event(ctx.guild, p, world)

    evolve_cartels(world, p)

    await cartel_attack_event(ctx.guild, p, world)

    await npc_world_actions(ctx.guild, p, world)

    daily_tick(p)

    if p.get("trigger_world_event"):
        await world_event(ctx.guild, p, world)
        p["trigger_world_event"] = False

    apply_player_identity_effects(p)

    save_data(data)
    save_world(world)

    await ctx.send("Production complete.")

@bot.command()
async def business(ctx, type):
    data = load_data()
    p = data[str(ctx.author.id)]

    cost = 10000

    if p["cash"] < cost:
        await ctx.send("Not enough money.")
        return

    biz = {
        "type": type,
        "income": random.randint(1000, 3000)
    }

    p["cash"] -= cost
    p["businesses"].append(biz)

    save_data(data)

    await ctx.send(f"Opened {type} business.")


@bot.command()
async def smuggle(ctx): 
    data = load_data()
    world = load_world()
    p = data[str(ctx.author.id)]

    if p.get("in_prison"):
        daily_tick(p)
        save_data(data)
        await ctx.send("You're in prison. Time passes...")
        return

    moved = random.randint(10, 30)

    total_stock = (
        p["inventory"]["low"] +
        p["inventory"]["pure"] +
        p["inventory"]["high"]
    )

    if total_stock <= 0:
        await ctx.send("No product.")
        return

    # remove proportionally
    remaining = moved

    for i, tier in enumerate(["low", "pure", "high"]):
        if remaining <= 0:
            break

        total = sum(p["inventory"].values())
        if total == 0:
            break

        ratio = p["inventory"][tier] / total

        if i == 2:  # last tier gets remainder
            take = remaining
        else:
            take = int(moved * ratio)

        take = min(take, p["inventory"][tier])

        p["inventory"][tier] -= take
        remaining -= take

    p["heat"] += 5

    ok, deficit = check_firepower(p)

    if not ok:
        p["heat"] += deficit
        p["stress"] += deficit
        await ctx.send(f"⚠️ You're under-armed by {deficit} weapons.")

    usage = max(1, len(p["crew"]) // 5)
    p["firepower"] = max(0, p["firepower"] - usage)

    await run_hierarchy_systems(ctx.guild, p, world)
    await check_raid(ctx.guild, p)

    update_dea(p)
    await dea_event(ctx.guild, p, world)

    await family_risk(ctx.guild, p)

    escalate_war(p)
    await war_event(ctx.guild, p, world)

    update_betrayal_chain(p)
    await betrayal_progression(ctx.guild, p)

    world_war_tick(world)
    await war_map_event(ctx.guild, p, world)

    evolve_cartels(world, p)

    await cartel_attack_event(ctx.guild, p, world)

    await npc_world_actions(ctx.guild, p, world)

    daily_tick(p)

    if p.get("trigger_world_event"):
        await world_event(ctx.guild, p, world)
        p["trigger_world_event"] = False

    apply_player_identity_effects(p)

    save_data(data)
    save_world(world)

    await ctx.send("Smuggled product.")


@bot.command()
async def sell(ctx):
    data = load_data()
    world = load_world()
    p = data[str(ctx.author.id)]

    if p.get("in_prison"):
        daily_tick(p)
        save_data(data)
        await ctx.send("You're in prison. Time passes...")
        return
    
    sold_low = min(p["inventory"]["low"], random.randint(5, 15))
    sold_pure = min(p["inventory"]["pure"], random.randint(3, 10))
    sold_high = min(p["inventory"]["high"], random.randint(1, 5))

    p["inventory"]["low"] -= sold_low
    p["inventory"]["pure"] -= sold_pure
    p["inventory"]["high"] -= sold_high

    profit = calculate_profit(p, sold_low, sold_pure, sold_high)

    p["cash"] += profit
    p["heat"] += 5

    p["reputation"] += int(profit / 1000)
    update_rank(p)

    ok, deficit = check_firepower(p)

    if not ok:
        p["heat"] += deficit
        p["stress"] += deficit
        await ctx.send(f"⚠️ You're under-armed by {deficit} weapons.")

    usage = max(1, len(p["crew"]) // 5)
    p["firepower"] = max(0, p["firepower"] - usage)

    territory_gain(p, world)
    passive_income(p, world)

    # 🔥 ADD ALL SYSTEMS HERE
    await run_hierarchy_systems(ctx.guild, p, world)
    await check_raid(ctx.guild, p)

    update_dea(p)
    await dea_event(ctx.guild, p, world)

    await family_risk(ctx.guild, p)

    escalate_war(p)
    await war_event(ctx.guild, p, world)

    update_betrayal_chain(p)
    await betrayal_progression(ctx.guild, p)

    world_war_tick(world)
    await war_map_event(ctx.guild, p, world)

    evolve_cartels(world, p)

    await cartel_attack_event(ctx.guild, p, world)

    await npc_world_actions(ctx.guild, p, world)

    daily_tick(p)

    if p.get("trigger_world_event"):
        await world_event(ctx.guild, p, world)
        p["trigger_world_event"] = False
    
    apply_player_identity_effects(p)

    if check_endgame(p, world):
        await ctx.send("You have become the dominant cartel. You win.")

    if check_collapse(p):
        await ctx.send("Your empire has collapsed. You must rebuild.")

    save_data(data)
    save_world(world)

    await ctx.send(f"Sold product for ${profit}")


@bot.command()
async def launder(ctx):
    data = load_data()
    p = data[str(ctx.author.id)]

    if p["cash"] <= 0:
        await ctx.send("No cash.")
        return

    # business boost
    boost = len(p["businesses"]) * 0.15

    success = random.uniform(0.4, 0.8) + boost
    success = min(success, 0.95)

    cleaned = int(p["cash"] * success)
    lost = p["cash"] - cleaned

    p["cash"] = 0
    p["bank"] += cleaned

    p["heat"] = max(0, p["heat"] - random.randint(3, 8))

    save_data(data)

    await ctx.send(f"Laundered ${cleaned} | Lost ${lost}")

@bot.command()
async def intel(ctx):
    data = load_data()
    p = data[str(ctx.author.id)]

    msg = "**🕵️ INTEL REPORT**\n"

    for lt in p["hierarchy"].get("lieutenants", []):
        name = lt["name"]
        loyalty = lt["loyalty"]

        # intel accuracy improves with intel_level
        noise = random.randint(-10, 10)
        skill_bonus = sum(lt["skills"]["stealth"] for lt in p["hierarchy"]["lieutenants"]) // 5
        perceived = loyalty + noise + p.get("intel_level", 0) + skill_bonus

        if perceived < 25:
            status = "💀 HIGH RISK"
        elif perceived < 50:
            status = "⚠️ Suspicious"
        else:
            status = "✅ Stable"

        msg += f"{name} — {status}\n"

    await ctx.send(msg)

@bot.command()
async def investigate(ctx, *, name):
    data = load_data()
    p = data[str(ctx.author.id)]

    for lt in p["hierarchy"].get("lieutenants", []):
        if lt["name"].lower() == name.lower():

            roll = random.randint(1,100) + p.get("intel_level", 0)

            if roll > 80:
                await ctx.send(f"{name} is secretly plotting against you.")
            elif roll > 50:
                await ctx.send(f"{name} has been acting strange.")
            else:
                await ctx.send(f"{name} appears loyal.")

            return

    await ctx.send("Not found.")

@bot.command()
async def interrogate(ctx, *, name):
    data = load_data()
    p = data[str(ctx.author.id)]

    for lt in p["hierarchy"].get("lieutenants", []):
        if lt["name"].lower() == name.lower():

            if random.randint(1,100) < 50:
                lt["loyalty"] -= 15
                await ctx.send(f"{name} cracked under pressure. Loyalty dropped.")
            else:
                lt["loyalty"] += 5
                await ctx.send(f"{name} proved loyalty under interrogation.")

            save_data(data)
            return

    await ctx.send("Not found.")

@bot.command()
async def execute(ctx, *, name):
    data = load_data()
    p = data[str(ctx.author.id)]

    for lt in p["hierarchy"].get("lieutenants", []):
        if lt["name"].lower() == name.lower():

            p["hierarchy"]["lieutenants"].remove(lt)

            p["heat"] += 10
            p["reputation"] += 5

            await ctx.send(f"{name} has been eliminated.")

            save_data(data)
            return

    await ctx.send("Not found.")

@bot.command()
async def replace(ctx, *, role):
    data = load_data()
    p = data[str(ctx.author.id)]

    new_lt = generate_npc("lieutenant")

    p["hierarchy"]["lieutenants"].append(new_lt)

    await ctx.send(f"Replaced with new lieutenant: {new_lt['name']}")

    save_data(data)

@bot.command()
async def community(ctx, amount: int):
    data = load_data()
    p = data[str(ctx.author.id)]

    if p["cash"] < amount:
        await ctx.send("Not enough cash.")
        return

    p["cash"] -= amount

    boost = amount // 1000
    p["community_support"] += boost

    await ctx.send(f"You invested in the community (+{boost} support)")

    save_data(data)

@bot.command()
async def rebuild(ctx):
    data = load_data()
    p = data[str(ctx.author.id)]

    if p["rank"] != "Collapsed":
        await ctx.send("You are not collapsed.")
        return

    p["cash"] = 2000
    p["heat"] = 10
    p["rank"] = "Street Runner"

    save_data(data)

    await ctx.send("You start again from nothing.")

# =========================
# RP EFFECT SYSTEM
# =========================

def parse_effects(text):
    effects = {
        "cash": 0,
        "heat": 0,
        "cocaine_low": 0,
        "cocaine_pure": 0,
        "cocaine_high": 0,
        "crew_add": None,
        "crew_remove": None
    }

    def get_val(key):
        if key in text:
            try:
                return int(text.split(key)[1].split()[0])
            except:
                return 0
        return 0

    effects["cash"] = get_val("CASH+") - get_val("CASH-")
    effects["heat"] = get_val("HEAT+") - get_val("HEAT-")

    effects["cocaine_low"] = get_val("LOW+") - get_val("LOW-")
    effects["cocaine_pure"] = get_val("PURE+") - get_val("PURE-")
    effects["cocaine_high"] = get_val("HIGH+") - get_val("HIGH-")

    if "CREW+" in text:
        effects["crew_add"] = text.split("CREW+")[1].split()[0]

    if "CREW-" in text:
        effects["crew_remove"] = text.split("CREW-")[1].split()[0]

    return effects


def apply_effects(p, effects):
    p["cash"] += effects["cash"]
    p["heat"] += effects["heat"]

    p["inventory"]["low"] += effects["cocaine_low"]
    p["inventory"]["pure"] += effects["cocaine_pure"]
    p["inventory"]["high"] += effects["cocaine_high"]

    if effects["crew_add"]:
        p["crew"].append(effects["crew_add"])

    if effects["crew_remove"] and effects["crew_remove"] in p["crew"]:
        p["crew"].remove(effects["crew_remove"])

def check_endgame(p, world):
    territories = world["territories"]

    owned = sum(1 for t in territories.values() if t["owner"] == p.get("cartel"))

    if owned >= 3 and p["bank"] > 50000:
        return True

    return False


# =========================
# AI RESPONSE SYSTEM
# =========================

def build_context(p):
    context = f"""
        You are a dynamic crime world simulation.

        Tone rules:
        - Cartel members: cold, direct, street-smart, dangerous
        - Government/DEA: formal, strategic, authoritative
        - Partner/family: emotional, personal, human
        - Kids: innocent, simple tone

        Tone should adapt to player style:
        - aggressive → more violent, confrontational
        - diplomatic → negotiation, calm tone
        - loyal → family, respect, emotion

        Player cartel: {p.get("cartel")}
        Location: {p["location"]}
        Heat: {p["heat"]}
        Cash: {p["cash"]}
        Player style: {p.get("style")}

        Respond in immersive narrative dialogue.

        When consequences happen, include:
        [EFFECT: CASH+X HEAT+X LOW+X PURE+X HIGH+X CREW+type CREW-type]
        """

    # hierarchy context
    context += f"\nPlayer rank: {p['rank']} | Reputation: {p['reputation']} | Stress: {p['stress']}\n"

    ub = p["hierarchy"].get("underboss")
    if ub:
        context += f"\nUnderboss: {ub['name']} (loyalty {ub['loyalty']})"

    for lt in p["hierarchy"].get("lieutenants", []):
        if lt.get("assigned_city"):
            context += f"\nLieutenant: {lt['name']} controls {lt['assigned_city']}"

    if p["partner"]:
        context += f"\nPartner: {p['partner']['name']}"

    if p.get("memory"):
        context += "\nRecent history:\n"
        for m in p["memory"][-3:]:
            context += f"- {m['input']} → {m['result']}\n"

    # NPC memory context
    if p.get("npc_memory"):
        context += "\nNPC relationships:\n"
        for name, data in p["npc_memory"].items():
            context += f"- {name}: {data['attitude']} | recent: {data['history'][-2:] if data['history'] else []}\n"

    # 👇 THIS LINE GOES OUTSIDE THE LOOP
    context += "\nIn raids, player can fight, flee, hide, or bribe.\n"

    return context


async def generate_ai_response(p, user_input):
    context = build_context(p)

    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": user_input}
        ]
    )

    return response.choices[0].message.content

async def resolve_raid_action(guild, p, action):
    crew_power = (
        len(p["crew"]) * 3 +
        p.get("firepower", 0) * 5
    )

    for lt in p["hierarchy"].get("lieutenants", []):
        crew_power += lt["skills"]["combat"] * 2

    heat_factor = p["heat"]

    if action == "fight":
        ok, deficit = check_firepower(p)

        # ALWAYS define enemy power
        enemy_power = (
            heat_factor +
            random.randint(20, 50) +
            p["reputation"] * 0.5 +
            p["war_stage"] * 10
        )

        if not ok:
            await trigger_scene(
                guild,
                p,
                "OUTGUNNED",
                f"Your crew lacks {deficit} weapons. You're severely outgunned."
            )
            enemy_power += 20  # penalty

        # THEN consume weapons AFTER check
        usage = max(1, len(p["crew"]) // 5)
        p["firepower"] = max(0, p["firepower"] - usage)

        if crew_power > enemy_power:
            await trigger_scene(guild, p, "Fight Back", "You fought them off successfully.")
        else:
            loss = random.randint(5000, 10000)
            p["cash"] = max(0, p["cash"] - loss)

            # 💀 MULTI CASUALTY SYSTEM
            diff = enemy_power - crew_power
            deaths = min(len(p["crew"]), max(1, diff // 10))

            dead_list = []

            for _ in range(deaths):
                if not p["crew"]:
                    break
                dead = random.choice(p["crew"])
                p["crew"].remove(dead)
                dead_list.append(dead)

            # 🔫 firepower loss matches deaths
            weapon_loss = random.randint(len(dead_list), len(dead_list) * 2)
            p["firepower"] = max(0, p["firepower"] - weapon_loss)

            if dead_list:
                await trigger_scene(
                    guild,
                    p,
                    "CASUALTIES",
                    f"You lost {len(dead_list)} crew members: {', '.join(dead_list)}"
                )

    elif action == "flee":
        p["heat"] += 5
        await trigger_scene(guild, p, "Escape", "You escaped, but left things behind.")

    elif action == "bribe":
        cost = random.randint(3000, 8000)
        if p["cash"] >= cost:
            p["cash"] -= cost
            await trigger_scene(guild, p, "Bribe Success", "They backed off.")
        else:
            await trigger_scene(guild, p, "Bribe Failed", "You didn’t have enough.")

    elif action == "hide":
        saved = random.randint(5, 15)
        await trigger_scene(guild, p, "Hidden", f"You saved {saved} product.")


# =========================
# MESSAGE HANDLER (RP CORE)
# =========================

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if reaction.message.channel.name != "news":
        return

    data = load_data()
    uid = str(user.id)

    if uid not in data:
        return

    p = data[uid]

    if str(reaction.emoji) == "💰":
        gain = random.randint(1000, 4000)
        p["cash"] += gain

        await reaction.message.channel.send(f"{user.name} exploited the situation (+${gain})")

    elif str(reaction.emoji) == "⚔️":
        p["heat"] += 5
        await reaction.message.channel.send(f"{user.name} got involved in violence (+heat)")

    elif str(reaction.emoji) == "👀":
        p["reputation"] += 2
        await reaction.message.channel.send(f"{user.name} gained intel (+rep)")

    save_data(data)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # allow commands
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # only run in threads (RP scenes)
    if not isinstance(message.channel, discord.Thread):
        return

    data = load_data()
    uid = str(message.author.id)

    if uid not in data:
        return

    p = data[uid]

    if p["partner"]:
        update_npc_memory(p, p["partner"]["name"], message.content)

    # generate AI response
    if len(message.content.split()) > 3:
        reply = await generate_ai_response(p, message.content)
    else:
        reply = random.choice([
            "He nods.",
            "They watch you carefully.",
            "No response."
        ])

    # detect active NPC (simple version: underboss first)
    ub = p["hierarchy"].get("underboss")

    if ub:
        update_npc_memory(p, ub["name"], message.content)

    update_memory(p, message.content, reply)

    if "fight" in message.content.lower():
        await resolve_raid_action(message.guild, p, "fight")

    elif "flee" in message.content.lower():
        await resolve_raid_action(message.guild, p, "flee")

    elif "bribe" in message.content.lower():
        await resolve_raid_action(message.guild, p, "bribe")

    elif "hide" in message.content.lower():
        await resolve_raid_action(message.guild, p, "hide")

    # apply effects
    effects = parse_effects(reply)
    apply_effects(p, effects)

    # save
    save_data(data)

    # send response
    await message.channel.send(reply)

# =========================
# HIERARCHY SYSTEM
# =========================

def update_loyalty(p):
    def adjust(npc):
        if not npc:
            return

        name = npc["name"]
        base_change = random.randint(-2, 2)

        # 🧠 memory influence
        mem = p["npc_memory"].get(name)

        if mem:
            attitude = mem["attitude"]

            if attitude == "hostile":
                base_change -= 3

            elif attitude == "loyal":
                base_change += 3

            elif attitude == "distant":
                base_change -= 1

        npc["loyalty"] += base_change
        npc["loyalty"] = max(0, min(100, npc["loyalty"]))

    h = p["hierarchy"]

    adjust(h.get("underboss"))

    for lt in h.get("lieutenants", []):
        adjust(lt)

    for capo in h.get("capos", []):
        adjust(capo)


def check_collapse(p):

    if p["cash"] <= 0 and p["bank"] <= 0 and p["inventory"]["low"] == 0 and p["inventory"]["pure"] == 0 and p["inventory"]["high"] == 0:
        p["rank"] = "Collapsed"
        return True

    return False

# =========================
# UNDERBOSS AI
# =========================

async def underboss_ai(guild, p):
    if PAUSED:
        return

    ub = p["hierarchy"].get("underboss")
    if not ub:
        return

    roll = random.randint(1, 100)
    name = ub["name"]
    loyalty = ub["loyalty"]

    # 💰 good move
    if roll < 25 and loyalty > 60:
        gain = random.randint(2000, 5000)
        p["cash"] += gain

        await trigger_scene(
            guild, p,
            "Underboss Deal",
            f"{name} handled a deal behind the scenes (+${gain})."
        )

    # ⚠️ warning
    elif roll < 50:
        await trigger_scene(
            guild, p,
            "Warning",
            f"{name} warns you about possible danger."
        )

    # ❌ bad move (low loyalty)
    elif roll < 70 and loyalty < 40:
        loss = random.randint(2000, 6000)
        p["cash"] = max(0, p["cash"] - loss)

        await trigger_scene(
            guild, p,
            "Mistake",
            f"{name} made a bad decision costing you ${loss}."
        )

    gain_xp(ub, 15)


# =========================
# LIEUTENANT CONTROL SYSTEM
# =========================

def lieutenant_bonus(p):
    loc = p["location"]
    bonus = 0

    for lt in p["hierarchy"].get("lieutenants", []):
        if lt.get("assigned_city") == loc:
            bonus += 5

    return bonus

def promote_npc(p, name):
    for lt in p["hierarchy"]["lieutenants"]:
        if lt["name"].lower() == name.lower():

            # move to capo
            p["hierarchy"]["lieutenants"].remove(lt)
            p["hierarchy"]["capos"].append(lt)

            lt["role"] = "capo"
            return f"{name} promoted to Capo."

    return "NPC not found."


# =========================
# LIEUTENANT DISOBEDIENCE
# =========================

async def lieutenant_ai(guild, p, world):
    if PAUSED:
        return

    territories = world["territories"]

    for lt in p["hierarchy"].get("lieutenants", []):
        loyalty = lt["loyalty"]
        name = lt["name"]

        # 💀 DEFENSE SABOTAGE
        if lt.get("assigned_city") and loyalty < 25 and random.randint(1,100) < 40:
            city = lt["assigned_city"]

            if city in territories:
                territories[city]["defense"] = max(
                    0,
                    territories[city].get("defense", 0) - 10
                )

                await trigger_scene(
                    guild,
                    p,
                    "INSIDE JOB",
                    f"{name} secretly weakened defenses in {city} (-10 defense)"
                )
                
        # small gain
        elif loyalty > 70 and random.randint(1,100) < 25:

            gain = random.randint(1000, 3000)
            p["cash"] += gain

            await trigger_scene(
                guild,
                p,
                "Lieutenant Success",
                f"{name} successfully expanded operations (+${gain})."
            )


# =========================
# CAPO EFFECT (PASSIVE)
# =========================

def capo_bonus(p):
    return len(p["hierarchy"].get("capos", [])) * 0.1


# =========================
# INTEGRATION HOOK (IMPORTANT)
# =========================

async def run_hierarchy_systems(guild, p, world):
    update_loyalty(p)
    await underboss_ai(guild, p)
    await lieutenant_ai(guild, p, world)

# =========================
# STORY SYSTEMS
# =========================

async def world_event(guild, p, world):
    territories = world["territories"]

    roll = random.randint(1, 100)

    # DEA activity
    if roll < 20:
        await send_news(guild, "DEA activity increasing across multiple cities.")

    # cartel war
    elif roll < 40:
        city = random.choice(list(territories.keys()))
        territories[city]["conflict"] = True

        await send_news(guild, f"Violence escalates in {city}. Control is weakening.")

        save_world(world)

    # shipment seizure
    elif roll < 60:
        loss = random.randint(5, 15)
        p["inventory"]["low"] = max(0, p["inventory"]["low"] - loss)

        await send_news(guild, f"A shipment was intercepted. ({loss} lost)")

    # random npc move
    elif roll < 80:
        await send_news(guild, "A high-ranking member has been spotted moving operations.")

    # calm period
    else:
        await send_news(guild, "The streets are quiet… for now.")

def update_rank(p):
    rep = p["reputation"]

    if rep >= 500:
        p["rank"] = "Kingpin"
    elif rep >= 300:
        p["rank"] = "Cartel Boss"
    elif rep >= 150:
        p["rank"] = "Plaza Boss"
    elif rep >= 50:
        p["rank"] = "Crew Leader"
    else:
        p["rank"] = "Street Runner"

def update_betrayal_chain(p):
    ub = p["hierarchy"].get("underboss")

    if not ub:
        return

    loyalty = ub["loyalty"]

    if loyalty < 40:
        p["npc_relations"]["suspicion"] = True

    if loyalty < 30:
        p["npc_relations"]["warning"] = True

    if loyalty < 20:
        p["npc_relations"]["betrayal_ready"] = True


async def betrayal_progression(guild, p):
    ub = p["hierarchy"].get("underboss")
    if not ub:
        return

    name = ub["name"]
    flags = p["npc_relations"]

    # ⚠️ suspicion
    if flags.get("suspicion"):
        await trigger_scene(guild, p, "Suspicion", f"{name} has been acting different lately.")

    # ⚠️ warning
    if flags.get("warning"):
        await trigger_scene(guild, p, "Warning", f"{name} is making quiet moves behind your back.")

    # 💀 betrayal (REAL DAMAGE)
    if flags.get("betrayal_ready"):

        stolen = random.randint(5000, 15000)
        p["cash"] = max(0, p["cash"] - stolen)

        # crew loss
        if p["crew"]:
            removed = random.choice(p["crew"])
            p["crew"].remove(removed)
        else:
            removed = None

        # territory loss
        world = load_world()
        territories = world["territories"]

        for city, t in territories.items():
            if t["owner"] == p.get("cartel"):
                t["control"] = max(0, t["control"] - random.randint(20, 40))

        await trigger_scene(
            guild,
            p,
            "BETRAYAL",
            f"{name} betrayed you. Stole ${stolen} and destabilized your operation."
        )

        # remove underboss
        p["hierarchy"]["underboss"] = None

        # reset flags
        p["npc_relations"].clear()

        save_world(world)

def update_dea(p):
    reduction = p.get("community_support", 0) * 0.5
    gain = int(p["heat"] * 0.2)

    gain = max(0, gain - reduction)

    p["dea"] += gain
                
def escalate_war(p):
    if random.randint(1,100) < 20:
        p["war_stage"] += 1

async def war_event(guild, p):
    if p["war_stage"] >= 3:
        await trigger_scene(guild, p, "War", "Your cartel is under attack.")

async def check_raid(guild, p):
    if PAUSED:
        return
    
    if p["heat"] < 30:
        chance = 5
    elif p["heat"] < 60:
        chance = 15
    elif p["heat"] < 100:
        chance = 30
    else:
        chance = 50

    # apply community AFTER
    chance -= p.get("community_support", 0)
    chance = max(1, chance)

    if random.randint(1, 100) < chance:

        loss = random.randint(3000, 8000)
        p["cash"] = max(0, p["cash"] - loss)

        await trigger_scene(
            guild,
            p,
            "Raid",
            "Police are breaking in. Fight, flee, hide product, or bribe."
        )

def apply_player_identity_effects(p):
    style = p.get("style")

    if style == "aggressive":
        p["heat"] += 2

    elif style == "diplomatic":
        p["heat"] = max(0, p["heat"] - 2)

    elif style == "loyal":
        # boost crew loyalty slightly
        for npc in p["hierarchy"].get("lieutenants", []):
            npc["loyalty"] = min(100, npc["loyalty"] + 1)

def check_firepower(p):
    crew_count = len(p["crew"])
    firepower = p.get("firepower", 0)

    if firepower < crew_count:
        return False, crew_count - firepower

    return True, 0

# =========================
# BANK SYSTEM
# =========================

@bot.command()
async def promote(ctx, *, name):
    data = load_data()
    p = data[str(ctx.author.id)]

    msg = promote_npc(p, name)

    save_data(data)
    await ctx.send(msg)

@bot.command()
async def deposit(ctx, amount: int):
    data = load_data()
    p = data[str(ctx.author.id)]

    if p["cash"] < amount:
        await ctx.send("Not enough cash.")
        return

    p["cash"] -= amount
    p["bank"] += amount

    save_data(data)
    await ctx.send(f"Deposited ${amount}")


@bot.command()
async def withdraw(ctx, amount: int):
    data = load_data()
    p = data[str(ctx.author.id)]

    if p["bank"] < amount:
        await ctx.send("Not enough bank.")
        return

    p["bank"] -= amount
    p["cash"] += amount

    save_data(data)
    await ctx.send(f"Withdrew ${amount}")


# =========================
# RELATIONSHIP SYSTEM
# =========================

def generate_partner():
    return {
        "name": random.choice(["Sofia","Isabella","Camila","Valeria"]),
        "loyalty": random.randint(50, 90),
        "personality": random.choice(["loyal","flirty","cold","ambitious"])
    }


@bot.command()
async def meet(ctx):
    data = load_data()
    p = data[str(ctx.author.id)]

    candidate = generate_partner()
    p["npc_relations"]["candidate"] = candidate

    save_data(data)

    await ctx.send(f"You met {candidate['name']} ({candidate['personality']})")


@bot.command()
async def date_accept(ctx):
    data = load_data()
    p = data[str(ctx.author.id)]

    candidate = p["npc_relations"].get("candidate")

    if not candidate:
        await ctx.send("No one to accept.")
        return

    p["partner"] = candidate
    del p["npc_relations"]["candidate"]

    save_data(data)

    await ctx.send(f"You are now with {candidate['name']}")


@bot.command()
async def kid(ctx):
    data = load_data()
    p = data[str(ctx.author.id)]

    if not p["partner"]:
        await ctx.send("No partner.")
        return

    if random.randint(1,100) < 50:
        child = {"name": random.choice(["Mateo","Luna","Diego","Sofia"])}
        p["kids"].append(child)

        await ctx.send(f"You had a child: {child['name']}")
    else:
        await ctx.send("No child this time.")

    save_data(data)


# =========================
# CREW / ASSETS
# =========================

@bot.command()
async def hire(ctx, role):
    data = load_data()
    p = data[str(ctx.author.id)]

    if p.get("firepower", 0) <= len(p["crew"]):
        await ctx.send("You need more weapons before hiring more crew.")
        return

    p["crew"].append(role)

    save_data(data)

    await ctx.send(f"Hired {role}")

@bot.command()
async def buyguns(ctx, amount: int):
    data = load_data()
    p = data[str(ctx.author.id)]

    cost = amount * random.randint(800, 1500)

    if p["cash"] < cost:
        await ctx.send("Not enough cash.")
        return

    p["cash"] -= cost
    p["firepower"] += amount

    save_data(data)

    await ctx.send(f"Bought {amount} weapons (+{amount} firepower)")


@bot.command()
async def warehouse(ctx):
    data = load_data()
    p = data[str(ctx.author.id)]

    cost = 5000

    if p["cash"] < cost:
        await ctx.send("Not enough money.")
        return

    p["cash"] -= cost
    p["assets"]["warehouse"] += 1

    save_data(data)

    await ctx.send("Warehouse built.")


@bot.command()
async def lab(ctx):
    data = load_data()
    p = data[str(ctx.author.id)]

    cost = 8000

    if p["cash"] < cost:
        await ctx.send("Not enough money.")
        return

    p["cash"] -= cost
    p["assets"]["lab"] += 1

    save_data(data)

    await ctx.send("Lab built.")

@bot.command()
async def invade(ctx, *, city):
    data = load_data()
    world = load_world()

    p = data[str(ctx.author.id)]
    territories = world["territories"]

    if city not in territories:
        await ctx.send("Invalid city.")
        return

    strength = (
        len(p["crew"]) * 4 +
        p.get("firepower", 0) * 5 +
        p["reputation"]
    )

    owner = territories[city]["owner"]

    base_defense = random.randint(20, 40)

    if owner:
        base_defense += 30  # defended territory bonus

    defense = base_defense

    if strength > defense:
        owner_name = p.get("cartel") or p.get("name")

        territories[city]["owner"] = owner_name
        territories[city]["control"] = 100

        await trigger_scene(ctx.guild, p, "TAKEOVER", f"You seized control of {city}.")
    else:
        loss = random.randint(2000, 6000)
        p["cash"] = max(0, p["cash"] - loss)

        await trigger_scene(ctx.guild, p, "FAILED INVASION", f"You failed to take {city}. Lost ${loss}.")

    save_data(data)
    save_world(world)


# =========================
# TRAVEL SYSTEM
# =========================

@bot.command()
async def travel(ctx, *, city):
    data = load_data()
    p = data[str(ctx.author.id)]

    if city not in LOCATIONS:
        await ctx.send("Invalid city.")
        return

    p["location"] = city

    save_data(data)

    await ctx.send(f"Traveled to {city}")


@bot.command()
async def defend(ctx, lieutenant_name, *, city):
    data = load_data()
    world = load_world()

    p = data[str(ctx.author.id)]
    territories = world["territories"]

    if city not in territories:
        await ctx.send("Invalid city.")
        return

    # find lieutenant
    lt = None
    for l in p["hierarchy"].get("lieutenants", []):
        if l["name"].lower() == lieutenant_name.lower():
            lt = l
            break

    if not lt:
        await ctx.send("Lieutenant not found.")
        return

    lt["assigned_city"] = city
    territories[city]["defense"] += int(lt["loyalty"] / 3)

    save_data(data)
    save_world(world)

    await ctx.send(f"{lt['name']} is now defending {city}.")


# =========================
# CONNECTIONS SYSTEM
# =========================

@bot.command()
async def connections(ctx):
    p = load_data()[str(ctx.author.id)]

    msg = f"Cartel: {p.get('cartel')}\n"

    if p["hierarchy"]["underboss"]:
        msg += f"Underboss: {p['hierarchy']['underboss']['name']}\n"

    msg += f"Lieutenants: {len(p['hierarchy']['lieutenants'])}\n"
    if p["partner"]:
        msg += f"Partner: {p['partner']['name']}\n"
    else:
        msg += "Partner: None\n"
    msg += f"Kids: {len(p['kids'])}"

    await ctx.send(msg)


# =========================
# MAIN ACTION PANEL
# =========================

@bot.command()
async def actions(ctx):
    data = load_data()
    world = load_world()
    p = data[str(ctx.author.id)]

    world_war_tick(world)
    await war_map_event(ctx.guild, p, world)

    update_betrayal_chain(p)
    await betrayal_progression(ctx.guild, p)

    save_data(data)

    territories = world["territories"]

    embed = discord.Embed(title="Your Empire")

    embed.add_field(name="Cash", value=p["cash"])
    embed.add_field(name="Bank", value=p["bank"])
    embed.add_field(name="Heat", value=p["heat"])
    embed.add_field(name="Location", value=p["location"])
    embed.add_field(name="Firepower", value=p.get("firepower", 0))
    embed.add_field(
        name="Defense",
        value="\n".join(
            f"{city}: {t.get('defense', 0)}"
            for city, t in territories.items()
        ),
        inline=False
    )

    embed.add_field(
        name="Cocaine",
        value=f"L:{p['inventory']['low']} P:{p['inventory']['pure']} H:{p['inventory']['high']}",
        inline=False
    )

    embed.add_field(
        name="Territories",
        value=sum(1 for t in territories.values() if t["owner"] == p.get("cartel")),
        inline=False
    )

    await ctx.send(embed=embed)

@tasks.loop(seconds=60)
async def passive_world_loop():
    data = load_data()
    world = load_world()
    sanitize_world(world)

    for uid, p in data.items():
        p = ensure_player(p)
        data[uid] = p

        # skip prisoners
        if p.get("in_prison"):
            daily_tick(p)
            continue

        # world systems
        world_war_tick(world)
        if random.randint(1,100) < 30:
            territory_gain(p, world)

        if random.randint(1,100) < 50:
            passive_income(p, world)

        update_dea(p)

        # NPC systems (no guild here, so no scenes)
        update_loyalty(p)

        # firepower decay (see weapons system below)
        crew_count = len(p["crew"])
        firepower = p.get("firepower", 0)

        if firepower > crew_count:
            excess = firepower - crew_count

            p["firepower"] -= min(excess, 2)

            upkeep = excess * 100
            p["cash"] = max(0, p["cash"] - upkeep)

        # 🔥 ALWAYS EVOLVE (outside condition)
        evolve_cartels(world, p)

    save_data(data)
    save_world(world)

# =========================
# READY
# =========================

@bot.event
async def on_ready():
    print("Bot ready.")
    passive_world_loop.start()

bot.run(TOKEN)