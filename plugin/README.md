# The Agent Guild

Runs Claude Code or Codex as an org chart. An expensive orchestrator plans and rules but never builds; cheap worker subagents build; independent checker agents verify the workers without trusting a word they say. It's a recipe, not a framework: nothing here but host primitives, so there's no runner to install and no service to keep alive.

The bet underneath it: a cheap model doing well-specified work under an independent check is both cheaper and more reliable than one expensive model doing everything and grading itself.

## Install

[Install Agent Guild](https://github.com/kendrick/agent-guild/blob/main/docs/installing.md) is the single setup guide for the Claude Code plugin, Codex CLI and desktop plugin, and repo-local Codex IDE route. It includes project init, hook trust, cross-vendor credentials, fresh-project checks, and the duplicate-registration warning.

Install once for the host, initialize once per project, then start a fresh session and run the smoke suite before relying on the gates.

## Starting a Job

Each phase of a job is a Guild skill. Most jobs start at the host's namespaced `agent-guild:job` entry point. It intakes work that already lives somewhere—a GitHub issue, a spec on disk, or a page at a URL—and turns it into the job's spec. It flows straight into the constitution skill, where you settle what "done right" means: the falsifiable standard every task gets checked against. From there the orchestrator drives decomposition, checked implementation, and the retrospective.

No source to point at? Skip intake and open with the host's `agent-guild:constitution` skill; it interviews you for the standard from scratch.

## Running It Inside This Repo

Do not enable a host plugin beside that host's repo-local Agent Guild copy. The same skills and hooks would load twice, producing duplicate names, duplicate hook listings, and two denial messages for one action. The installation guide names the safe combinations.
