# Cartel Simulation Discord Bot

A dynamic AI-driven cartel empire simulation. Build your organization, expand territory, manage loyalty, and survive raids while competing against evolving rival cartels.

---

## CORE GAMEPLAY LOOP

buy → produce → smuggle → sell → launder  
→ expand → survive → dominate

---

## FEATURES

### ECONOMY
- !buy <amount> → buy raw supply
- !produce → convert supply into product
- !smuggle → move product (increases heat)
- !sell → sell product (gain cash + reputation)
- !launder → convert dirty cash into clean bank money
- Passive income from businesses
- Location-based profit multipliers

---

### TERRITORY SYSTEM
- !travel <city> → move between locations
- !invade <city> → attempt to capture territory
- !defend <lieutenant> <city> → assign defense
- Territories generate passive income
- Control system (0–100 per city)
- Global war system between cartels

---

### CREW & FIREPOWER
- !hire <role> → recruit crew
- !buyguns <amount> → increase firepower
- Crew requires weapons to function
- Firepower is consumed during actions
- Underpowered crews increase risk

---

### HIERARCHY SYSTEM
- Underboss (automated decisions)
- Lieutenants (city control, betrayal risk)
- Capos (boost profits)

Commands:
- !connections → view hierarchy
- !promote <name> → promote lieutenant to capo

---

### NPC SYSTEM (ADVANCED)
- NPC memory system (remembers interactions)
- Loyalty system (0–100)
- Personality traits (greedy, loyal, paranoid, etc.)
- Skill system:
  - combat
  - business
  - stealth
  - loyalty
- XP + leveling system for NPCs

---

### INTEL & CONTROL
- !intel → scan loyalty status
- !investigate <name> → deeper scan
- !interrogate <name> → force loyalty shift
- !execute <name> → remove NPC
- !replace <role> → recruit new NPC

---

### AI ROLEPLAY SYSTEM
- Dynamic AI-generated responses
- Context-aware world simulation
- Player style adaptation:
  - aggressive
  - diplomatic
  - loyal

Thread-based interaction:
- fight
- flee
- bribe
- hide

AI outputs include hidden effects:
[EFFECT: CASH+X HEAT+X LOW+X PURE+X HIGH+X CREW+X]

---

### DEA / HEAT SYSTEM
- Heat increases from illegal actions
- DEA pressure builds over time
- High DEA → raids + prison
- Community investment reduces detection

---

### RAID SYSTEM
Triggered by heat:
- Fight → risk crew + money
- Flee → gain heat
- Bribe → pay to escape
- Hide → save product

---

### WORLD SYSTEM
- Global cartel AI evolves over time
- Rival cartels adapt strategy:
  - aggressive
  - economic attacks
  - territory war
  - lay low
- Random world events:
  - DEA activity
  - shipment seizures
  - cartel wars
  - instability

---

### BETRAYAL SYSTEM
- Low loyalty → suspicion → warning → betrayal
- Underboss can:
  - steal money
  - destroy territory control
  - remove crew
- Full betrayal removes underboss

---

### FAMILY SYSTEM
- !meet → meet partner
- !date_accept → start relationship
- !kid → have children
- Family creates risk events
- Can increase stress + financial loss

---

### BUSINESS SYSTEM
- !business <type> → create business
- Generates passive income
- Improves laundering success rate

---

### BANK SYSTEM
- !deposit <amount>
- !withdraw <amount>

---

### PROGRESSION
Ranks:
- Street Runner
- Crew Leader
- Plaza Boss
- Cartel Boss
- Kingpin

---

### WIN / LOSS CONDITIONS

WIN:
- Control 3+ territories
- Bank > $50,000

LOSS:
- Lose all cash, bank, and product

- !rebuild → restart after collapse

---

## COMMANDS SUMMARY

START:
- !start
- !cartel <name>
- !actions
- !guide

ECONOMY:
- !buy
- !produce
- !smuggle
- !sell
- !launder

POWER:
- !hire
- !buyguns
- !connections
- !promote

TERRITORY:
- !travel
- !invade
- !defend

INTEL:
- !intel
- !investigate
- !interrogate
- !execute
- !replace

LIFE:
- !meet
- !date_accept
- !kid

FINANCE:
- !deposit
- !withdraw

OTHER:
- !community
- !rebuild

---

## SETUP

1. Clone repo
2. Install dependencies:
   pip install -r requirements.txt

3. Create environment variables:
   DISCORD_TOKEN=your_token
   OPENAI_API_KEY=your_key

4. Run bot:
   python bot.py

---

## NOTES

- Do NOT upload .env to GitHub
- Use Railway or other hosting for 24/7 uptime
- Bot uses JSON for persistent storage
- AI responses drive dynamic gameplay

---

## FUTURE IDEAS

- Multiplayer cartel alliances
- UI dashboard
- Drug pricing market system
- Custom NPC naming
- More cities / map expansion

---

Built for immersive cartel simulation gameplay inside Discord.