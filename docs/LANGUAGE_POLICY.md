# Repository Language Policy

## 1. Canonical Language

English is the canonical and sole maintained documentation language for the `sm-x510-linux-bringup` project.

## 2. Documentation and Artifacts

- All human-facing documentation must be written in English. This includes `README` files, architecture specifications, bring-up guides, hardware runbooks, research reports, audit records, roadmaps, decision logs, and release notes.
- Explanatory prose and human-readable headings in CSV, YAML, and JSON artifacts must be in English where doing so does not disrupt machine parsing or schema constraints.
- Maintainer comments in scripts, source files, and configuration files must be written in English.
- Commit messages, pull request titles, and review comments must be in English.

## 3. Preservation of Raw Evidence and Upstream Material

The following items must remain in their original, verbatim form and must not be translated or altered:
- Raw evidence, runtime logs, serial dumps, logcat outputs, and tool transcripts.
- Vendor strings, Android system properties (`ro.*`), kernel messages (`dmesg`), and hardware register/node names.
- Upstream and vendor code snippets, device tree source nodes, and third-party quotes.
- Cryptographic hashes (SHA-256), checksum files, firmware identifiers, and build fingerprints.
- Exact epistemic status classifications and machine-checked status enums (e.g., `CONFIRMED`, `STRONGLY_SUPPORTED`, `INCONCLUSIVE`, `NOT_READY_FOR_FIRST_CUSTOM_FLASH`, `UNTESTED_EZE4`).

## 4. Agent and Contributor Discipline

- Automated agents and contributors must never alter the repository's documentation language based on the natural language used in user prompts, inquiries, or conversations.
- Prompts received in other languages must be answered appropriately, but repository files, commits, and generated documentation must remain strictly in English.
