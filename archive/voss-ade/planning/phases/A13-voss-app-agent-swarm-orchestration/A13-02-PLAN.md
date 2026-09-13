---
phase: A13-voss-app-agent-swarm-orchestration
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/package.json
  - apps/voss-app/src/swarm/coordinator.ts
  - apps/voss-app/src/swarm/resultParser.ts
  - apps/voss-app/src/swarm/__tests__/coordinator.test.ts
  - apps/voss-app/src/swarm/__tests__/resultParser.test.ts
autonomous: true
requirements:
  - SWM-02
  - SWM-07

must_haves:
  truths:
    - "Coordinator can decompose a natural language goal into 2-6 subtasks via single Anthropic API call"
    - "Each subtask includes agent CLI choice, goal description, and file scope boundaries"
    - "Result files with YAML frontmatter can be parsed into structured objects"
    - "Fan-in synthesis concatenates result summaries into a human-readable summary"
  artifacts:
    - path: "apps/voss-app/src/swarm/coordinator.ts"
      provides: "coordinatorDecompose(goal, repoTree, claudeMd, apiKey) and synthesizeResults(results) functions"
      exports: ["coordinatorDecompose", "synthesizeResults"]
    - path: "apps/voss-app/src/swarm/resultParser.ts"
      provides: "parseResultFile(content) function that extracts YAML frontmatter + markdown body"
      exports: ["parseResultFile"]
    - path: "apps/voss-app/src/swarm/__tests__/coordinator.test.ts"
      provides: "Unit tests for coordinator decomposition and synthesis"
    - path: "apps/voss-app/src/swarm/__tests__/resultParser.test.ts"
      provides: "Unit tests for result file parsing"
  key_links:
    - from: "apps/voss-app/src/swarm/coordinator.ts"
      to: "@anthropic-ai/sdk"
      via: "import Anthropic from '@anthropic-ai/sdk'"
      pattern: "new Anthropic"
    - from: "apps/voss-app/src/swarm/resultParser.ts"
      to: "gray-matter"
      via: "import matter from 'gray-matter'"
      pattern: "matter\\("
---

<objective>
Install npm dependencies and build the coordinator LLM decomposition module and result file parser.

Purpose: Per D-03/D-17, the coordinator is a single Opus LLM call that decomposes a user goal into 2-6 parallel subtasks. Per D-06, result files use YAML frontmatter. Per SWM-07, results are synthesized into a summary. This plan delivers both the decomposition and synthesis logic with full unit tests.

Output: coordinator.ts (LLM decompose + synthesize), resultParser.ts (gray-matter frontmatter parsing), unit tests, npm deps installed.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-RESEARCH.md

<interfaces>
<!-- Key types from Plan 01 (parallel — may not exist yet; define locally or import if available) -->

SubTask type shape (from swarmTypes.ts, created by Plan 01 in parallel):
  id: string (e.g. "agent-1")
  cli: string (e.g. "claude")
  goal: string
  fileScope: string[]
  excludeScope: string[]

ResultFileParsed type shape (from swarmTypes.ts):
  agentId: string
  status: "complete" | "error"
  filesModified: string[]
  durationSecs: number | null
  summary: string

Note: Since Plan 01 and Plan 02 run in Wave 1 (parallel), the executor should
check if swarmTypes.ts exists. If it does, import from it. If not, define the
SubTask and ResultFileParsed types inline in coordinator.ts and resultParser.ts
with a TODO comment to re-export from swarmTypes.ts once Plan 01 completes.
The types MUST match the shapes above exactly.

From apps/voss-app/src/pane/pty-ipc.ts:
  AgentConfig { cliBinary: string; cliArgs: string[]; sessionId?: string; }

From @anthropic-ai/sdk (RESEARCH Pattern 1):
  import Anthropic from '@anthropic-ai/sdk';
  const client = new Anthropic({ apiKey: '...' });
  const msg = await client.messages.create({
    model: 'claude-opus-4-5-20250514',
    max_tokens: 2048,
    messages: [{ role: 'user', content: '...' }],
  });
  msg.content[0].type === 'text' ? msg.content[0].text : ''

From gray-matter:
  import matter from 'gray-matter';
  const { data, content } = matter(rawString);
  // data = parsed YAML frontmatter object
  // content = markdown body after frontmatter
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Install @anthropic-ai/sdk and gray-matter, create coordinator and result parser with tests</name>
  <files>apps/voss-app/package.json, apps/voss-app/src/swarm/coordinator.ts, apps/voss-app/src/swarm/resultParser.ts, apps/voss-app/src/swarm/__tests__/coordinator.test.ts, apps/voss-app/src/swarm/__tests__/resultParser.test.ts</files>
  <read_first>
    apps/voss-app/package.json (current deps)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-RESEARCH.md (Pattern 1: Coordinator Prompt Design, Pitfall 6: API key, Don't Hand-Roll section, Assumptions Log A1 model ID)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md (D-03, D-11, D-16, D-17, D-18)
    apps/voss-app/src/swarm/swarmTypes.ts (if exists from Plan 01; if not, define types inline)
  </read_first>
  <action>
    A. Install deps: Run "cd apps/voss-app && npm install @anthropic-ai/sdk gray-matter" and "npm install -D @types/gray-matter" (if types package exists; gray-matter ships its own types so this may not be needed — check after install).

    B. Create apps/voss-app/src/swarm/coordinator.ts:
       - Import Anthropic from "@anthropic-ai/sdk"
       - Import SubTask type from ./swarmTypes (or define inline if Plan 01 has not run yet)
       - Export async function coordinatorDecompose(goal: string, repoTree: string, claudeMd: string, apiKey: string): Promise of SubTask array
         - Create Anthropic client with explicit apiKey parameter (per Pitfall 6 — do NOT rely on process.env)
         - Call client.messages.create with model "claude-opus-4-5-20250514" (per RESEARCH A1 — use full dated model ID for stability)
         - max_tokens: 4096
         - System prompt: "You are a coordinator for a parallel agent swarm. You decompose goals into 2-6 independent subtasks for CLI AI agents."
         - User message: includes the goal, claudeMd content (per D-11), repoTree (per D-17), and instructs the model to respond with ONLY a JSON array matching the SubTask shape (per D-16, D-18)
         - Parse the text response as JSON. If JSON.parse fails, throw with a descriptive error including the raw text (first 200 chars)
         - Validate the parsed array: must be array, length 2-6, each item has id/cli/goal/fileScope/excludeScope. If validation fails, throw descriptive error.
         - Return the validated SubTask array

       - Export function synthesizeResults(goal: string, results: Array of {agentId: string, summary: string}): string
         - Build a markdown string: "## Swarm Summary\n\nGoal: {goal}\n\n" then for each result: "### {agentId}\n{summary}\n\n"
         - This is concatenation-based per RESEARCH Open Question 3 recommendation (no second LLM call)
         - Return the markdown string

       - Export function buildTaskFileContent(swarmId: string, agentId: string, cli: string, goal: string, fileScope: string array, excludeScope: string array): string
         - Build the markdown task file content per D-05 format from CONTEXT.md File Protocol section
         - YAML frontmatter with swarm, agent, cli fields
         - Body sections: "## Your Task" with goal, "## File Scope" with modify/exclude lists, "## Shared Context" pointing to .voss/swarm/shared/context.md, "## When Done" instructing to write results to .voss/swarm/results/{agentId}.result.md

    C. Create apps/voss-app/src/swarm/resultParser.ts:
       - Import matter from "gray-matter"
       - Import ResultFileParsed from ./swarmTypes (or define inline)
       - Export function parseResultFile(raw: string): ResultFileParsed
         - Use matter(raw) to extract frontmatter data and content body
         - Extract from data: agentId = data.agent (string), status = data.status (default "complete"), filesModified = data.files_modified (default empty array), durationSecs = data.duration_secs (default null)
         - summary = content.trim()
         - Return the ResultFileParsed object
         - If matter throws, return a fallback with status "error", empty filesModified, summary = raw.slice(0, 500)

    D. Create apps/voss-app/src/swarm/__tests__/coordinator.test.ts:
       - Test coordinatorDecompose: mock the Anthropic SDK (vi.mock("@anthropic-ai/sdk")) to return a valid JSON array of 3 subtasks. Verify the function returns parsed SubTask array with correct fields.
       - Test coordinatorDecompose error: mock Anthropic to return non-JSON text. Verify it throws with descriptive error.
       - Test coordinatorDecompose validation: mock Anthropic to return JSON with missing fields. Verify it throws.
       - Test synthesizeResults: call with 2 results, verify output contains goal, both agent IDs, both summaries in markdown format.
       - Test buildTaskFileContent: call with known args, verify output contains YAML frontmatter with correct fields and all body sections.

    E. Create apps/voss-app/src/swarm/__tests__/resultParser.test.ts:
       - Test parseResultFile with valid frontmatter + summary body. Verify all fields extracted correctly.
       - Test parseResultFile with status "error". Verify status field.
       - Test parseResultFile with missing optional fields (duration_secs, files_modified). Verify defaults.
       - Test parseResultFile with invalid/no frontmatter. Verify fallback behavior.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/swarm/__tests__/coordinator.test.ts src/swarm/__tests__/resultParser.test.ts --reporter=verbose 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - @anthropic-ai/sdk and gray-matter appear in apps/voss-app/package.json dependencies
    - coordinator.ts exports coordinatorDecompose, synthesizeResults, buildTaskFileContent
    - resultParser.ts exports parseResultFile
    - coordinatorDecompose uses explicit apiKey parameter (not process.env)
    - coordinatorDecompose uses model ID "claude-opus-4-5-20250514"
    - buildTaskFileContent produces markdown with YAML frontmatter matching D-05 format
    - parseResultFile handles valid frontmatter, missing fields, and invalid input gracefully
    - All unit tests pass
    - tsc --noEmit passes
  </acceptance_criteria>
  <done>Coordinator decomposition + synthesis + task file builder + result parser all implemented and tested. npm deps installed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Webview JS -> api.anthropic.com | HTTPS call with API key |
| LLM output -> JSON.parse | Untrusted LLM text parsed as JSON |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A13-04 | Information Disclosure | coordinatorDecompose apiKey | mitigate | Key passed as parameter, never stored in module state, never logged; Anthropic SDK handles HTTPS transport |
| T-A13-05 | Tampering | coordinatorDecompose JSON parse | mitigate | Validate parsed JSON: must be array, length 2-6, each item has required string fields; reject malformed output with descriptive error |
| T-A13-06 | Tampering | LLM-returned fileScope paths | mitigate | fileScope is used only in task file markdown (instruction text for agents); no filesystem operations use these paths directly in this module |
| T-A13-SC | Tampering | npm installs | mitigate | @anthropic-ai/sdk [VERIFIED: official Anthropic repo], gray-matter [VERIFIED: 11yr npm history] per RESEARCH Package Legitimacy Audit |
</threat_model>

<verification>
npm test for coordinator and resultParser tests must pass.
tsc --noEmit must pass.
package.json contains both new dependencies.
</verification>

<success_criteria>
Coordinator can mock-decompose goals into subtasks, build task file content, synthesize results, and parse result files. All behaviors unit tested. Dependencies installed.
</success_criteria>

<output>
Create `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-02-SUMMARY.md` when done
</output>
