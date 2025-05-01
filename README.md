![alt text](docs/assets/banner.png)

AI-Powered Reflections for Human Decisions
Ask the council. Reflect with ducks. Make better choices.

## What is Duck Council?

Duck Council is a quirky, AI-driven decision evaluator where you describe a real-life situation and your intended action—and a council of AI duck agents evaluates how suitable that action is.

#### Each duck provides:

- A suitability score (0–100)
- A personal reflection based on its own reasoning style
- A perspective like logic, ethics, emotion, or risk-taking

## But Why?

Humans are emotional. Decisions are messy.
But what if you had a council of intelligent ducks to reflect back your choices?

## Inspired by:

- [Rubber duck debugging](https://rubberduckdebugging.com)
- Inner committee therapy
- Thought experiments & moral dilemmas

This project combines LLMs + agent collaboration to simulate multi-perspective reasoning.

🔧 Tech Stack

| Layer | Tools |
|-----|-----|
|Backend|CrewAI, Flask|
|LLM|OpenAI or other compatible providers|
|Frontend |React / Tailwind |

## 🦆 The Ducks (Starter Pack)

|Duck Name|	Role|	Style of Reasoning|
|-----|-----|----|
|Lawyer Duck|	Focuses on legal feasibility|	“The law is the ultimate word.”|
|Witch Duck|	Quite and A-social. Expert in arcane. |	“Why am i even here? But since you asked ...”|
|Doctor Duck|	Cautious. Values health and well-being|	“Is this the right thing to do?”|
|Rich Duck|	Risk taker. Bold like a true leader|	“Fortune favors the brave!”|
|Gamer Duck|	Treats everything as a competition or a game|	“How can I get the best possible outcome?”|
|Gangsta Duck|	Punk straight outta the hood|	“Solutions to my problems are my homies”|
|Serial Killer Duck| Nice and accomodating. Has murderous tendencies. *Average Genocide Jack*|	“I just looove it when I slice up a manly hunk.”|
|Diplomat Duck|	Great negotiator. Wishes for everyones' well-being|	“How can I establish a profitable deal?”|
|Techno Duck|	Expert in tech. Typical geek. Can probably hack you|	“The solutions I deal with, are computer apps.”|
|King Duck|	Wise and dedicated. Treats everyone equally|	“By the power vested in me, I shall lay bare my wisdom for you aid"|
|Spiritual-Medium Duck|	Possessed by a latin-speaking demon|	Fiat voluntas daemonis... He says the path is cursed, child. Turn back before the sun weeps.  ”|
|Detective Duck| Focuses on logical feasibility|	“This makes sense. It is probable given the situation.”|
|Rebel Duck|	Rebelious. Prioritizes feelings & empathy|	"Empathy is stronger than rules”|

## 🚀 How It Works

1. You submit a scenario
2. Situation: “I have a final exam tomorrow.”
3. Intended action: “I'm going to binge-watch Netflix.”

Each duck reflects

- Lawyer Duck: “Not practical. 20/100.”
- Gamer Duck: “You probably need the break, but...”
- Rich Duck: “YOLO? 65/100.”
- Doctor Duck: “You owe it to your future self.”

You get a council verdict
→ A mix of scores, reflections, and wisdom from your feathered advisors.

## 🛠️ Setup (Backend)

Prerequisites:
- you need `crewai` installed

Copy `duck_council/.env.example` to `duck_council/.env` and populate the variables

You need to install crew.ai CLI to your environment

```bash
cd ./duck_council/src/duck_council/

# install crew.ai dependencies
crewai install
```

Then install dependencies for Flask

```bash
# Install dependencies
uv pip install -r requirements.txt
```

Your API is now ready to run

```bash
# Run API
uvicorn app.main:app --reload
```

## 🛠️ Setup (Frontend)

Copy `client/.env.example` to `client/.env` and populate the variables

Install dependencies

```bash
cd ./client/

pnpm install
```

Run you client

```bash
pnpm run dev
```