# Idea
## Summary
I want a [15_notebook](20_workspaces/15_notebooks) that allows me to test the [format-markdown.md](20_workspaces/12_prompts/tasks/format-markdown.md) prompt.
In the notebook, I want to be able to have a clump of text, run the sequence, and it generate formatted markdown.
I want to use LM Studio http://localhost:1234/v1 with qwen/qwen3.6-27b . The server needs to allow at least 10k context and I think the limit is 18k for the model
This should expand to eventually provide an interactive test across the entire system pipeline of markdown formatting.
## Trigger

I need a way to explore the individual components in this repo as well as observe the steps within the full end to end workflows. I also need to
test and tune and understand individual cause and effect.

## Desired Outcome

Ability to run the model on a dirty markdown file and get a well formatted one

## Unknowns
I'm not sure what all the components are needed in the big picture from when I 
- run a /slash command to formate ./file.md
- ask a larger LLM to format files and it dispatches them via the mcp server
- I trigger a pre commit hook that ensures all markdown files in the repo are formatted

A lot of these senarios are compositional, for now I just need to see a markdown file work when I trigger it from the notebook
