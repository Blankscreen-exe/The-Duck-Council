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
|Backend|CrewAI, FastAPI|
|LLM|OpenAI or other compatible providers|
|Frontend |React / Tailwind |

## 🦆 The Ducks

|Duck Name|	Role|	Style of Reasoning|
|-----|-----|----|
|Pragmatic Duck|	Focuses on logical feasibility|	“This makes sense. It's efficient.”|
|Emo Duck|	Prioritizes feelings & empathy|	“How would this make people feel?”|
|Ethical Duck|	Values morality & fairness|	“Is this the right thing to do?”|
|Risky Duck|	Loves bold choices and chances|	“Fortune favors the brave!”|
|Wise Duck|	Thinks long-term & big-picture|	“Will this matter in five years?”|

## 🚀 How It Works

1. You submit a scenario
2. Situation: “I have a final exam tomorrow.”
3. Intended action: “I'm going to binge-watch Netflix.”

Each duck reflects

- Pragmatic Duck: “Not practical. 20/100.”
- Emo Duck: “You probably need the break, but...”
- Risky Duck: “YOLO? 65/100.”
- Ethical Duck: “You owe it to your future self.”

You get a council verdict
→ A mix of scores, reflections, and wisdom from your feathered advisors.

## 🛠️ Setup

```bash
# Install dependencies
uv pip install -r requirements.txt

# Run API
uvicorn app.main:app --reload
```

## 🧪 Example Request

```json
POST /evaluate/
{
  "situation": "My boss just emailed me on a Saturday.",
  "intended_action": "I'm going to reply immediately."
}
```