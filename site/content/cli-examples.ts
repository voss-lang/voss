export type CliExample = {
  id: string;
  label: string;
  blurb: string;
  command: string;
  code: string;
  lang: "python";
};

export const cliExamples: CliExample[] = [
  {
    id: "classify",
    label: "Classify",
    blurb: "Confidence-gated intent classification.",
    command: "voss run samples/classify.voss",
    lang: "python",
    code: `fn classifyIntent(input: string) -> string {
    let intent: probable<string> = ask("Classify the intent: " + input)

    if intent @ p >= 0.80 {
        return intent.value
    } else {
        return "unknown"
    }
}`,
  },
  {
    id: "support",
    label: "Support",
    blurb: "Semantic routing for a support inbox.",
    command: "voss run samples/support.voss",
    lang: "python",
    code: `prompt SupportAgent {
    "You are a customer support agent for a SaaS product."
}

let tickets: memory.episodic(capacity: 50 turns)

fn handleMessage(userMessage: string) -> string {
    tickets.add(userMessage, role: "user")
    match userMessage {
        case similar("refund, money back, cancel subscription") => {
            return refundFlow(userMessage)
        }
        case _ => {
            ctx(budget: 3000 tokens) {
                include tickets.last(6)
                yield ask(userMessage)
            }
        }
    }
}`,
  },
  {
    id: "research",
    label: "Research",
    blurb: "Parallel agents with timeout and graceful fallback.",
    command: "voss run samples/research.voss",
    lang: "python",
    code: `agent Researcher(topic: string) -> string {
    system: "You are a research analyst."

    ctx(budget: 2000 tokens) {
        yield ask("Summarize key findings on: " + topic)
    }
}

fn runResearch(company: string) -> string {
    let topics = [company + " market", company + " news"]
    let researchers = topics.map(t => spawn Researcher(t))
    let reports: list<string> = gather(researchers, timeout: 60s)

    within budget(tokens: 5000, latency: 10s) {
        return reports.join("\\n---\\n")
    } fallback {
        return reports[0]
    }
}`,
  },
];
