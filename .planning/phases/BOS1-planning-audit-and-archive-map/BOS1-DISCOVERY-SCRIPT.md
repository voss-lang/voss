# BOS1 Discovery Interview Script

Mom-Test-style first design-partner interviews for the Voss Behavioral OS (BOS) project. The goal of these conversations is to validate that the problem actually hurts today and to map how delegation decisions are made now — before any wedge is pitched. Interviewers must stay backward-looking and behavior-based: ask what the person did last week / last sprint / on a specific recent task. Never ask "would you use…" or pitch Voss. Save the wedge and willingness-to-pay probes for the end, after the problem is confirmed on the interviewee's own terms.

## Interviewee target

These interviews target engineering managers and engineering leads of small multi-agent engineering teams — teams of roughly 3 to 15 developers that are already running multiple coding agents in their day-to-day work (Claude Code, Codex, Voss, or similar). This is the buyer-side of the ICP defined in the product brief (D-03): the EM/eng-lead is the economic buyer because they own the team-level coordination, review, and validation pain that BOS addresses. They are the person who feels the cost of mis-delegated work, unreviewed agent output, and rework loops across humans and agents.

Within each team we also probe the daily dev users for their current delegation behavior. Devs are the ones actually routing work to agents vs. themselves and reacting to agent output in the loop, so their lived behavior is the ground truth for the delegation wedge. The EM gives us the team-level view (how work is assigned, what signals exist, what goes wrong); the devs give us the in-the-trenches view (what they actually hand off, what they trust, where they get burned). Both perspectives are required — the EM owns the pain economically, the devs own it behaviorally.

A team qualifies for an interview only if they are already running more than one coding agent in production development work. Teams that have "experimented with" a single agent but not adopted do not qualify — the BOS problem only materializes once multiple agents and humans are sharing the workstream.

## Problem validation

All questions in this section are asked before any wedge is surfaced. They are backward-looking and behavior-based: anchor every answer to a specific recent event (last week, last sprint, a named task). If the interviewee drifts hypothetical ("we would…"), redirect to "tell me about the last time that actually happened."

1. Walk me through the last time you had to decide whether a task should go to a coding agent or to a human on your team. What was the task, what triggered the decision, and what did you end up deciding?

2. In the last sprint, what's a task that went to an agent that in hindsight shouldn't have — or one that went to a human that an agent should have handled? How did you find out it was the wrong call, and what did it cost?

3. When you last reviewed a coding agent's output before it merged or shipped, what specific signals did you look at to decide it was good enough? Where did those signals come from, and which ones were you missing?

4. Tell me about the most recent time a coding agent's work caused a problem downstream — a bug, a regression, a rework loop, a broken contract with another team. When did you catch it, and what would have let you catch it earlier?

5. What's the last task you handed to a coding agent where, after it came back, you genuinely weren't sure whether the work was correct? What did you do about that uncertainty — and how long did resolving it take?

6. Walk me through how your team currently tracks who (or which agent) is working on what across humans and agents. Show me the last place you looked to figure out the state of in-flight work. What was easy about it, and what was missing?

### Current decision behavior

These questions probe the delegation decision itself — the wedge surface — but purely descriptively. We are mapping how the decision is made today, not pitching a better way. Ask the EM-version and dev-version of each where both apply.

For the EM / eng-lead:

- When you assigned work last sprint, what determined whether a given task went to a human vs. an agent? What signals did you have in front of you at the moment of assignment, and what signals did you wish you had?
- Of the tasks you assigned to agents last sprint, how did you decide which agent (or which configuration) was the right pick? Walk me through one specific case.
- When a task came back from an agent and needed rework, how did you decide whether to re-route it to a human, send it back to the same agent, or send it to a different agent? What was the tipping factor?

For the dev / daily user:

- When you picked up work last week, walk me through how you decided which parts to do yourself vs. hand to an agent. What was the tipping point for one specific task?
- Think about the last task you handed to an agent and then ended up redoing yourself. What made you take it back, and at what point did you realize the agent's output wasn't usable as-is?
- When you're deciding whether to trust an agent's output without re-checking it line by line, what are you actually relying on? Walk me through the last time you made that call.

Probe for concrete artifacts wherever possible: "Can you show me the last place you recorded that decision?" "Can you pull up the task where that happened?" Real behavior leaves a trail; hypotheticals don't.

## Wedge resonance

Only now — after the problem is confirmed on the interviewee's own terms — may the delegation wedge be surfaced. The wedge is narrow: a recommendation surface that says, for a given task, whether it should go to an agent or a human, and that captures ownership of the task once assigned. This is the V25 server-native swarm assignment flow (task ownership, operator gates, worker completion, audit) expressed as a recommendation — not a review-depth or validation-depth feature. Keep these questions non-leading: do not describe the product, do not ask "would you use it," do not attach a price.

1. If your team had a single place that, for a given task, recommended whether it should go to a coding agent or to a human — and recorded who owns it once assigned — what's the first task from last week you'd want that recommendation on? Walk me through that task.

2. What would have to be true about that recommendation for you to actually act on it instead of going with your gut? What's the bar — a confidence score, a track record, a reason you can inspect?

3. Where in your current flow would that recommendation need to show up for you to even see it? What's the surface — the issue tracker, the agent's own UI, a standup doc, a Slack ping — and why there?

4. If that recommendation existed today but got the call wrong on a task you cared about, what would you want to happen next — override and move on, or feedback in so it gets better? Walk me through the last task where a wrong call would have been expensive.

Do not extend into review-depth ("how should we check agent output?") or validation-depth ("how do we prove the work is correct?") territory. If the interviewee volunteers those, note it and return to delegation.

## Willingness to pay

This section is light and behavior-based. It is not a pricing study — pricing hypotheses are deferred. The goal is to understand budget ownership and buying behavior so a later phase can shape a commercial path. Never ask "would you pay $X."

1. What tools does your team currently pay for that touch the coding-agent workflow directly — agent seats, eval harnesses, agent observability, anything else? Who owns that budget line, and how is it sized?

2. Walk me through the last time your team evaluated and adopted a new developer tool. Who was in the room, what was the deciding factor, and how long did it take from first look to swiped card?

3. Is there a person on your team whose job it is to worry about agent output quality and agent–human coordination, or does that just land on whoever is closest? If that pain had an owner and a budget, whose would it be?

4. When a new tool has gotten purchased for your team in the past year, what was the trigger that turned "interesting" into "bought"? What was the event?

Close by asking if there's anyone else on the team or in their network running multiple coding agents who'd be worth a conversation — but do not turn this into a sourcing discussion. Sourcing is deferred beyond this product-context artifact.
