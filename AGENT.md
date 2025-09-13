# Global Agent Directives

This document provides global instructions to the agent for interacting with any workspace. These directives should be followed unless overridden by a local markdown file.

## General

- **Be proactive:** Fulfill the user's request thoroughly, including reasonable, directly implied follow-up actions.
- **Confirm Ambiguity/Expansion:** Do not take significant actions beyond the clear scope of the request without confirming with the user. If asked *how* to do something, explain first, don't just do it.

## Checkpoint Commits

Before taking any action, you must make sure that it can be reverted easily and cleanly. First, check if there is a checkpointing feature enabled. If not, check if there is any uncommitted work in the repository and if there is, create a new checkpoint commit that includes all current changes. This ensures that the repository is in a clean state before the agent begins its work.
