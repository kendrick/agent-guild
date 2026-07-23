# The Agent Guild

Runs Claude Code as an org chart. An expensive orchestrator plans and rules but never builds; cheap worker subagents build; independent checker agents verify the workers without trusting a word they say. It's a recipe, not a framework: nothing here but Claude Code's own primitives, so there's no runner to install and no service to keep alive.

The bet underneath it: a cheap model doing well-specified work under an independent check is both cheaper and more reliable than one expensive model doing everything and grading itself.

## Install

From any Claude Code session:

```
/plugin marketplace add kendrick/agent-guild
/plugin install agent-guild
```

That lands the tooling: the six guild agents, the lifecycle skills, and the four hook gates. What it doesn't do is put the guild to work in a project. For that, run this once inside the project where you want to run jobs:

```
/agent-guild:init
```

The extra step exists because a plugin can't ship an always-on `CLAUDE.md`. Claude Code loads a plugin's agents, skills, and hooks on demand, but the orchestrator contract—the standing rules that keep the orchestrator out of the deliverables and route every task through an independent check—has to live as persistent project instructions, and a plugin has no way to contribute those. So `/agent-guild:init` writes the contract and the runtime scaffolding into the project itself, where Claude Code reads it every session. Install once per machine; init once per project.

## Starting a Job

Each phase of a job is a guild skill. Most jobs start at the front door:

```
/agent-guild:job <issue number, URL, or file path>
```

`/agent-guild:job` intakes work that already lives somewhere—a GitHub issue, a spec on disk, a page at a URL—and turns it into the job's spec. It flows straight into `/agent-guild:constitution`, where you settle what "done right" means for this job: the falsifiable standard every task gets checked against. From there the orchestrator drives the rest. `/agent-guild:decompose` breaks the spec into checked tasks, workers build them, checkers verify them without reading a word the worker said about its own work, and `/agent-guild:retrospective` closes the job with a report on what the checks caught and where the retries clustered.

No source to point at? Skip the front door and open with `/agent-guild:constitution`; it interviews you for the standard from scratch.

## Running It Inside This Repo

One caveat if you enable the plugin inside the agent-guild repo itself. The repo already registers the same hooks through its own `.claude/settings.json`, so with the plugin turned on, every gate fires twice: two dispatch-guards on one dispatch, two stop-gates on one turn. Nothing breaks, but the doubled output is noise and the `SMOKE.md` drills stop matching what you see. Leave the plugin disabled here and let the checked-in `.claude/` copy run the gates. Everywhere else, the plugin is the whole install.
