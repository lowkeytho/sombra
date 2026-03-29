# =========================
# IMPORTS
# =========================
import discord
from discord.ext import commands, tasks
import json, os, random
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import time
import asyncio

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

MALE_NAMES = [
    "Javier","Luis","Mateo","Carlos","Diego","Andres","Miguel","Santiago",
    "Juan","Emilio","Rafael","Fernando","Ricardo","Manuel","Alejandro"
]

FEMALE_NAMES = [
    "Sofia","Isabella","Camila","Valeria","Lucia","Daniela","Mariana",
    "Gabriela","Valentina","Ana","Paula","Carolina","Elena"
]

DEA_FIRST = ["James","Robert","Michael","David","Daniel","Chris","Anthony"]
DEA_LAST = ["Cruz","Miller","Hale","Turner","Reyes","Cole","Vargas"]

PRISON_GANGS = ["La Raza", "Black Bloc", "Iron Syndicate", "Ghosts"]

# =========================
# DATA HELPERS
# =========================

def load_data():
    try:
        if not os.path.exists(DATA_FILE):
            return {}
        return json.load(open(DATA_FILE))
    except:
        return {}

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

            "dea_agents": [
                {
                    "name": f"{random.choice(DEA_FIRST)} {random.choice(DEA_LAST)}",
                    "skill": random.randint(60, 90),

                    "style": random.choice(["aggressive", "patient", "corrupt"]),
                    "mode": random.choice(["surveillance", "interdiction", "takedown"]),

                    "region": random.choice(list(LOCATIONS.keys())),

                    "focus": None,
                    "target_route": None,

                    "heat_target": random.randint(30, 80),

                    "knowledge": 0,
                    "informants": [],

                    "tenure": random.randint(3, 6)
                }
                for _ in range(3)
            ],

            "media": {
                "journalists": [
                    {
                        "name": "Laura Mendes",
                        "style": "investigative",
                        "alive": True,
                        "focus": None,  # player id or cartel name
                        "credibility": random.randint(50, 90)
                    },
                    {
                        "name": "Victor Hale",
                        "style": "sensational",
                        "alive": True,
                        "focus": None,
                        "credibility": random.randint(40, 80)
                    }
                ]
            },

            "economy": {
                city: {
                    "demand": random.randint(60, 120),
                    "saturation": random.randint(0, 30)
                }
                for city in LOCATIONS
            },

            "president": {
                "name": random.choice(["Anderson","Rivera","Coleman","Vargas"]),
                "style": random.choice(["corrupt","strict","balanced"]),
                "term": 4
            },
            
            "bosses": {
                city: {
                    "name": f"Boss of {city}",
                    "power": random.randint(50,100),
                    "loyalty": random.randint(30,80),
                    "personality": random.choice(["ruthless","business","paranoid"]),
                    "lieutenants": [
                        {
                            "name": random.choice(MALE_NAMES),
                            "power": random.randint(30, 70),
                            "loyalty": random.randint(40, 90)
                        }
                        for _ in range(2)
                    ],
                    "family": {
                        "has_family": random.choice([True, False]),

                        "partner": {
                            "name": random.choice(FEMALE_NAMES),
                            "loyalty": random.randint(40, 90)
                        } if random.choice([True, False]) else None,

                        "kids": [
                            {
                                "name": random.choice(MALE_NAMES + FEMALE_NAMES),
                                "age": random.randint(3, 16)
                            }
                            for _ in range(random.randint(0, 2))
                        ],

                        "vulnerability": random.randint(20, 80)
                    }
                }
                for city in LOCATIONS
            },

            "market": {
                "low": random.randint(150, 250),
                "pure": random.randint(300, 500),
                "high": random.randint(600, 900)
            },

            "relations": {},

            "territories": {
                city: {
                    "owner": None,
                    "control": 0,
                    "conflict": False,
                    "defense": 0,
                    "resistance": random.randint(10, 40)
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

        "identity": "balanced",  # aggressive / stealth / business / balanced

        "cash": 5000,
        "bank": 10000,
        "heat": 10,
        "dea": 0,

        "corruption": 0,

        "trial": None,

        "pressure": 0,

        "xp": 0,
        "level": 1,

        "routes": {},  # city → active route

        "lifestyle": "basic",  # basic / luxury / kingpin

        "location": "Medellin",
        "day": 1,

        "trigger_world_event": False,

        "in_prison": False, 
        "charges": 0,
        "lawyer_level": 0,
        "sentence": 0,

        "prison": {
            "gang": None,
            "respect": 0,
            "heat_inside": 0
        },

        "supply": 0,

        "war_phase": "calm",

        "community_support": 0,   # reduces informants / DEA pressure
        "intel_level": 0,         # improves detection accuracy

        "reputation": 0,
        "rank": "Street Runner",
        
        "npc_memory": {},

        "max_storage": 100,
        "deals": {},
        "contracts": [],

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

        "vehicles": {
            "cars": 0,
            "planes": 0
        },

        "weapons": {
            "pistols": 0,
            "rifles": 0,
            "military": 0
        },

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

    if "memory" not in p:
        p["memory"] = []

    if p.get("cash", 0) == 0:
        p["cash"] = 5000

    if p.get("bank", 0) == 0:
        p["bank"] = 10000

    if "max_storage" not in p:
        p["max_storage"] = 100

    if "deals" not in p:
        p["deals"] = {}

    if "contracts" not in p:
        p["contracts"] = []

    for key, value in default.items():
        if key not in p:
            p[key] = value

    return p

def reduce_firepower(p, amount):
    for tier in ["military", "rifles", "pistols"]:
        if amount <= 0:
            break
        have = p["weapons"].get(tier, 0)
        take = min(have, amount)
        p["weapons"][tier] -= take
        amount -= take

def update_war_phase(p, world):
    territories = world["territories"]

    owned = sum(1 for t in territories.values() if t["owner"] == p.get("cartel"))

    if owned >= 3:
        p["war_phase"] = "war"
    elif p["war_stage"] >= 3:
        p["war_phase"] = "conflict"
    elif p["heat"] > 60:
        p["war_phase"] = "tension"
    else:
        p["war_phase"] = "calm"

def cartel_wipe_attempt(p, world):
    territories = world["territories"]

    # trigger condition
    if p["bank"] < 40000 or p["war_stage"] < 3:
        return

    if random.randint(1,100) > 15:
        return

    # 💀 WIPE EVENT
    loss = random.randint(10000, 25000)
    p["cash"] = max(0, p["cash"] - loss)

    # hit multiple territories
    owned = [
        city for city, t in territories.items()
        if t["owner"] == p.get("cartel")
    ]

    for city in random.sample(owned, min(len(owned), 2)):
        territories[city]["control"] = max(
            0,
            territories[city]["control"] - random.randint(30, 70)
        )

    # crew loss
    if p["crew"]:
        removed = random.sample(p["crew"], min(len(p["crew"]), 2))
        for r in removed:
            p["crew"].remove(r)

def check_pressure_event(p):
    if p.get("pressure", 0) < 30:
        return None

    roll = random.randint(1, 100)

    if roll < 40:
        return "raid"
    elif roll < 70:
        return "cartel_attack"
    elif roll < 90:
        return "betrayal"
    else:
        return "wipe"

def update_dea_agents(world, p):
    agents = world.get("dea_agents", [])

    for i, agent in enumerate(agents):

        agent["tenure"] -= 1
        agent["knowledge"] += random.randint(1, 5)
        agent["knowledge"] = min(100, agent["knowledge"])

        update_case_stage(agent)

        case = agent.setdefault("case", {
            "routes": {},
            "crew": {},
            "evidence": 0
        })

        # ☎️ PHONE INTERCEPTION SYSTEM
        if random.randint(1,100) < 20:

            if p.get("routes"):
                route = random.choice(list(p["routes"].keys()))

                # store intercept logs
                agent.setdefault("intercepts", []).append({
                    "route": route,
                    "value": random.randint(2,6)
                })

                # build case quietly
                case["routes"][route] = case["routes"].get(route, 0) + 3
                case["evidence"] += 2

        # 🕵️ infiltration attempt
        if random.randint(1,100) < 10:

            undercover = generate_npc("associate")
            undercover["is_undercover"] = True
            undercover["loyalty"] = 80  # appears loyal

            p["crew"].append(undercover)

        specialty = agent.get("specialty")

        # 🎯 ROUTE SPECIALIST
        if specialty == "routes":
            for route in p.get("routes", {}):
                if random.randint(1,100) < 60:
                    case["routes"][route] = case["routes"].get(route, 0) + random.randint(2,6)

        # 👥 CREW SPECIALIST
        elif specialty == "crew":
            for npc in p.get("crew", []):
                if random.randint(1,100) < 50:
                    name = npc["name"]
                    case["crew"][name] = case["crew"].get(name, 0) + random.randint(2,5)

        # 💰 FINANCIAL INVESTIGATOR
        elif specialty == "finance":
            if random.randint(1,100) < 50:
                case["evidence"] += random.randint(3,8)

        # 🔥 evidence grows from knowledge
        case["evidence"] = min(150, case["evidence"])

        # 🎯 mark high-value targets
        for crew_name, val in case["crew"].items():
            if val > 10:
                agent["focus"] = crew_name
                break

        # specialization bonus
        if specialty == "finance":
            case["evidence"] += 2

        # 🤝 SHARE INTEL
        for other in world.get("dea_agents", []):
            if other is agent:
                continue

            if random.randint(1,100) < 30:

                other_case = other.setdefault("case", {
                    "routes": {},
                    "crew": {},
                    "evidence": 0
                })

                # merge strongest intel
                for r, val in case["routes"].items():
                    other_case["routes"][r] = max(
                        other_case["routes"].get(r, 0),
                        val - 1  # slight decay when sharing
                    )

                for c, val in case["crew"].items():
                    other_case["crew"][c] = max(
                        other_case["crew"].get(c, 0),
                        val - 1
                    )

                other_case["evidence"] = max(
                    other_case["evidence"],
                    case["evidence"] - 1
                )

        if agent["tenure"] <= 0:
            agents[i] = generate_dea_agent()

        wiretap = agent.get("wiretap", {})

        # 🎧 START WIRETAP
        if not wiretap.get("active") and random.randint(1,100) < 20:
            if p.get("routes"):
                target = random.choice(list(p["routes"].keys()))

                wiretap["active"] = True
                wiretap["target"] = target
                wiretap["progress"] = 0

        # 📡 BUILD WIRETAP
        if wiretap.get("active"):

            # 🔥 ESCALATION if ignored
            target = wiretap.get("target")

            if target and wiretap["progress"] > 15:
                case["routes"][target] = case["routes"].get(target, 0) + 5

            wiretap["progress"] += agent["skill"] // 10

            # 🎯 success
            if wiretap["progress"] > 25:

                target = wiretap["target"]

                case["routes"][target] = case["routes"].get(target, 0) + 15
                case["evidence"] += 10

                # reset
                wiretap["active"] = False
                wiretap["target"] = None
                wiretap["progress"] = 0

def generate_case_news(agent, p):
    agent.get("case", {}).get("stage")

    if stage == "monitoring":
        return "Authorities are quietly observing cartel activity."

    elif stage == "investigation":
        return "Federal agents have opened an investigation into cartel operations."

    elif stage == "target":
        return "A cartel leader has been identified as a priority target."

    elif stage == "indictment":
        return "Federal prosecutors are preparing charges against a cartel figure."

    elif stage == "trial":
        return "A major cartel trial is underway."

    return None

def detect_wiretap(p, world):
    alerts = []

    intel = p.get("intel_level", 0)

    for agent in world.get("dea_agents", []):
        wiretap = agent.get("wiretap", {})

        if not wiretap.get("active"):
            continue

        target = wiretap.get("target")
        progress = wiretap.get("progress", 0)

        # 🎯 detection chance scales with:
        # - your intel
        # - their progress (harder to detect early)
        chance = intel * 2 - (progress // 2)

        if random.randint(1,100) < max(5, chance):

            alerts.append({
                "route": target,
                "agent": agent["name"],
                "certainty": min(100, 40 + intel + progress)
            })

    # 🎭 FALSE POSITIVES (noise)
    if p.get("routes") and random.randint(1,100) < 15:
        alerts.append({
            "route": random.choice(list(p["routes"].keys())),
            "agent": "Unknown",
            "certainty": random.randint(20, 50)
        })

    return alerts

def required_firepower(p):
    requirement = 0

    for c in p["crew"]:
        if c["role"] == "soldier":
            requirement += 2
        elif c["role"] == "smuggler":
            requirement += 1
        elif c["role"] == "lieutenant":
            requirement += 3

    return requirement

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

    if len(p["memory"]) > 30:
        p["memory"].pop(0)

    if len(p["npc_memory"]) > 20:
        # 🔥 remove least active NPC
        least_used = min(
            p["npc_memory"].items(),
            key=lambda x: len(x[1].get("history", []))
        )[0]

        del p["npc_memory"][least_used]

def get_player(ctx, data):
    uid = str(ctx.author.id)

    if uid not in data:
        return None, uid

    return data[uid], uid

def gain_xp_player(p, amount):
    p["xp"] += amount

    if p["xp"] >= p["level"] * 100:
        p["xp"] = 0
        p["level"] += 1
        p["reputation"] += 5

def total_firepower(p):
    w = p.get("weapons", {})
    return (
        w.get("pistols", 0) * 1 +
        w.get("rifles", 0) * 3 +
        w.get("military", 0) * 5
    )

def generate_journalist():
    first = ["Elena","Marco","Sofia","Daniel","Carmen","Luis"]
    last = ["Reyes","Vega","Morales","Cruz","Navarro","Santos"]

    return {
        "name": f"{random.choice(first)} {random.choice(last)}",
        "style": random.choice(["investigative","sensational","neutral"]),
        "alive": True,
        "focus": None,
        "credibility": random.randint(40, 90)
    }

def generate_npc(role):
    base_name = random.choice([
        "Javier","Luis","Mateo","Carlos","Diego","Andres","Miguel","Santiago","Juan","Emilio",
        "Rafael","Fernando","Ricardo","Manuel","Alejandro","Eduardo","Victor","Hector","Tomas","Cesar",
        "Julian","Nicolas","Esteban","Cristian","Alonso","Marco","Raul","Orlando","Adrian","Bruno",
        "Marcus","Dante","Vincent","Tony","Salvatore","Luca","Nico","Roman","Alex","Victor",
        "Leon","Noah"
    ])

    nickname = random.choice([
        "", "", "", "", "",  # keep blanks common

        # 🔥 cartel style
        "El Toro",
        "El Flaco",
        "El Diablo",
        "El Lobo",
        "El Gato",
        "El Fantasma",
        "El Rey",
        "El Jefe",
        "El Sicario",
        "El Carnicero",
        "El Veneno",
        "El Silencio",
        "El Tiburon",

        # 🇩🇴 / street vibes
        "El Duro",
        "El Loco",
        "El Bravo",
        "El Tigre",
        "El Menor",
        "El Viejo",
    ])

    return {
        "name": f"{base_name} {nickname}".strip(),
        "role": role,
        "faction": random.choice(["loyalists", "ambitious", "business", "independent"]),
        "loyalty": random.randint(40, 90),
        "personality": random.choice(["loyal","greedy","paranoid","ambitious"]),
        "trait": random.choice(["none","informant","loyalist"]),
        "style": random.choice(["calm","aggressive","cold"]),
        "is_undercover": False,
        "assigned_city": None,
        "is_informant": False,
        "handler": None,  # DEA agent name
        "risk": random.randint(1, 100),  # chance to flip later
        "relationships": {
            "likes": [],
            "rivals": []
        },
        "special": random.choice([
            None,
            "ghost",        # harder to detect (stealth++)
            "ruthless",     # better in combat
            "connected",    # reduces heat slightly
            "rat",          # higher betrayal chance
            "genius"        # faster XP gain
        ]),

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

def bloc_loyalty_shift(p):
    factions = {}

    # group NPCs by faction
    for npc in p.get("crew", []):
        f = npc.get("faction", "independent")
        factions.setdefault(f, []).append(npc)

    for faction, members in factions.items():

        avg_loyalty = sum(n["loyalty"] for n in members) / len(members)

        # 🔥 if one faction drops → all drop
        if avg_loyalty < 40:
            for npc in members:
                npc["loyalty"] -= 2

        # 🔥 strong faction → stabilize
        elif avg_loyalty > 70:
            for npc in members:
                npc["loyalty"] += 1

def update_president(world):
    pres = world["president"]

    pres["term"] -= 1

    if pres["term"] <= 0:
        world["president"] = {
            "name": random.choice(["Anderson","Rivera","Coleman","Vargas"]),
            "style": random.choice(["corrupt","strict","balanced"]),
            "term": 4
        }

def faction_conflict(p):
    events = []

    for npc in p.get("crew", []):

        if random.randint(1,100) < 10:

            for other in p["crew"]:
                if other["faction"] != npc["faction"]:

                    # 🔥 conflict damage
                    loss = random.randint(2,6)
                    p["inventory"]["low"] = max(0, p["inventory"]["low"] - loss)

                    events.append(
                        f"⚠️ {npc['faction']} clashed with {other['faction']} (-{loss})"
                    )
                    break

    return events

def generate_dea_agent():
    return {
        "name": f"{random.choice(DEA_FIRST)} {random.choice(DEA_LAST)}",
        "skill": random.randint(60, 90),

        "style": random.choice(["aggressive", "patient", "corrupt"]),
        "mode": random.choice(["surveillance", "interdiction", "takedown"]),
        "specialty": random.choice(["routes", "crew", "finance"]),

        "region": random.choice(list(LOCATIONS.keys())),

        "intercepts": [],

        "focus": None,
        "target_route": None,

        "heat_target": random.randint(30, 80),

        "wiretap": {
            "active": False,
            "target": None,
            "progress": 0
        },

        "case": {
            "routes": {},
            "crew": {},
            "evidence": 0,
            "stage": "monitoring"
        },

        "knowledge": 0,
        "informants": [],

        "tenure": random.randint(3, 6)
    }

def detect_intent(text):
    text = text.lower()

    if any(w in text for w in ["kill", "threat", "shoot", "attack"]):
        return "threat"
    elif any(w in text for w in ["deal", "negotiate", "talk"]):
        return "diplomatic"
    elif any(w in text for w in ["help", "support", "trust"]):
        return "friendly"
    else:
        return "neutral"

def update_npc_memory(p, npc_name, user_input):
    if npc_name not in p["npc_memory"]:
        p["npc_memory"][npc_name] = {
            "history": [],
            "attitude": "neutral"
        }

    memory = p["npc_memory"][npc_name]
    intent = detect_intent(user_input)
    text = user_input.lower()

    memory["history"].append({
        "text": user_input,
        "intent": detect_intent(user_input)
    })

    if len(memory["history"]) > 5:
        memory["history"].pop(0)

    if intent == "threat":
        memory["attitude"] = "hostile"

    elif intent == "diplomatic":
        memory["attitude"] = "cooperative"

    elif intent == "friendly":
        memory["attitude"] = "loyal"

    if "threat" in text or "kill" in text:
        memory["attitude"] = "hostile"

    elif "respect" in text or "trust" in text:
        memory["attitude"] = "loyal"

    elif "ignore" in text:
        memory["attitude"] = "distant"

def update_dea_stage(p):
    dea = p["dea"]

    if dea < 40:
        p["dea_stage"] = "low"
    elif dea < 80:
        p["dea_stage"] = "watch"
    elif dea < 140:
        p["dea_stage"] = "target"
    elif dea < 200:
        p["dea_stage"] = "manhunt"
    else:
        p["dea_stage"] = "lockdown"

def clear_state(p):
    p["active_scene"] = {}
    p["state"] = None

def update_dea_targets(world, p):
    routes = list(p.get("routes", {}).keys())

    if not routes:
        return

    for agent in world.get("dea_agents", []):

        case = agent.get("case", {})

        # 🎯 smarter scoring (risk + investigation)
        def score(route):
            risk = p["routes"][route]["risk"]
            suspicion = case.get("routes", {}).get(route, 0)

            region_bonus = 0
            if agent.get("region") == route:
                region_bonus += 10

            return risk + (suspicion * 2) + region_bonus

        best_route = max(routes, key=score)

        # 🧠 smarter targeting chance
        chance = 30 + agent.get("knowledge", 0) // 5 + case.get("evidence", 0) // 5

        if random.randint(1,100) < chance:
            agent["target_route"] = best_route

def check_case_raid(p, world):
    for agent in world.get("dea_agents", []):

        case = agent.get("case", {})
        evidence = case.get("evidence", 0)

        # 🎯 threshold scales with player stealth
        threshold = 40 - (p.get("intel_level", 0) * 2)

        if evidence > threshold and random.randint(1,100) < 40:

            # 🔥 BIG EVENT
            return {
                "agent": agent["name"],
                "type": "case_raid",
                "strength": evidence
            }

    return None

def dea_passive_effects(p, world):
    stage = p.get("dea_stage", "low")

    if stage == "watch":
        p["heat"] += 1

    elif stage == "target":
        # money bleed
        loss = random.randint(1000, 3000)
        p["cash"] = max(0, p["cash"] - loss)

    elif stage == "lockdown":
        # 🔥 heavy punishment
        loss = random.randint(3000, 8000)
        p["cash"] = max(0, p["cash"] - loss)

        # inventory seizure
        for k in p["inventory"]:
            p["inventory"][k] = max(0, p["inventory"][k] - random.randint(2, 8))

    elif stage == "manhunt":
        p["heat"] += 3
        p["cash"] = max(0, p["cash"] - random.randint(2000, 5000))

def informant_system(p):
    events = []

    for npc in p.get("crew", []):

        if npc.get("special") == "rat":
            if random.randint(1,100) < 40:
                p["heat"] += 8
                events.append(f"⚠️ {npc['name']} leaked information.")

        if npc.get("trait") == "informant":

            if random.randint(1,100) < 25:

                p["heat"] += 5

                events.append(f"⚠️ Someone leaked information to authorities.")

                # 🔥 boost route risk indirectly
                for r in p.get("routes", {}).values():
                    r["risk"] += 2

        if npc.get("is_undercover"):

            p["heat"] += 6

            for r in p.get("routes", {}).values():
                r["risk"] += 3

            events.append(f"⚠️ {npc['name']} secretly passed intel to authorities.")

    return events

def update_case_stage(agent):
    e = agent["case"]["evidence"]

    if e < 20:
        stage = "monitoring"
    elif e < 50:
        stage = "investigation"
    elif e < 80:
        stage = "target"
    elif e < 120:
        stage = "indictment"
    else:
        stage = "trial"

    agent["case"]["stage"] = stage

def get_notoriety_title(p):
    rep = p.get("reputation", 0)
    heat = p.get("heat", 0)

    if rep < 50:
        return "an unknown operator"

    elif rep < 150:
        return "a rising cartel figure"

    elif rep < 300:
        return "a powerful trafficker"

    elif rep < 500:
        return "a cartel boss"

    else:
        return "a dominant kingpin"

def get_display_name(p):
    rep = p.get("reputation", 0)
    name = p.get("cartel") or p.get("name")

    if rep < 100:
        return "an unidentified cartel"

    elif rep < 300:
        return name

    else:
        return f"{name} (feared cartel leader)"

def record_news(p, headline):
    p.setdefault("news_history", [])
    p["news_history"].append(headline)

    if len(p["news_history"]) > 10:
        p["news_history"].pop(0)

def get_news_callback(p):
    history = p.get("news_history", [])

    if not history or len(history) < 3:
        return None

    if random.randint(1,100) < 40:
        return random.choice([
            "Authorities believe this is connected to earlier activity.",
            "This continues a pattern of escalating cartel violence.",
            "Investigators link this to previous operations.",
            "This appears to be part of a larger expansion strategy."
        ])

    return None

def generate_news(world, p):
    events = []

    roll = random.randint(1,100)

    # =========================
    # DEA / LAW ENFORCEMENT
    # =========================
    if roll < 10:
        city = random.choice(list(LOCATIONS.keys()))
        amount = random.randint(50000, 200000)

        events.append(f"DEA seized {amount} units in {city}. Investigations ongoing.")

    elif roll < 20:
        events.append("Federal agencies announce a nationwide crackdown on trafficking routes.")

    elif roll < 30:
        agent = random.choice(world.get("dea_agents", []))
        events.append(f"DEA Agent {agent['name']} is leading a major operation.")

    # =========================
    # PLAYER-SPECIFIC (if exists)
    # =========================
    elif roll < 45 and p:

        if p.get("in_prison"):
            events.append(f"High-profile cartel figure imprisoned. Influence still suspected outside.")

        elif p["heat"] > 80:
            events.append("Authorities are closing in on a major cartel leader.")

        elif p["bank"] > 50000:
            events.append("A cartel is reportedly generating massive profits across multiple cities.")

    # =========================
    # PRISON EVENTS
    # =========================
    elif roll < 60:
        events.append(random.choice([
            "Violence erupts inside a high-security prison.",
            "Rumors of gang control spreading through prison systems.",
            "An inmate was killed under suspicious circumstances.",
            "Authorities suspect organized crime operations inside prison walls."
        ]))

    # =========================
    # CARTEL WARS
    # =========================
    elif roll < 75:
        city = random.choice(list(world["territories"].keys()))
        events.append(f"Cartel violence escalates in {city} as control weakens.")

    # =========================
    # BETRAYAL / INTERNAL
    # =========================
    elif roll < 85:
        events.append(random.choice([
            "Reports suggest internal betrayal within a cartel.",
            "A high-ranking member has gone missing.",
            "Sources claim informants are increasing inside cartel networks."
        ]))

    # =========================
    # ECONOMY
    # =========================
    elif roll < 95:
        city = random.choice(list(LOCATIONS.keys()))
        change = random.choice(["surge", "drop"])

        events.append(f"Demand for product in {city} sees a sudden {change}.")

    # =========================
    # QUIET / ATMOSPHERE
    # =========================
    else:
        events.append(random.choice([
            "The streets are quiet… but tension is building.",
            "Authorities report no major incidents today.",
            "Something big is coming — sources remain silent."
        ]))

    return random.choice(events)

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

        if random.randint(1,100) < 10:
            data["conflict"] = True

        if data["conflict"]:
            data["control"] = max(0, data["control"] - random.randint(5,15))

            if data["control"] == 0:
                data["owner"] = random.choice(list(CITY_CARTELS.values()))
                data["conflict"] = False

def cartel_ai(world, p):
    territories = world["territories"]

    phase = p.get("war_phase", "calm")

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

        city = world.get("target_city") or random.choice(player_cities)

        defense = territories[city].get("defense", 0)

        base_damage = random.randint(10, 30)

        if phase == "war":
            base_damage += 15
        elif phase == "conflict":
            base_damage += 8

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
        "firepower": total_firepower(p)
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

def smart_cartel_targeting(world, p):
    territories = world["territories"]
    player_cartel = p.get("cartel")

    player_cities = [
        city for city, t in territories.items()
        if t["owner"] == player_cartel
    ]

    if not player_cities:
        return

    # 🎯 prioritize weakest + lowest defense
    def score(city):
        t = territories[city]
        return t["control"] + t.get("defense", 0)

    weakest = min(player_cities, key=score)

    world["target_city"] = weakest

def cartel_takeover_tick(world, p):
    territories = world["territories"]
    player_name = p.get("cartel")

    for city, t in territories.items():
        if t["owner"] != player_name:
            continue

        pressure = random.randint(5, 20)

        # cartel scaling (stronger over time)
        pressure += p.get("war_stage", 0) * 3

        # defense reduces damage
        defense = t.get("defense", 0)
        net = max(0, pressure - defense)

        t["control"] = max(0, t["control"] - net)

        # 🔥 FULL LOSS
        if t["control"] == 0:
            t["owner"] = random.choice(list(CITY_CARTELS.values()))
            t["conflict"] = True

def update_dea(p):
    reduction = p.get("community_support", 0) * 0.5 + p.get("corruption", 0)
    gain = int(p["heat"] * 0.1)

    gain = max(0, gain - reduction)

    p["dea"] += gain

def advance_scene(p):
    if not p.get("state"):
        return

    p["state"]["stage"] += 1

    if p["state"]["stage"] > p["state"].get("max_stage", 1):
        p["state"] = None

def cartel_vs_cartel(world):
    territories = world["territories"]
    bosses = world["bosses"]

    if random.randint(1,100) > 30:
        return []

    events = []

    city = random.choice(list(territories.keys()))

    damage = random.randint(10, 40)

    territories[city]["control"] = max(0, territories[city]["control"] - damage)

    # possible boss death
    if random.randint(1,100) < 20:
        old = bosses[city]["name"]

        if bosses[city].get("lieutenants"):
            new = random.choice(bosses[city]["lieutenants"])
            bosses[city]["name"] = new["name"]

            events.append(f"{old} was killed. {new['name']} has taken control in {city}.")

    events.append(f"Cartel conflict erupted in {city} (-{damage} control)")

    return events

def process_route_risk(p, world):
    territories = world["territories"]

    events = []

    for dest, route in p.get("routes", {}).items():

        base_risk = route["risk"]

        for agent in world.get("dea_agents", []):
            if agent.get("target_route") == dest:
                base_risk += 15 + agent["skill"] // 10

        # 🧠 SMUGGLER EFFECT
        smuggler_bonus = 0

        for npc in p.get("crew", []):
            if npc.get("role") == "smuggler" and npc.get("assigned_city") == dest:

                skill = npc["skills"]["stealth"]
                level = npc.get("level", 1)
                loyalty = npc.get("loyalty", 50)

                bonus = (skill * 0.8) + (level * 2)

                # 🔥 APPLY SPECIAL EFFECTS HERE
                if npc.get("special") == "ghost":
                    bonus *= 1.5   # harder to detect

                elif npc.get("special") == "connected":
                    base_risk -= 3  # reduces overall route risk slightly

                elif npc.get("special") == "rat":
                    base_risk += 5  # more likely to leak info


                # loyalty modifier (keep this AFTER)
                if loyalty < 30:
                    bonus *= 0.5
                elif loyalty > 70:
                    bonus *= 1.2

                smuggler_bonus += bonus

                # ⚠️ betrayal chance
                if npc.get("loyalty", 50) < 20 and random.randint(1,100) < 20:
                    events.append(f"⚠️ {npc['name']} tipped off authorities.")
                    base_risk += 15

        # apply reduction
        base_risk -= int(smuggler_bonus / 5)

        # 📍 territory modifier
        owner = territories.get(dest, {}).get("owner")

        if owner != p.get("cartel"):
            base_risk += 10

        # 🔥 heat scaling
        base_risk += p["heat"] // 10

        # 🧠 DEA pressure
        base_risk += p["dea"] // 20

        # 🛡 corruption reduces risk
        base_risk -= route.get("corruption", 0)

        # 🧠 DEA case pressure (ALL agents)
        total_suspicion = 0

        for agent in world.get("dea_agents", []):
            case = agent.get("case", {})
            total_suspicion += case.get("routes", {}).get(dest, 0)

        base_risk += total_suspicion * 2

        roll = random.randint(1, 100)

        if roll < base_risk:

            event_type = random.choice(["DEA", "CARTEL"])

            if event_type == "DEA":
                loss = random.randint(5, 15)

                p["inventory"]["low"] = max(0, p["inventory"]["low"] - loss)
                p["heat"] += 5

                events.append(f"🚨 DEA intercepted shipment to {dest} (-{loss} low)")

            else:
                loss = random.randint(5, 15)

                p["inventory"]["pure"] = max(0, p["inventory"]["pure"] - loss)

                events.append(f"💀 Rival cartel hit your route to {dest} (-{loss} pure)")

    return events

def check_coup(p):
    ambitious = [
        n for n in p.get("crew", [])
        if n.get("faction") == "ambitious"
    ]

    if len(ambitious) < 3:
        return False

    avg_loyalty = sum(n["loyalty"] for n in ambitious) / len(ambitious)

    if avg_loyalty < 30 and random.randint(1,100) < 20:
        return True

    return False

def format_news(headline, severity="normal"):
    if severity == "breaking":
        return f"🚨 BREAKING: {headline}"

    elif severity == "rumor":
        return f"👀 RUMOR: {headline}"

    return f"📰 {headline}"

def cartel_hits_crew(p, world):
    events = []

    if p.get("war_phase") not in ["conflict", "war"]:
        return events

    if random.randint(1,100) < 30:

        if not p["crew"]:
            return events

        target = random.choice(p["crew"])
        p["crew"].remove(target)

        events.append(f"💀 Rival cartel eliminated {target['name']}")

    return events

def generate_rivalries(p):
    crew = p.get("crew", [])

    if len(crew) < 2:
        return

    for npc in crew:
        if random.randint(1,100) < 30:

            other = random.choice(crew)

            if other["name"] == npc["name"]:
                continue

            npc["relationships"]["rivals"].append(other["name"])
            other["relationships"]["rivals"].append(npc["name"])

def dea_hunt_crew(p, world):
    events = []

    for agent in world.get("dea_agents", []):

        if p["heat"] < agent["heat_target"]:
            continue

        if random.randint(1,100) < 25:

            if not p["crew"]:
                continue

            focus = agent.get("focus")

            if focus:
                target = next((c for c in p["crew"] if c["name"] == focus), None)

            if not focus or not target:
                target = random.choice(p["crew"])

            chance = agent["skill"] - target["skills"]["stealth"] * 5

            # 🔥 SPECIAL EFFECTS
            if target.get("special") == "ghost":
                chance -= 20  # VERY hard to catch

            elif target.get("special") == "ruthless":
                chance += 10  # easier to track (more violent profile)

            if random.randint(1,100) < chance:
                p["crew"].remove(target)

                events.append(f"🚨 {agent['name']} arrested {target['name']}")
            else:
                events.append(f"{target['name']} evaded {agent['name']}")

    return events

async def handle_pressure_event(guild, p, world, event):

    if event == "raid":
        await trigger_scene(guild, p, "DEA RAID", "Federal agents are closing in.")

    elif event == "cartel_attack":
        await cartel_attack_event(guild, p, world)

    elif event == "betrayal":
        await betrayal_progression(guild, p)

    elif event == "wipe":
        cartel_wipe_attempt(p, world)
        await trigger_scene(guild, p, "WIPE", "Your cartel took a massive hit.")

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
            if data.get("lost_announced"):
                continue

            await trigger_scene(
                guild,
                p,
                "Territory Lost",
                f"You lost control of {city}."
            )

            data["lost_announced"] = True

async def cartel_attack_event(guild, p, world):
    result = cartel_ai(world, p)

    if not result:
        return

    cartel_name, city, damage, strategy = result

    await trigger_scene(
        guild,
        p,
        "RIVAL MOVE",
        f"{cartel_name} is targeting {city}.\n\n"
        "Respond: negotiate / attack / defend / retreat"
    )

# =========================
# SCENE SYSTEM
# =========================

async def trigger_scene(guild, player, title, text, npcs=None):
    channel = discord.utils.get(guild.text_channels, name="rp") or guild.system_channel

    if not channel:
        return  # fallback in case even system channel is None

    thread = await channel.create_thread(
        name=f"{title} — {player.get('cartel', player['name'])}",
        type=discord.ChannelType.public_thread
    )

    msg = f"**{title}**\n{text}"

    if npcs:
        names = ", ".join(npc["name"] for npc in npcs)
        msg += f"\n\nPresent: {names}"

        # 🔥 store active scene NPCs
        player.setdefault("active_scene", {})
        player["active_scene"]["npcs"] = npcs

        player["state"] = {
        "type": title.lower().replace(" ", "_"),
        "stage": 1,
        "max_stage": 3,
        "data": {}
    }

    await thread.send(msg)

    import asyncio

    async def auto_delete_thread(thread):
        await asyncio.sleep(300)  # 5 minutes
        try:
            await thread.delete()
        except:
            pass

    asyncio.create_task(auto_delete_thread(thread))

# -------------------------

async def send_news(guild, text=None, world=None, p=None):

    # 🔧 helper INSIDE function (properly indented)
    def get_news_channel(guild, city=None):
        if city:
            ch = discord.utils.get(
                guild.text_channels,
                name=f"news-{city.lower().replace(' ','-')}"
            )
            if ch:
                return ch

        return discord.utils.get(guild.text_channels, name="news")

    # 📍 actually pick the channel
    city = p.get("location") if p else None
    channel = get_news_channel(guild, city)

    if not channel:
        return

    # 🔥 AUTO-GENERATE NEWS IF NO TEXT
    if text is None and world:
        text = generate_news(world, p)

    timestamp = datetime.now().strftime("%I:%M %p")
    day = world.get("day", 1)

    msg = await channel.send(f"Day {day}\n@ {timestamp}\n📰 {text}")

    if random.randint(1,100) < 30 and p:
        await trigger_scene(
            guild,
            p,
            "NEWS EVENT",
            f"{text}\n\nRespond: bribe / investigate / silence / ignore"
        )

    await msg.add_reaction("⚔️")
    await msg.add_reaction("👀")
    await msg.add_reaction("💰")

    return msg

async def npc_encounter(guild, p):
    if random.randint(1,100) > 25:
        return  # 25% chance per action

    role = random.choice(["dealer", "lieutenant", "informant", "smuggler"])

    npc = generate_npc(role)

    channel = discord.utils.get(guild.text_channels, name="rp")
    if not channel:
        return

    thread = await channel.create_thread(
        name=f"Encounter — {npc['name']}",
        type=discord.ChannelType.public_thread
    )

    await thread.send(
        f"You encounter **{npc['name']}** ({role}).\n"
        f"They approach you cautiously...\n\n"
        f"What do you do?"
    )

    # store temp NPC
    p.setdefault("npc_relations", {})

async def run_turn(ctx, p, world):
    # 🧠 hierarchy FIRST
    await run_hierarchy_systems(ctx.guild, p, world)

    bloc_loyalty_shift(p)

    for npc in p["crew"]:
        if npc.get("is_undercover") and random.randint(1,100) < 10:
            p["crew"].remove(npc)
            p["heat"] += 15

    for e in faction_conflict(p):
        await ctx.send(e)

    if random.randint(1,100) < 15:
        await ctx.send("📞 You feel like your calls aren't secure lately...")

    if check_coup(p):
        await trigger_scene(ctx.guild, p, "COUP", "Your own cartel is turning on you.")

    # 🔥 pressure build
    p["pressure"] += 5 + p["heat"] // 10

    betrayals = corruption_betrayal(p)

    for b in betrayals:
        await ctx.send(b)

    kill_events = rivalry_kill(p)

    for e in kill_events:
        await ctx.send(e)

    rival_events = rivalry_sabotage(p)

    for e in rival_events:
        await ctx.send(e)

    inf_events = informant_system(p)

    for e in inf_events:
        await ctx.send(e)

    # 🚨 law enforcement
    update_dea(p)
    update_dea_stage(p)
    update_dea_targets(world, p)
    dea_passive_effects(p, world)

    alerts = detect_wiretap(p, world)

    for alert in alerts:
        await ctx.send(
            f"📡 Suspicious activity detected on route to {alert['route']}.\n"
            f"Confidence: {alert['certainty']}%"
        )

    case_event = check_case_raid(p, world)

    if case_event:
        await trigger_scene(
            ctx.guild,
            p,
            "CASE RAID",
            f"{case_event['agent']} built a case against you.\n\n"
            "Federal strike incoming.\n\n"
            "Respond: fight / flee / hide / bribe"
        )

    dea_events = dea_hunt_crew(p, world)

    for e in dea_events:
        await ctx.send(e)

    cartel_events = cartel_hits_crew(p, world)

    for e in cartel_events:
        await ctx.send(e)

    pres = world.get("president", {})
    style = pres.get("style")

    if style == "strict":
        p["heat"] += 2

    elif style == "corrupt":
        p["heat"] = max(0, p["heat"] - 2)

    for city in LOCATIONS:
        count = sum(1 for c in p["crew"] if c.get("assigned_city") == city)

        if count > 5:
            p["heat"] += 2

    if p.get("has_leverage"):
        p["heat"] += 1

    await check_raid(ctx.guild, p)
    await dea_event(ctx.guild, p, world)

    # 👨‍👩‍👧 life
    await family_risk(ctx.guild, p)

    # ⚔️ war system
    escalate_war(p)
    update_war_phase(p, world)
    await war_event(ctx.guild, p)

    world_war_tick(world)
    evolve_cartels(world, p)

    # 🎯 smart targeting
    smart_cartel_targeting(world, p)

    cartel_takeover_tick(world, p)

    gain_xp_player(p, 5)

    # 💀 pressure event (controlled chaos)
    event = check_pressure_event(p)
    if event:
        await handle_pressure_event(ctx.guild, p, world, event)
        p["pressure"] = 0

    # 🧠 NPC + RP
    await npc_world_actions(ctx.guild, p, world)
    await npc_encounter(ctx.guild, p)

    # 📆 time
    events = daily_tick(p, world)

    if events:
        for old, new in events:
            await send_news(
                ctx.guild,
                f"DEA Agent {old} reassigned. New agent {new} deployed."
            )

    # 🌎 world event
    if p.get("trigger_world_event"):
        await world_event(ctx.guild, p, world)
        p["trigger_world_event"] = False


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
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    price = amount * random.randint(150, 300)

    if p["cash"] < price:
        await ctx.send("Not enough cash.")
        return

    if p["supply"] + amount > p["max_storage"]:
        await ctx.send("Not enough storage.")
        return

    p["cash"] -= price
    p["supply"] += amount

    p["heat"] += 3

    save_data(data)

    await ctx.send(f"Bought {amount} units for ${price}")

@bot.command()
async def cartel(ctx, *, name):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    data[uid]["cartel"] = name

    save_data(data)

    await ctx.send(f"Cartel created: {name}")

@bot.command()
async def scramble(ctx, city):
    data = load_data()
    p, uid = get_player(ctx, data)
    world = load_world()

    if city not in p.get("routes", {}):
        await ctx.send("No route there.")
        return

    cost = 3000

    if p["cash"] < cost:
        await ctx.send("Not enough cash.")
        return

    p["cash"] -= cost

    removed = False

    for agent in world.get("dea_agents", []):
        wiretap = agent.get("wiretap", {})

        if wiretap.get("target") == city and wiretap.get("active"):
            wiretap["active"] = False
            wiretap["progress"] = 0
            removed = True

    save_data(data)
    save_world(world)

    if removed:
        await ctx.send(f"📡 You scrambled communications in {city}. Wiretap disrupted.")
    else:
        await ctx.send("Nothing found, but systems secured.")

@bot.command()
async def identity(ctx, style):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    if style not in ["aggressive", "stealth", "business", "balanced"]:
        await ctx.send("Choose: aggressive, stealth, business, balanced")
        return

    p["identity"] = style
    save_data(data)

    await ctx.send(f"Identity set to {style}")

@bot.command()
async def map(ctx):
    data = load_data()
    world = load_world()
    sanitize_world(world)

    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    territories = world["territories"]

    def get_icon(city):
        t = territories[city]

        if t["owner"] == p.get("cartel"):
            return "🟩"  # yours
        elif t["conflict"]:
            return "🟥"  # war
        elif t["control"] < 30 and t["owner"] == p.get("cartel"):
            return "🟧"  # losing control
        elif t["owner"]:
            return "🟨"  # enemy
        else:
            return "⬜"

    def heat_icon():
        h = p["heat"]
        if h < 30:
            return "🟢"
        elif h < 70:
            return "🟡"
        else:
            return "🔴"

    embed = discord.Embed(
        title="🧠 STRATEGY MAP",
        description=f"Heat Level: {heat_icon()} ({p['heat']})"
    )

    map_view = "\n".join(
        f"{get_icon(city)} {city} ({territories[city]['control']}%)"
        for city in territories
    )

    status_lines = []

    for city, t in territories.items():
        if t["owner"] == p.get("cartel") and t["control"] < 30:
            status_lines.append(f"{city}: Losing control")

        if t["conflict"]:
            status_lines.append(f"{city}: Active war")

    embed.add_field(
        name="⚠️ Situations",
        value="\n".join(status_lines) or "Stable",
        inline=False
    )

    embed.add_field(name="Territories", value=map_view, inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def guide(ctx):
    embed = discord.Embed(
        title="🧠 CARTEL SIM — COMPLETE SYSTEM GUIDE",
        description="Everything you can do. Master the system.",
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
        name="💰 CORE LOOP",
        value="""
buy → produce → smuggle → sell → launder  
""",
        inline=False
    )

    embed.add_field(
        name="📦 SUPPLY SYSTEM (NEW)",
        value="""
!route A B → create supply line  
!protect <city> <money> → reduce interception risk  

⚠️ Routes can be:
• Intercepted by DEA  
• Attacked by cartels  
• Betrayed by corrupt officials  
""",
        inline=False
    )

    embed.add_field(
        name="⚔️ TERRITORY",
        value="""
!travel <city>  
!invade <city>  
!defend <lt> <city>  

Owning cities:
• lowers smuggle risk  
• increases control  
""",
        inline=False
    )

    embed.add_field(
        name="🔫 CREW / POWER",
        value="""
!hire <role>  
!buyguns <tier> <amount>  
!assign <role> <city>  
""",
        inline=False
    )

    embed.add_field(
        name="🏢 ASSETS",
        value="""
!warehouse  
!lab  
!business <type>  
""",
        inline=False
    )

    embed.add_field(
        name="🧠 INTEL / CONTROL",
        value="""
!intel  
!investigate  
!interrogate  
!execute  
!replace  
""",
        inline=False
    )

    embed.add_field(
        name="👨‍👩‍👧 LIFE / RP SYSTEM",
        value="""
!meet → meet partner  
!date_accept → accept  
!kid → have child  

In RP threads:
• threaten  
• negotiate  
• attack  
• manipulate  

Everything affects the world  
""",
        inline=False
    )

    embed.add_field(
        name="⚠️ SYSTEMS",
        value="""
• DEA raids  
• Cartel wars  
• Route interceptions  
• Corruption betrayal  
• NPC betrayal  
• Family risk  
""",
        inline=False
    )

    embed.add_field(
        name="🏆 WIN CONDITION",
        value="""
Control 3+ territories  
AND  
$50,000+ bank  
""",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command()
async def lifestyle(ctx, level):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    if level not in ["basic", "luxury", "kingpin"]:
        await ctx.send("Choose: basic, luxury, kingpin")
        return

    cost = {
        "basic": 0,
        "luxury": 10000,
        "kingpin": 30000
    }

    if p["bank"] < cost[level]:
        await ctx.send("Not enough bank money.")
        return

    p["bank"] -= cost[level]
    p["lifestyle"] = level

    save_data(data)

    await ctx.send(f"Lifestyle upgraded to {level}")

@bot.command()
async def hit(ctx, city, *, target_name):
    data = load_data()
    world = load_world()

    p, uid = get_player(ctx, data)

    boss = world["bosses"].get(city)

    if not boss:
        await ctx.send("No target found.")
        return

    # check boss
    if boss["name"].lower() == target_name.lower():

        if random.randint(1,100) < 50:
            old = boss["name"]

            # promote lieutenant
            if boss.get("lieutenants"):
                new = random.choice(boss["lieutenants"])
                boss["name"] = new["name"]

                await ctx.send(f"💀 You eliminated {old}. {new['name']} takes over.")
        else:
            await ctx.send("Hit failed.")

    else:
        for lt in boss.get("lieutenants", []):
            if lt["name"].lower() == target_name.lower():

                if random.randint(1,100) < 60:
                    boss["lieutenants"].remove(lt)
                    await ctx.send(f"💀 You eliminated lieutenant {lt['name']}")
                else:
                    await ctx.send("Hit failed.")
                break

    save_world(world)

@bot.command()
async def route(ctx, from_city, to_city):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    if from_city not in LOCATIONS or to_city not in LOCATIONS:
        await ctx.send("Invalid cities.")
        return

    p.setdefault("routes", {})

    p["routes"][to_city] = {
        "from": from_city,
        "risk": random.randint(5, 15),
        "heat": 0,
        "corruption": 0  # protection level
    }

    save_data(data)

    await ctx.send(f"Route established: {from_city} → {to_city}")

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

@bot.command()
async def reset(ctx):
    data = load_data()
    uid = str(ctx.author.id)

    if uid in data:
        del data[uid]
        save_data(data)
        await ctx.send("Your empire has been wiped. Use !start to begin again.")
    else:
        await ctx.send("You don’t have a profile yet.")

@bot.command()
async def join_gang(ctx, *, name):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p.get("in_prison"):
        await ctx.send("You’re not in prison.")
        return

    if name not in PRISON_GANGS:
        await ctx.send(f"Available: {', '.join(PRISON_GANGS)}")
        return

    p["prison"]["gang"] = name
    p["prison"]["respect"] = 10

    save_data(data)

    await ctx.send(f"You joined {name}.")

@bot.command()
async def prison_protect(ctx):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p.get("in_prison"):
        return

    cost = 2000

    if p["cash"] < cost:
        await ctx.send("Not enough cash.")
        return

    p["cash"] -= cost
    p["prison"]["heat_inside"] = max(0, p["prison"]["heat_inside"] - 10)

    await ctx.send("🛡 You secured protection inside prison.")

    save_data(data)

@bot.command()
async def silence(ctx, *, name):
    world = load_world()

    for j in world["media"]["journalists"]:
        if j["name"].lower() == name.lower() and j["alive"]:
            j["alive"] = False

            await send_news(
                ctx.guild,
                f"Journalist {j['name']} was found dead under mysterious circumstances.",
                world,
                None
            )

            save_world(world)
            return

    await ctx.send("Journalist not found.")

@bot.command()
async def lobby(ctx):
    data = load_data()
    world = load_world()

    p, uid = get_player(ctx, data)

    pres = world.get("president")

    if pres["style"] != "corrupt":
        await ctx.send("President is not open to deals.")
        return

    if random.randint(1,100) < 60:
        p["heat"] -= 10
        await ctx.send("You secured protection.")
    else:
        await ctx.send("Deal failed.")

    save_data(data)

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

        for agent in world.get("dea_agents", []):
            if agent["case"]["stage"] == "trial":
                p["trial"] = {
                    "progress": 0,
                    "verdict": None
                }
                break

        p["sentence"] = random.randint(2, 5)
        p["charges"] = random.randint(1, 5) + p.get("dea", 0) // 40

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

        await send_news(
            guild,
            f"{p.get('cartel')} leader arrested in major federal operation.",
            world,
            p
        )

        save_world(load_data())

async def court_trial(guild, p):

    evidence = p.get("dea", 0) + p.get("charges", 0) * 10
    defense = p.get("lawyer_level", 0) * 15

    outcome = evidence - defense + random.randint(-20,20)

    if outcome > 50:
        years = random.randint(5, 15)
    elif outcome > 20:
        years = random.randint(2, 5)
    else:
        years = random.randint(0, 2)

    p["sentence"] = years

    await trigger_scene(
        guild,
        p,
        "COURT VERDICT",
        f"You were sentenced to {years} years."
    )

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
            if total_firepower(p) < required_firepower(p):
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

    if not p["kids"] and not p["partner"]:
        return

    risk = 20 + p["heat"] // 5

    if random.randint(1,100) < risk:

        await trigger_scene(
            guild,
            p,
            "Family Threat",
            "Your family has been targeted."
        )

        p["stress"] += 15

        # possible outcomes
        roll = random.randint(1,100)

        if roll < 30:
            loss = int(p["cash"] * 0.3)
            p["cash"] -= loss

        elif roll < 60:
            p["heat"] += 10

        else:
            # emotional impact
            p["stress"] += 20

# =========================
# ECONOMY SYSTEM
# =========================

def produce_cocaine(p):
    labs = p["assets"].get("lab", 0)

    if labs <= 0:
        return "no_lab"

    if p["supply"] <= 0:
        return "no_supply"

    used = min(p["supply"], labs * 10)
    p["supply"] -= used

    low = int(used * random.uniform(0.4, 0.6))
    pure = int(used * random.uniform(0.2, 0.4))
    high = int(used * random.uniform(0.1, 0.2))

    p["inventory"]["low"] += low
    p["inventory"]["pure"] += pure
    p["inventory"]["high"] += high

    return f"Produced {used} units"

# =========================
# TERRITORY SYSTEM
# =========================

def territory_gain(p, world):
    territories = world["territories"]
    loc = p["location"]

    if loc not in territories:
        return

    territories[loc]["lost_announced"] = False

    resistance = territories[loc].get("resistance", 0)

    gain = random.randint(5, 15)
    gain = max(1, gain - resistance // 10)

    for lt in p["hierarchy"].get("lieutenants", []):
        if lt.get("assigned_city") == loc:
            gain += 5

    territories[loc]["control"] += gain

    if territories[loc]["control"] >= 100:
        territories[loc]["owner"] = p.get("cartel", p["name"])

    crew_in_city = sum(
        1 for c in p["crew"]
        if c.get("assigned_city") == loc
    )

    gain += crew_in_city * 3

def passive_income(p, world):
    total = 0

    territories = world["territories"]

    owner_name = p.get("cartel") or p.get("name")

    for city, t in territories.items():
        if t["owner"] == owner_name:
            total += int(2000 * (t["control"] / 100))

    p["bank"] += total

def corruption_betrayal(p):
    events = []

    for city, route in p.get("routes", {}).items():

        corruption = route.get("corruption", 0)

        if corruption <= 0:
            continue

        betrayal_chance = max(5, 30 - corruption)

        if random.randint(1,100) < betrayal_chance:

            loss = random.randint(10, 25)

            p["inventory"]["high"] = max(0, p["inventory"]["high"] - loss)

            p["heat"] += 10

            route["corruption"] = max(0, corruption - 2)

            events.append(f"⚠️ Corrupt officials in {city} flipped on you (-{loss} high, +heat)")

    return events

def rivalry_kill(p):
    events = []

    if random.randint(1,100) > 10:
        return events

    for npc in p.get("crew", []):

        rivals = npc.get("relationships", {}).get("rivals", [])

        if not rivals:
            continue

        if random.randint(1,100) < 20:

            victim_name = random.choice(rivals)

            for other in p["crew"]:
                if other["name"] == victim_name:
                    p["crew"].remove(other)

                    events.append(f"💀 {npc['name']} killed {victim_name}")
                    break

    return events

# =========================
# SELL SYSTEM
# =========================

def calculate_profit(p, world, sold_low, sold_pure, sold_high):

    loc = LOCATIONS[p["location"]]

    econ = world.get("economy", {}).get(p["location"], {})

    demand = econ.get("demand", 100)
    sat = econ.get("saturation", 0)

    # 🔥 price modifier
    econ_mult = max(0.5, min(1.5, (demand - sat) / 100))

    prices = world.get("market", {
        "low": 200,
        "pure": 400,
        "high": 700
    })

    total = (
        sold_low * prices["low"] +
        sold_pure * prices["pure"] +
        sold_high * prices["high"]
    )

    # location multiplier
    total = int(total * loc["profit_mult"] * econ_mult)

    # capo bonus
    capo_bonus = len(p["hierarchy"].get("capos", [])) * 0.1
    total = int(total * (1 + capo_bonus))

    for capo in p["hierarchy"].get("capos", []):
        total += min(500, capo["skills"]["business"] * 50)

    return total

# -------------------------
# TIME SYSTEM
# -------------------------

def daily_tick(p, world):
    if p.get("in_prison"):
        p["sentence"] -= 1

        # 🧾 release check
        if p["sentence"] <= 0:
            p["in_prison"] = False
            p["heat"] = 20

        if random.randint(1,100) < 15:
            if p["crew"]:
                traitor = random.choice(p["crew"])
                traitor["loyalty"] -= 10

        # 🔪 prison attack
        if random.randint(1,100) < 15:

            danger = p["prison"]["heat_inside"] + 20

            if random.randint(1,100) < danger:
                loss = random.randint(1000,5000)
                p["cash"] = max(0, p["cash"] - loss)

                p["stress"] += 10

                # possible injury
                if random.randint(1,100) < 30:
                    p["sentence"] += 1

                # 🔥 send event later via ctx if you want

        # 🚓 breakout attempt
        if p.get("crew"):

            avg_loyalty = sum(n["loyalty"] for n in p["crew"]) / len(p["crew"])

            if avg_loyalty > 70 and random.randint(1,100) < 10:

                if random.randint(1,100) < avg_loyalty:

                    p["in_prison"] = False
                    p["heat"] += 40

                    # lose some crew in breakout
                    if p["crew"]:
                        lost = random.choice(p["crew"])
                        p["crew"].remove(lost)

                    # you should trigger a scene instead if in run_turn

        if p.get("trial"):
            p["trial"]["progress"] += 1

            if p["trial"]["progress"] > 3:
                media_pressure = sum(
                    j["credibility"]
                    for j in world.get("media", {}).get("journalists", [])
                    if j["alive"]
                )

                chance = (
                    50
                    - p.get("corruption", 0) * 2
                    + p["heat"]
                    + (media_pressure // 50)  # 🔥 media influence
                )

                if random.randint(1,100) < chance:
                    p["in_prison"] = True
                    base = random.randint(3,10)

                    media_bonus = media_pressure // 40

                    p["sentence"] = base + media_bonus
                    verdict = "guilty"
                else:
                    verdict = "not guilty"

                p["trial"]["verdict"] = verdict

                if p["trial"].get("verdict") and not p["trial"].get("resolved"):
                    await court_trial(guild, p)
                    p["trial"]["resolved"] = True

        # 💼 PARTIAL BUSINESS INCOME (nerfed)
        for biz in p.get("businesses", []):
            p["bank"] += int(biz.get("income", 0) * 0.5)

        # ⚠️ CREW INSTABILITY (you’re not there)
        for npc in p.get("crew", []):
            if random.randint(1,100) < 15:
                npc["loyalty"] -= random.randint(2,6)

        # 🕵️ HIGHER INFORMANT RISK
        if random.randint(1,100) < 20:
            p["heat"] += 5

        # 🚫 IMPORTANT: DO NOT RETURN HERE

    if p["level"] >= 5:
            p["max_storage"] += 5

    for c in p.get("contracts", []):
        if c["cooldown"] <= 0:
            p["supply"] += c["amount"]
            c["cooldown"] = 1  # daily tick
        else:
            c["cooldown"] -= 1

    if p["lifestyle"] == "luxury":
        p["heat"] -= 1
        p["stress"] -= 1

    elif p["lifestyle"] == "kingpin":
        p["heat"] -= 2
        p["stress"] -= 2
        p["reputation"] += 1

    for city, t in world["territories"].items():
        if t["owner"] == p.get("cartel") and t["control"] > 0:
            if random.randint(1,100) < 20:
                t["control"] -= random.randint(1,5)

    p["day"] += 1

    rotation_events = []

    for i, agent in enumerate(world.get("dea_agents", [])):
        agent["tenure"] -= 1

        if agent["tenure"] <= 0:
            old_name = agent["name"]

            new_agent = generate_dea_agent()
            world["dea_agents"][i] = new_agent

            rotation_events.append((old_name, new_agent["name"]))

    if random.randint(1,100) < 10:
        reduce_firepower(p, 1)

    for kid in p["kids"]:
        if random.randint(1,3) == 1:  # slower aging
            kid["age"] += 1

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

    return rotation_events

# =========================
# COMMANDS — ECONOMY
# =========================

@bot.command()
async def produce(ctx):
    data = load_data()
    world = load_world()
    sanitize_world(world)

    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return
    
    if p.get("in_prison"):
        daily_tick(p, world)
        save_data(data)
        await ctx.send("You're in prison. Time passes...")
        return
    
    ok, unarmed = check_firepower(p)

    if not ok:
        penalty = len(unarmed)
        p["heat"] += penalty
        p["stress"] += penalty
        await ctx.send(f"⚠️ You're under-armed by {len(unarmed)} weapons.")

    result = produce_cocaine(p)

    if result == "no_lab":
        await ctx.send("You need a lab to produce.")
        return

    if result == "no_supply":
        await ctx.send("You have no supply.")
        return

    await ctx.send(result)

    await run_turn(ctx, p, world)

    gain_xp_player(p, 5)

    apply_player_identity_effects(p)

    save_data(data)
    save_world(world)

    await ctx.send("Production complete.")

@bot.command()
async def business(ctx, type):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    world = load_world()
    sanitize_world(world)

    territories = world["territories"]
    loc = p["location"]

    owner = territories.get(loc, {}).get("owner")

    if owner != p.get("cartel") and loc not in p.get("deals", {}):
        await ctx.send("You need a deal or control to smuggle here.")
        return

    if p.get("in_prison"):
        daily_tick(p, world)
        save_data(data)
        await ctx.send("You're in prison. Time passes...")
        return

    capacity = 20 + (p["vehicles"]["planes"] * 50)
    moved = random.randint(10, capacity)

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
            take = min(int(moved * ratio), p["inventory"][tier], remaining)

        take = min(take, p["inventory"][tier])

        p["inventory"][tier] -= take
        remaining -= take

    events = process_route_risk(p, world)

    for e in events:
        await ctx.send(e)

    if p.get("routes"):
        bonus = len(p["routes"]) * 5
        moved += bonus

    if random.randint(1,100) < 15:
        loss = random.randint(5, 15)
        p["inventory"]["low"] = max(0, p["inventory"]["low"] - loss)
        await ctx.send("Shipment intercepted on route.")

    p["heat"] += 5

    ok, unarmed = check_firepower(p)

    if not ok:
        penalty = len(unarmed)
        p["heat"] += penalty
        p["stress"] += penalty
        await ctx.send(f"⚠️ You're under-armed by {len(unarmed)} weapons.")

    await run_turn(ctx, p, world)

    gain_xp_player(p, 10)

    apply_player_identity_effects(p)

    save_data(data)
    save_world(world)

    await ctx.send("Smuggled product.")

    for npc in p["crew"]:
        xp_gain = 5

        if npc.get("special") == "genius":
            xp_gain = 10

        gain_xp(npc, xp_gain)

@bot.command()
async def sell(ctx):
    data = load_data()
    world = load_world()
    sanitize_world(world)

    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    territories = world["territories"]
    loc = p["location"]

    owner = territories.get(loc, {}).get("owner")

    if owner != p.get("cartel") and loc not in p.get("deals", {}):
        await ctx.send("You need control or a deal in this city to sell.")
        return

    if p.get("in_prison"):
        daily_tick(p, world)
        save_data(data)
        await ctx.send("You're in prison. Time passes...")
        return
    
    sold_low = min(p["inventory"]["low"], random.randint(5, 15))
    sold_pure = min(p["inventory"]["pure"], random.randint(3, 10))
    sold_high = min(p["inventory"]["high"], random.randint(1, 5))

    p["inventory"]["low"] -= sold_low
    p["inventory"]["pure"] -= sold_pure
    p["inventory"]["high"] -= sold_high

    profit = calculate_profit(p, world, sold_low, sold_pure, sold_high)

    world["economy"][p["location"]]["saturation"] += (sold_low + sold_pure + sold_high) // 5

    p["cash"] += profit
    p["heat"] += 5

    p["reputation"] += int(profit / 1000)
    update_rank(p)

    ok, unarmed = check_firepower(p)

    if not ok:
        penalty = len(unarmed)
        p["heat"] += penalty
        p["stress"] += penalty
        await ctx.send(f"⚠️ You're under-armed by {len(unarmed)} weapons.")

    territory_gain(p, world)
    passive_income(p, world)

    # 🔥 ADD ALL SYSTEMS HERE
    await run_turn(ctx, p, world)

    apply_player_identity_effects(p)

    if check_endgame(p, world):
        await ctx.send("You have become the dominant cartel. You win.")

    if check_collapse(p):
        await ctx.send("Your empire has collapsed. You must rebuild.")

    gain_xp_player(p, 20)

    save_data(data)
    save_world(world)

    await ctx.send(f"Sold product for ${profit}")

@bot.command()
async def protect(ctx, city, amount: int):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    if city not in p.get("routes", {}):
        await ctx.send("No route there.")
        return

    if p["cash"] < amount:
        await ctx.send("Not enough cash.")
        return

    p["cash"] -= amount

    boost = amount // 2000

    p["routes"][city]["corruption"] += boost

    await ctx.send(f"Protected route to {city} (+{boost} corruption)")

    save_data(data)

@bot.command()
async def launder(ctx):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
async def bribe(ctx, amount: int):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    if p["cash"] < amount:
        await ctx.send("Not enough cash.")
        return

    p["cash"] -= amount

    gain = amount // 2000
    p["corruption"] += gain

    await ctx.send(f"Corruption increased (+{gain})")

    save_data(data)

@bot.command()
async def intel(ctx):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    new_lt = generate_npc("lieutenant")

    p["hierarchy"]["lieutenants"].append(new_lt)

    await ctx.send(f"Replaced with new lieutenant: {new_lt['name']}")

    save_data(data)

@bot.command()
async def plea(ctx):
    data = load_data()
    p, uid = get_player(ctx, data)

    reduction = random.randint(1,3)

    p["sentence"] = max(0, p["sentence"] - reduction)
    p["reputation"] -= 10

    await ctx.send(f"⚖️ You accepted a plea deal (-{reduction} years, -rep)")
    save_data(data)

@bot.command()
async def community(ctx, amount: int):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    effects["control"] = get_val("CONTROL+") - get_val("CONTROL-")
    effects["cocaine_low"] = get_val("LOW+") - get_val("LOW-")
    effects["cocaine_pure"] = get_val("PURE+") - get_val("PURE-")
    effects["cocaine_high"] = get_val("HIGH+") - get_val("HIGH-")

    if "CREW+" in text:
        effects["crew_add"] = text.split("CREW+")[1].split()[0]

    if "CREW-" in text:
        effects["crew_remove"] = text.split("CREW-")[1].split()[0]

    effects["deal_city"] = None

    if "deal" in text.lower():
        for city in LOCATIONS:
            if city.lower() in text.lower():
                effects["deal_city"] = city

    return effects

@bot.command()
async def leverage(ctx, *, city):
    data = load_data()
    world = load_world()
    sanitize_world(world)

    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    boss = world["bosses"].get(city)
    family = boss.get("family", {})

    if not boss or not boss.get("family", {}).get("has_family"):
        await ctx.send("No leverage found.")
        return

    if family.get("partner"):
        await ctx.send(f"You found leverage through {family['partner']['name']}")
    elif family.get("kids"):
        await ctx.send(f"You found leverage through their family")

    power = boss["family"]["vulnerability"]

    if random.randint(1,100) < power:
        world["territories"][city]["control"] -= 30

        await trigger_scene(
            ctx.guild,
            p,
            "LEVERAGE SUCCESS",
            f"You now have leverage over {city}.\n\n"
            "Use it: negotiate / threaten / exploit"
        )
        await rival_reaction_to_leverage(ctx.guild, p, world, city)
    else:
        p["heat"] += 10
        await ctx.send("Leverage attempt failed.")

    save_world(world)
    save_data(data)

def apply_effects(p, world, effects):
    p["cash"] += effects["cash"]
    p["heat"] += effects["heat"]

    p["inventory"]["low"] += effects["cocaine_low"]
    p["inventory"]["pure"] += effects["cocaine_pure"]
    p["inventory"]["high"] += effects["cocaine_high"]

    if effects.get("control"):
        loc = p["location"]
        if loc in world["territories"]:
            world["territories"][loc]["control"] += effects["control"]

    if effects.get("deal_city"):
        p.setdefault("deals", {})
        p["deals"][effects["deal_city"]] = "AI-generated"

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

CORE RULES:
- The player can attempt ANY action through natural language.
- You must interpret intent (threat, negotiation, deception, violence, manipulation).
- The world reacts realistically and proportionally.
- Avoid random outcomes — base consequences on context.

TONE RULES:
- Cartel members: cold, direct, dangerous
- Government/DEA: formal, strategic
- Partner/family: emotional, human
- Kids: innocent

- Bribes to high officials can reduce charges or sentences but are expensive and risky

PLAYER STATE:
Cartel: {p.get("cartel")}
Location: {p["location"]}
Heat: {p["heat"]}
Cash: {p["cash"]}
Style: {p.get("style")}
Rank: {p['rank']}
Reputation: {p['reputation']}
Stress: {p['stress']}

BEHAVIOR SYSTEM:
Interpret player intent into one of these:
- Threat → increases fear, may cause retaliation or compliance
- Negotiation → may reduce conflict or create deals
- Violence → high reward, high risk (heat, loss, escalation)
- Deception → success depends on context and intelligence
- Emotional manipulation → stronger on family targets
- Passive / observing → builds intel, lowers risk

CONSEQUENCE RULES:
- Strong actions → strong consequences
- High heat → harsher punishment
- Low loyalty NPCs → more likely to betray
- Family involvement → emotional reactions, unstable outcomes
- Player advantage → increases success chance
- Never guarantee success

EFFECT FORMAT:
When consequences happen, include:
[EFFECT: CASH+X HEAT+X LOW+X PURE+X HIGH+X CREW+type CREW-type]

IMMERSION:
- Respond in narrative dialogue
- Characters speak naturally
- Avoid robotic phrasing
- Make interactions feel real and tense
"""

    # -------------------------
    # HIERARCHY
    # -------------------------
    ub = p["hierarchy"].get("underboss")
    if ub:
        context += f"\nUnderboss: {ub['name']} (loyalty {ub['loyalty']})"

    for lt in p["hierarchy"].get("lieutenants", []):
        if lt.get("assigned_city"):
            context += f"\nLieutenant: {lt['name']} controls {lt['assigned_city']} (loyalty {lt['loyalty']})"

    if p.get("partner"):
        context += f"\nPartner: {p['partner']['name']} ({p['partner'].get('personality', 'unknown')})"

    if p.get("kids"):
        context += f"\nKids: {[k['name'] for k in p['kids']]}"

    context += f"\nWar Phase: {p.get('war_phase')}"
    context += f"\nLifestyle: {p.get('lifestyle', 'basic')}"

    context += "\nNPC MEMORY DETAILS:\n"

    for name, data in p["npc_memory"].items():
        if data["history"]:
            last = data["history"][-1]
            context += f"- {name}: {data['attitude']} (last interaction: {last['intent']})\n"

    # -------------------------
    # MEMORY
    # -------------------------
    if p.get("memory"):
        context += "\nRecent history:\n"
        for m in p["memory"][-3:]:
            context += f"- {m['input']} → {m['result']}\n"

    if p.get("npc_memory"):
        context += "\nNPC relationships:\n"
        for name, data in p["npc_memory"].items():
            context += f"- {name}: {data['attitude']} | recent: {data['history'][-2:] if data['history'] else []}\n"

    # -------------------------
    # CURRENT SCENE (CRITICAL)
    # -------------------------
    if p.get("active_scene", {}).get("npcs"):
        context += "\nCurrent scene characters:\n"
        for npc in p["active_scene"]["npcs"]:
            context += (
                f"- {npc['name']} "
                f"(role: {npc.get('role')}, "
                f"personality: {npc.get('personality')}, "
                f"style: {npc.get('style')}, "
                f"loyalty: {npc.get('loyalty')})\n"
            )

    # -------------------------
    # SYSTEM HINTS
    # -------------------------
    context += """
SYSTEM HINTS:
- If player threatens someone important → fear OR retaliation
- If player uses leverage → negotiation OR escalation
- If player attacks → casualties + heat spike
- If player manipulates family → emotional + unstable reactions
- If situation is dangerous → DEA or rivals may intervene

RAIDS:
Player may: fight / flee / hide / bribe
"""

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

async def handle_player_decision(guild, p, action):
    world = load_world()
    sanitize_world(world)
    territories = world["territories"]

    city = p["location"]

    if city not in territories:
        return

    if action == "attack":
        dmg = random.randint(10, 30)
        territories[city]["control"] = max(0, territories[city]["control"] - dmg)

        await trigger_scene(guild, p, "ATTACK", f"You strike back (-{dmg} control)")

    elif action == "defend":
        territories[city]["defense"] += 10
        await trigger_scene(guild, p, "DEFENSE", "You reinforce defenses")

    elif action == "negotiate":
        success_chance = 50 

        if p.get("has_leverage"):
            success_chance += 25 

        if random.randint(1,100) < 50:
            await trigger_scene(guild, p, "DEAL", "You avoided conflict")
        else:
            await trigger_scene(guild, p, "FAILED DEAL", "Talks broke down")

    elif action == "retreat":
        territories[city]["control"] = max(0, territories[city]["control"] - 20)
        await trigger_scene(guild, p, "RETREAT", "You pulled back")

async def resolve_raid_action(guild, p, action):
    crew_power = (
        len(p["crew"]) * 3 +
        total_firepower(p) * 5
    )

    for lt in p["hierarchy"].get("lieutenants", []):
        crew_power += lt["skills"]["combat"] * 2

    heat_factor = p["heat"]

    if action == "fight":
        ok, unarmed = check_firepower(p)

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
                f"Your crew lacks {len(unarmed)} weapons. You're severely outgunned."
            )
            enemy_power += len(unarmed) * 2

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
                if not p["crew"]:
                    break

                dead = random.choice(p["crew"])
                p["crew"].remove(dead)
                dead_list.append(dead["name"])

            # 🔫 weapon loss based on casualties
            weapon_loss = len(dead_list) + random.randint(0, len(dead_list))

            loss = weapon_loss

            for tier in ["military", "rifles", "pistols"]:
                if loss <= 0:
                    break

                have = p["weapons"].get(tier, 0)
                take = min(have, loss)

                p["weapons"][tier] -= take
                loss -= take

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

async def rival_reaction_to_leverage(guild, p, world, city):
    boss = world["bosses"].get(city)
    if not boss:
        return

    personality = boss.get("personality", "ruthless")
    reaction_roll = random.randint(1,100)

    # 🔥 reaction types
    if reaction_roll < 30:
        # NEGOTIATE
        await trigger_scene(
            guild,
            p,
            "NEGOTIATION OFFER",
            f"{boss['name']} wants to talk.\n\n"
            "You’re invited to a private meeting.\n\n"
            "Respond: negotiate / threaten / walk away"
        )

    elif reaction_roll < 55:
        # RETALIATION (family risk / counter leverage)
        p["heat"] += 5

        await trigger_scene(
            guild,
            p,
            "RETALIATION",
            f"{boss['name']} is making moves against you.\n\n"
            "Your people may be at risk."
        )

    elif reaction_roll < 80:
        # WAR ESCALATION
        world["territories"][city]["conflict"] = True

        await trigger_scene(
            guild,
            p,
            "ESCALATION",
            f"{boss['name']} refused to bend.\n\n"
            f"{city} is now in open conflict."
        )

    else:
        # FEAR / BACKDOWN
        world["territories"][city]["control"] = max(
            0,
            world["territories"][city]["control"] - 20
        )

        await trigger_scene(
            guild,
            p,
            "FEAR",
            f"{boss['name']} is shaken.\n\n"
            "They’re losing grip on the city."
        )

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

    p = ensure_player(data[uid])
    data[uid] = p

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

    data = load_data()
    uid = str(message.author.id)
    world = load_world()
    sanitize_world(world)

    if uid not in data:
        return

    p = ensure_player(data[uid])
    data[uid] = p

    if "last_msg" in p and time.time() - p["last_msg"] < 1:
        return
    p["last_msg"] = time.time()

    state = p.get("state")

    if state:

        state_type = state.get("type")
        stage = state.get("stage", 1)
        text = message.content.lower()

        # =========================
        # RAID SYSTEM
        # =========================
        if state_type in ["raid", "dea_raid"]:

            if stage == 1:

                if "fight" in text:
                    await resolve_raid_action(message.guild, p, "fight")
                    p["state"]["stage"] = 2

                    await message.channel.send("More agents are arriving. Fight again or flee?")
                    save_data(data)
                    return

                elif "flee" in text:
                    await resolve_raid_action(message.guild, p, "flee")
                    clear_state(p)
                    save_data(data)
                    return

                elif "hide" in text:
                    await resolve_raid_action(message.guild, p, "hide")
                    clear_state(p)
                    save_data(data)
                    return

                elif "bribe" in text:
                    await resolve_raid_action(message.guild, p, "bribe")
                    clear_state(p)
                    save_data(data)
                    return

            elif stage == 2:

                if "fight" in text:
                    await resolve_raid_action(message.guild, p, "fight")

                    clear_state(p)

                    await message.channel.send("You survived the raid.")
                    save_data(data)
                    return

                elif "flee" in text:
                    await resolve_raid_action(message.guild, p, "flee")

                    clear_state(p)
                    save_data(data)
                    return

    scene = p.get("active_scene", {})
    scene_npcs = scene.get("npcs", [])

    npc = p.get("npc_relations", {}).get("active")

    if npc:
        update_npc_memory(p, npc["name"], message.content)

    if npc and "join me" in message.content.lower():
        await message.channel.send(f"{npc['name']} joins your cartel.")

    # allow commands
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # only run in threads (RP scenes)
    if not isinstance(message.channel, discord.Thread):
        return

    if uid not in data:
        return

    p = ensure_player(data[uid])
    data[uid] = p

    if p["partner"]:
        update_npc_memory(p, p["partner"]["name"], message.content)

    # generate AI response
    import time  # (put this at top of file if not already)

    if "last_ai" not in p or time.time() - p["last_ai"] > 2:
        try:
            reply = await generate_ai_response(p, message.content)
        except Exception as e:
            print("AI ERROR:", e)
            reply = "Something feels off… the situation is tense."
        p["last_ai"] = time.time()
    else:
        reply = "..."

    # detect active NPC (simple version: underboss first)
    ub = p["hierarchy"].get("underboss")

    if ub:
        update_npc_memory(p, ub["name"], message.content)

    update_memory(p, message.content, reply)

    text = message.content.lower()

    # 🎯 PLAYER DECISION SYSTEM
    if any(w in text for w in ["attack", "hit"]):
        await handle_player_decision(message.guild, p, "attack")

    elif any(w in text for w in ["defend", "hold"]):
        await handle_player_decision(message.guild, p, "defend")

    elif any(w in text for w in ["negotiate", "deal"]):
        await handle_player_decision(message.guild, p, "negotiate")

    elif any(w in text for w in ["retreat", "run"]):
        await handle_player_decision(message.guild, p, "retreat")

    # 🎯 RAID-SPECIFIC ACTIONS
    elif "flee" in text:
        await resolve_raid_action(message.guild, p, "flee")

    elif "bribe" in text:
        await resolve_raid_action(message.guild, p, "bribe")

    elif "hide" in text:
        await resolve_raid_action(message.guild, p, "hide")

    # apply effects
    effects = parse_effects(reply)
    apply_effects(p, world, effects)
    save_world(world)

    # save
    save_data(data)

    # send response
    await message.channel.send(reply)
    await message.channel.send("👉 What do you do next?")

    # auto-end scene after response (for now)
    if p.get("state") and p["state"]["stage"] > p["state"]["max_stage"]:
        clear_state(p)

    save_data(data)

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

    # 🔥 RIVALRY EFFECT
    for rival_name in npc.get("relationships", {}).get("rivals", []):
        for other in p.get("crew", []):
            if other["name"] == rival_name:

                if other["loyalty"] > 60:
                    npc["loyalty"] -= 2


def check_collapse(p):

    if p["cash"] <= 0 and p["bank"] <= 0 and p["inventory"]["low"] == 0 and p["inventory"]["pure"] == 0 and p["inventory"]["high"] == 0:
        p["rank"] = "Collapsed"
        return True

    return False

def rivalry_sabotage(p):
    events = []

    for npc in p.get("crew", []):

        rivals = npc.get("relationships", {}).get("rivals", [])

        if not rivals:
            continue

        if random.randint(1,100) < 15:

            target_name = random.choice(rivals)

            # 🔥 sabotage effect
            loss = random.randint(3, 10)
            p["inventory"]["low"] = max(0, p["inventory"]["low"] - loss)

            events.append(f"⚠️ Internal conflict disrupted operations (-{loss})")

    return events

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

async def random_event(guild, p):
    roll = random.randint(1,100)

    if roll > 25:
        return

    event_type = random.choice([
        "phone_call",
        "street_encounter",
        "business_opportunity",
        "relationship"
    ])

    channel = discord.utils.get(guild.text_channels, name="rp")

    if event_type == "phone_call":
        await channel.send("📞 Your phone is ringing…")

    elif event_type == "street_encounter":
        await channel.send("👤 Someone approaches you on the street…")

    elif event_type == "business_opportunity":
        await channel.send("💼 A potential deal is available.")

    elif event_type == "relationship":
        await channel.send("❤️ You meet someone interesting.")


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
        sanitize_world(world)
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

        await send_news(
            guild,
            "A cartel insider has reportedly betrayed their organization.",
            world,
            p
        )

        save_world(world)
                
def escalate_war(p):
    if random.randint(1,100) < 20:
        p["war_stage"] += 1

async def war_event(guild, p):
    phase = p.get("war_phase", "calm")

    if phase == "tension":
        await trigger_scene(guild, p, "Tension Rising", "Rival cartels are watching your moves.")

    elif phase == "conflict":
        await trigger_scene(guild, p, "Conflict", "Your cartel is clashing with rivals.")

    elif phase == "war":
        await trigger_scene(guild, p, "FULL WAR", "All-out war has erupted across territories.")

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

    # NEW corruption reduction
    chance -= p.get("corruption", 0) * 2

    # clamp
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
    identity = p.get("identity", "balanced")

    if identity == "aggressive":
        p["heat"] += 1
        p["reputation"] += 1

    elif identity == "stealth":
        p["heat"] = max(0, p["heat"] - 2)

    elif identity == "business":
        p["bank"] += 500

    if p["stress"] > 80:
        p["heat"] += 2

    if style == "aggressive":
        p["heat"] += 2

    elif style == "diplomatic":
        p["heat"] = max(0, p["heat"] - 2)

    elif style == "loyal":
        # boost crew loyalty slightly
        for npc in p["hierarchy"].get("lieutenants", []):
            npc["loyalty"] = min(100, npc["loyalty"] + 1)

def check_firepower(p):
    crew = p["crew"]

    if not crew:
        return True, []

    firepower = total_firepower(p)

    if firepower >= len(crew):
        return True, []

    deficit = len(crew) - firepower
    unarmed = random.sample(crew, min(deficit, len(crew)))

    return False, unarmed

# =========================
# BANK SYSTEM
# =========================

@bot.command()
async def deal(ctx, city, *, cartel):
    data = load_data()
    world = load_world()
    sanitize_world(world)

    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    boss = world.get("bosses", {}).get(city)

    if not boss:
        await ctx.send("No boss found for that city.")
        return

    chance = random.randint(1,100) + p["reputation"]

    if chance > boss["power"]:
        p.setdefault("deals", {})
        p["deals"][city] = boss["name"]
        await ctx.send(f"Deal secured with {boss['name']}")
    else:
        await ctx.send(f"{boss['name']} rejected your offer.")

    save_data(data)

@bot.command()
async def promote(ctx, *, name):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    msg = promote_npc(p, name)

    save_data(data)
    await ctx.send(msg)

@bot.command()
async def deposit(ctx, amount: int):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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

def generate_partner(gender=None):

    if gender == "male":
        name = random.choice(MALE_NAMES)
    elif gender == "female":
        name = random.choice(FEMALE_NAMES)
    else:
        name = random.choice(MALE_NAMES + FEMALE_NAMES)

    return {
        "name": name,
        "gender": gender or random.choice(["male","female"]),
        "loyalty": random.randint(50, 90),
        "personality": random.choice(["loyal","flirty","cold","ambitious"])
    }

@bot.command()
async def contract(ctx, city, amount: int):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    p.setdefault("contracts", [])

    p["contracts"].append({
        "city": city,
        "amount": amount,
        "cooldown": 0
    })

    save_data(data)

    await ctx.send(f"Supply contract secured in {city} ({amount}/day)")

@bot.command()
async def preference(ctx, gender):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    if gender not in ["male","female"]:
        await ctx.send("Choose male or female.")
        return

    p["preference"] = gender
    save_data(data)

    await ctx.send(f"Preference set to {gender}")


@bot.command()
async def date_accept(ctx):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    candidate = p["npc_relations"].get("candidate")

    if not candidate:
        await ctx.send("No one to accept.")
        return

    p["partner"] = candidate
    del p["npc_relations"]["candidate"]

    save_data(data)

    await ctx.send(f"You are now with {candidate['name']}")


@bot.command()
async def kid(ctx, name=None):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    if not p["partner"]:
        await ctx.send("No partner.")
        return

    if random.randint(1,100) < 50:

        child_name = name or random.choice(MALE_NAMES + FEMALE_NAMES)

        child = {
            "name": child_name,
            "age": 0
        }

        p["kids"].append(child)

        await ctx.send(f"You had a child: {child_name}")
    else:
        await ctx.send("No child this time.")

    save_data(data)


# =========================
# CREW / ASSETS
# =========================

@bot.command()
async def hire(ctx, role):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    required = len(p["crew"]) + 1
    if total_firepower(p) < required:
        await ctx.send("You need more weapons before hiring more crew.")
        return

    npc = generate_npc(role)

    npc["assigned_city"] = None

    p["crew"].append(npc)

    # 🔥 ADD THIS
    generate_rivalries(p)

    save_data(data)

    await ctx.send(f"Hired {role}")

@bot.command()
async def assign(ctx, role, *, city):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    for c in p["crew"]:
        if c["role"] == role and c["assigned_city"] is None:
            c["assigned_city"] = city
            await ctx.send(f"{role} assigned to {city}")
            save_data(data)
            return

@bot.command()
async def buyguns(ctx, tier, amount: int):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    costs = {
        "pistols": 800,
        "rifles": 2000,
        "military": 5000
    }

    if tier not in costs:
        await ctx.send("Choose pistols, rifles, military")
        return

    cost = costs[tier] * amount

    if p["cash"] < cost:
        await ctx.send("Not enough cash.")
        return

    p["cash"] -= cost
    p.setdefault("weapons", {})
    p["weapons"][tier] = p["weapons"].get(tier, 0) + amount

    save_data(data)

    await ctx.send(f"Bought {amount} {tier}")

@bot.command()
async def warehouse(ctx):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    cost = 5000

    if p["cash"] < cost:
        await ctx.send("Not enough money.")
        return

    p["cash"] -= cost
    p["assets"]["warehouse"] += 1
    p["max_storage"] += 100

    save_data(data)

    await ctx.send("Warehouse built.")


@bot.command()
async def lab(ctx):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    sanitize_world(world)

    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    territories = world["territories"]

    if city not in territories:
        await ctx.send("Invalid city.")
        return

    strength = (
        len(p["crew"]) * 4 +
        total_firepower(p) * 5 +
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

        owner_name = p.get("cartel") or p.get("name")
        title = get_notoriety_title(p)
        display = get_display_name(p)

        headline = random.choice([
            f"{city} has fallen to {title}.",
            f"{display} expands operations into {city}.",
            f"A violent takeover in {city} is linked to {title}.",
            f"{city} is now under control of {display}.",
        ])

        # 🔥 callback (past news reference)
        callback = get_news_callback(p)
        if callback:
            headline += " " + callback

        # 🧠 store history
        record_news(p, headline)

        # 📰 send it
        await send_news(ctx.guild, headline, world, p)
    else:
        loss = random.randint(2000, 6000)
        p["cash"] = max(0, p["cash"] - loss)

        title = get_notoriety_title(p)
        display = get_display_name(p)

        headline = random.choice([
            f"A failed takeover attempt in {city} has been reported.",
            f"{display} attempted to seize {city} but was pushed back.",
            f"Authorities report a violent but unsuccessful attack in {city}.",
        ])

        callback = get_news_callback(p)
        if callback:
            headline += " " + callback

        record_news(p, headline)

        await send_news(ctx.guild, headline, world, p)
        

    save_data(data)
    save_world(world)


# =========================
# TRAVEL SYSTEM
# =========================

@bot.command()
async def travel(ctx, *, city):
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    sanitize_world(world)

    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return
    
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
    data = load_data()
    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

    msg = f"Cartel: {p.get('cartel')}\n"

    if p["hierarchy"].get("underboss"):
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
    sanitize_world(world)

    p, uid = get_player(ctx, data)

    if not p:
        await ctx.send("Use !start first.")
        return

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
    embed.add_field(name="Firepower", value=total_firepower(p))
    embed.add_field(
        name="Defense",
        value="\n".join(
            f"{city}: {t.get('defense', 0)}"
            for city, t in territories.items()
        ),
        inline=False
    )

    crew_info = "\n".join(
        f"{c['name']} ({c['role']}) → {c.get('assigned_city','Unassigned')}"
        for c in p["crew"]
    )

    embed.add_field(name="Crew", value=crew_info or "None", inline=False)

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

    # 🌎 global systems
    world_war_tick(world)
    
    update_president(world)

    events = cartel_vs_cartel(world)

    for e in events:
        # send to news channel later if you want
        pass
    
    for j in world.get("media", {}).get("journalists", []):
        if not j["alive"]:
            continue

        if j["style"] == "investigative":
            p["heat"] += 1

        if random.randint(1,100) < 30:
            j["focus"] = p.get("cartel")

            # optional: generate targeted news
            if random.randint(1,100) < 20:
                headline = f"Journalist {j['name']} is investigating {p.get('cartel')}."

                await send_news(guild, headline, world, p)

    for i, j in enumerate(world["media"]["journalists"]):
        if not j["alive"]:
            if random.randint(1,100) < 50:
                world["media"]["journalists"][i] = generate_journalist()

    for k in world["market"]:
        world["market"][k] += random.randint(-20, 20)
        world["market"][k] = max(50, world["market"][k])

    for city, econ in world.get("economy", {}).items():
        econ["saturation"] = max(0, econ["saturation"] - random.randint(1, 5))
        econ["demand"] += random.randint(-5, 5)
        econ["demand"] = max(50, min(150, econ["demand"]))

    for agent in world["dea_agents"]:
        if random.randint(1,100) < 25:
            news = generate_case_news(agent, p)
            if news:
                await send_news(guild, news, world, p)

    for uid, p in data.items():
        p = ensure_player(p)
        data[uid] = p

        # 🔥 LIGHT PASSIVE PRESSURE
        p["heat"] = min(100, p["heat"] + random.randint(0, 2))
        p["stress"] += random.randint(0, 1)

        # ⛓ prison handling
        if p.get("in_prison"):
            daily_tick(p, world)
            continue

        # 💰 passive income
        if random.randint(1,100) < 50:
            passive_income(p, world)

        # 🏙 territory growth (slow)
        if random.randint(1,100) < 20:
            territory_gain(p, world)

        # 🧪 passive production (light)
        result = produce_cocaine(p)

        # skip silently if not possible
        if result in ["no_lab", "no_supply"]:
            pass

        # 🧠 DEA (passive only)
        update_dea(p)
        update_dea_stage(p)
        dea_passive_effects(p, world)
        update_dea_agents(world, p)
        update_dea_targets(world, p)

        # 🧠 loyalty system
        update_loyalty(p)

        # 🔫 firepower upkeep
        crew_count = len(p["crew"])
        firepower = total_firepower(p)

        if firepower > crew_count:
            excess = firepower - crew_count

            reduce_firepower(p, min(excess, 2))

            upkeep = excess * 100
            p["cash"] = max(0, p["cash"] - upkeep)

        # 🧠 cartel evolution ONLY (no attacks here)
        evolve_cartels(world, p)

    # 🔥 RANDOM WORLD NEWS
    if random.randint(1,100) < 40:
        guild = bot.guilds[0] if bot.guilds else None
        if guild:
            await send_news(guild, world=world, p=None)

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