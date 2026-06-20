# BOS1 Product Brief — Behavioral OS

## Product boundary

The Behavioral OS (BOS) is a **team control plane** over AI-assisted engineering work, not a generic project-management clone (BOS-PROD-01). It is the team-level layer that sits *above* the existing Voss ADE / harness / server / swarm substrate and turns that substrate's already-emitted activity into a shared system of decisions and outcomes. BOS does not replace the runtime; it observes and labels it. The agents keep coding in the Voss ADE, the swarm keeps assigning work through the V25 server-native runtime, and BOS reads those streams to make the *team-level* decisions visible, explainable, and overridable. It is a control plane in the systems sense: it tells the substrate what the team decided, and it records what happened as a result.

This boundary is deliberately narrow. BOS is not a runtime, not an agent harness, not a new editor, and not a full PM suite — those exist already and replacing them is explicitly out of scope for v0.2 (PROJECT.md). It is the orchestration and labeling layer that makes the agent-driven work the team is *already doing* legible to the team itself and to the engineering lead.

## Ideal customer and first beachhead

The ideal customer profile is **small multi-agent engineering teams of 3-15 devs** who are already running multiple coding agents — Claude Code, Codex, and/or Voss — as part of their normal flow (BOS-PROD-03, D-01). These teams qualify for two compounding reasons. First, they feel real coordination pain: who delegated what to which agent, which task is owned by a human versus a swarm, and what the review/validation posture of a given unit of work actually is. Second, and more importantly, they already generate the ADE/swarm events that BOS needs to observe. BOS does not have to instrument a new surface to learn about them; their daily work is the training signal.

The rejected alternatives sharpen the wedge (per D-01). The **solo power-user** is the wrong first beachhead because a single developer running agents generates plenty of activity but almost no *team-level* coordination load; there is weak pull for a control plane when there is no team to control. The **devex/platform team at a scale-up** looks attractive on paper — budget, mandate, scale — but the buying cycle is long, the integration surface is wide, and the observability wedge is weaker because platform teams want telemetry and aggregation before they want decision support. BOS's wedge is decision observability, not telemetry aggregation, so the platform-team motion asks BOS to be the wrong product first. The 3-15-dev multi-agent team is the beachhead where the pain and the signal coincide.

## Buyer and user split

The economic buyer is the **EM / engineering lead**; the daily users are the **developers** on the team (BOS-PROD-03, D-03). This split is not a footnote — it defines how the product is sold, how it is configured, and what it is allowed to report. The EM buys because BOS gives them a team-level view of decisions and outcomes that today is invisible when agents are doing the work. The devs use it because it makes their own delegations, ownership, and review posture legible to themselves and their teammates — not because it ranks them. Everything downstream of this split (defaults, reporting, anti-positioning) follows from the fact that the person paying and the people using are different roles with different stakes.

## The wedge: delegation

The first recommendation surface is **delegation — task to agent or human** (BOS-PROD-02, D-02). Delegation is the chosen entry point because it is already modeled in the V25 server-native swarm assignment flow: `swarm.assign`, task ownership, operator gates, worker completion, and the audit files the swarm runtime already emits. Of all the decision surfaces BOS could recommend on, delegation is the most directly observable today — the substrate is already producing the events, so the wedge is a label and recommendation layer over an existing stream, not a new instrumentation project.

Review-depth and validation-depth are explicitly **later** wedges and are out of scope for the first product wedge. Review-depth needs review-outcome data that the substrate does not yet emit with enough structure; validation-depth depends on CI and validation ingestion that lands later in the BOS track. BOS1 locks the delegation wedge only. Widening the recommendation surface prematurely would require inventing event sources, and the whole point of the wedge is that the signal already exists.

## Positioning

With design partners, the external category is **"control plane for AI engineering teams."** That phrase is the thing we say out loud: it is accurate, it is defensible, and it does not require the partner to buy into a new vocabulary (D-05). The internal, north-star term is **Behavioral OS** — used inside the team and in planning, not as a market-facing label. "Behavioral OS" names where the product is heading: a shared operating layer for how an AI-assisted engineering team actually behaves, decides, and learns. It is not the external category, because "OS" language invites premature scope arguments with partners who reasonably want to know what the v0 product does, not what it aspires to be.

## Anti-positioning

BOS is **not** a Jira / Linear / Atlassian PM clone (BOS-PROD-01, D-06). It does not replace those tools in v0.2; PROJECT.md is explicit that defining the path to coexistence is in scope, but building a full PM suite is not. BOS reads the agent/swarm substrate and recommends team-level decisions; it does not aspire to be the system of record for tickets, sprints, or roadmaps.

BOS is **not** individual-developer surveillance, ranking, or productivity leaderboards. This is not a feature we have chosen to omit — it is an incompatibility with the trust model. PROJECT.md's out-of-scope list names exactly these: individual-developer rankings, raw activity scoring, keystroke telemetry, and productivity leaderboards are out of scope because they are *incompatible with the trust model*. Team-level defaults, explainable recommendations, human override, and auditability are non-negotiable; anything that turns the control plane into a surveillance plane breaks the trust contract that lets the daily users (developers) actually keep using the substrate BOS observes. The EM gets a team-level view; the developer never gets scored as an individual.

## Core tension and resolution

The core tension is structural: a **top-down EM buyer** paired with a **dev-generated data substrate** (D-04). The person paying wants team-level visibility; the data that would produce that visibility is produced, one event at a time, by the developers doing the work. In most tools this tension is resolved by asking the devs to behave differently — log more, fill out more fields, accept more telemetry — which is exactly the motion that erodes trust and adoption.

BOS resolves it differently. The team is **already** on the Voss ADE and swarm runtime for their agent work; that is the existing product, not a new ask. The EM buys BOS as the team-level control plane over data the devs **already generate** by doing their normal work. No new dev behavior is required for the wedge to land: the swarm still assigns, the agents still complete, the audit files still get written, and BOS labels and recommends on top of that existing stream. The buyer and the users are different people, but the buyer's value and the users' effort are not in conflict — the users do not have to do anything they were not already doing. That is what makes the 3-15-dev multi-agent team a real beachhead rather than a wish, and it is what makes delegation, not a broader recommendation surface, the right first wedge.
