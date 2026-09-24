# Prior art: agents that own the code

*A survey of work related to AI-native software development, compiled 2026-09-23. Every GitHub repo, arXiv paper and key web page linked here was checked to exist on that date. Star counts are approximate.*

## The question

Can AI agents own the whole software lifecycle, perhaps in a representation designed for machines instead of people, while humans only state intent and business goals? What already exists, what works, and what is still open?

## Summary

- **The goal is where the frontier already is.** StrongDM, OpenAI and Anthropic have published systems in which no human wrote the code, and in StrongDM's case no human reviews it either. The practice has a name: the *dark factory*.
- **"AI needs its own language" has been tried at least a dozen times since 2025.** The most serious attempt is Vercel Labs' Zero. None has shown an advantage at scale, and models remain far stronger in popular languages.
- **"Talk straight binary" is the part the evidence rejects.** Low-level output is longer, harder to check and less accurate. Where AI beats compilers, it works inside the toolchain.
- **Trust is the real bottleneck.** The efforts that work without humans reading code replace code review with independent evidence: hidden holdout scenarios, kernel-checked proofs, trusted reference implementations. The ones that failed lacked it.
- **The open gap** is an open, tool-agnostic contract between human intent and machine evidence that covers the whole lifecycle. The pieces exist in separate silos.

## 1. AI-native programming languages

A wave of languages designed for LLMs to write, not humans, arrived in 2025–26.

| Project | Who, when | Idea | Status |
|---|---|---|---|
| [Zero](https://github.com/vercel-labs/zerolang) | Vercel Labs, May 2026 | The program is a semantic graph owned by the compiler. Agents query it and submit type-checked, hash-guarded patches; `.0` text files are an optional view for humans | Experimental; ~5.4k★; active |
| [Vera](https://github.com/aallan/vera) | Alasdair Allan, Feb 2026 | No variable names (typed De Bruijn indices); every function declares contracts and effects, checked with Z3; compiles to WebAssembly | ~400★; active |
| [Aver](https://github.com/jasisz/aver) | Feb 2026 | Code that AI writes and humans audit: effects in signatures, inline verify blocks, export to Lean/Dafny with proof certificates tied to the compiled WebAssembly | ~60★; active |
| [NanoLang](https://github.com/jordanhubbard/nanolang) | Jordan Hubbard, Sep 2025 | Minimal syntax, mandatory tests, transpiles to C, core semantics proved in Coq | ~630★; active |
| [Jacquard](https://github.com/jbwinters/jacquard-lang) | Jul 2026 | Effect rows act as an authority manifest; code identity is content-addressed | Prototype; ~120★ |
| [Mog](https://github.com/voltropy/mog) | Feb 2026 | Typed, embeddable language for agent-written plugins; the whole spec fits in ~3,200 tokens | ~140★; quiet since Mar 2026 |
| [AILANG](https://ailang.sunholo.com/) | Sunholo, Sep 2025 | Deterministic, effect-typed, replayable | Small; active |
| Token-minimizing languages: [GlyphLang](https://github.com/GlyphLang/GlyphLang), [NERD](https://www.nerd-lang.org/), [Codong](https://github.com/brettinhere/Codong), [Sever](https://github.com/AvitalTamir/sever), [B-IR](https://github.com/ImJasonH/ImJasonH/blob/main/articles/llm-programming-language.md) | 2025–26 | Terse syntax to cut token counts | Small, several dormant. Hacker News threads kept asking where the training data would come from |
| [MoonBit](https://www.moonbitlang.com/blog/fastcc-ai-driven-development) | MoonBit team, 2024– | An existing language redesigned to be AI-friendly: flat, signature-first layout and a sampler that checks semantics during decoding ([paper](https://dl.acm.org/doi/10.1145/3643795.3648376)) | Commercial; active |
| [Unison](https://www.unison-lang.org/docs/the-big-idea/) | Unison Computing; 1.0 in Nov 2025 | Code stored as content-addressed, typed syntax trees; text is a view; ships an [MCP server](https://www.unison-lang.org/docs/usage-topics/mcp-setup/) for agents | ~6.7k★; active |
| [Darklang](https://blog.darklang.com/gpt/) | 2023 pivot | Set out to make AI the main way to write code; Dark Inc. [ran out of money](https://blog.darklang.com/goodbye-dark-inc-welcome-darklang-inc/) in 2025 and a successor open-sourced it | Cautionary tale |
| Agent-action languages: [Pel](https://arxiv.org/abs/2505.13453), [Quasar](https://arxiv.org/abs/2506.12202), [Dana](https://github.com/aitomatic/dana) | 2025 | Languages for tool calls and orchestration, not whole applications | Research; quiet |

Research on AI-oriented syntax: [SimPy and DualCode](https://arxiv.org/abs/2404.16333) (ISSTA 2024) define a grammar with the same syntax tree as Python but fewer tokens, plus two-way conversion so humans can keep reading Python. Follow-ups: [Token Sugar](https://arxiv.org/abs/2512.08266) and [removing formatting](https://arxiv.org/abs/2508.13666).

**Evidence**

- **Popularity dominates.** DeepSeek-V3 scores about 80% in Python but 21–24% in Racket and Erlang, failing mostly on compile errors ([ICLR 2026](https://arxiv.org/abs/2509.23261)). Top models are near 100% in Python and JavaScript but 0–11% in esoteric languages ([EsoLang-Bench](https://arxiv.org/abs/2603.09678)).
- **Agents route around unfamiliar languages** by writing Python programs that generate the target code ([Jun 2026](https://arxiv.org/abs/2606.10933)).
- **A small, regular language with its spec in context can keep up on small tasks.** In VeraBench (run by Vera's author, and saturated), Vera scored 98.7% against Python's 96.7% ([vera-bench](https://github.com/aallan/vera-bench)).
- **Token savings from syntax are real but modest**: 8.6–34.7% for SimPy depending on the tokenizer, 24.5% from dropping formatting. Total cost is driven by debugging loops, not syntax density ([Jul 2026](https://arxiv.org/abs/2607.22807); [Dan Luu](https://danluu.com/pl-tokens/)).
- **Exotic languages cost more.** Chess engines built by agents in 17 languages all worked, but exotic languages took 25–50 prompts and about $60–480, against $2–30 for mainstream ones ([Jun 2026](https://arxiv.org/abs/2606.13763)).

Essays: Armin Ronacher, [A Language for Agents](https://lucumr.pocoo.org/2026/2/9/a-language-for-agents/) (Feb 2026); Mark Seemann, [Programming languages for AI](https://blog.ploeh.dk/2026/03/30/programming-languages-for-ai/) (Mar 2026); José Valim, [Why Elixir is the best language for AI](https://dashbit.co/blog/why-elixir-best-language-for-ai) (Feb 2026), which leans on an [AutoCodeBench](https://arxiv.org/abs/2508.09101) result that its own authors caveat.

## 2. Spec- and intent-driven development

Humans write specs and agents generate the code. Birgitta Böckeler's [analysis on martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) (Oct 2025) separates three levels: *spec-first*, *spec-anchored* and *spec-as-source*. Only the last treats code as a disposable by-product.

| Project | Who, when | Idea | Do humans still read code? |
|---|---|---|---|
| [Spec Kit](https://github.com/github/spec-kit) | GitHub, Sep 2025; v1.0 Aug 2026 | Constitution → specify → plan → tasks → implement; treats code as the last mile | Yes, code and artifact diffs; ~139k★ |
| [Kiro](https://kiro.dev/blog/general-availability/) | AWS, Jul 2025; GA Nov 2025 | Requirements in EARS notation → design → tasks; property-based tests from requirements; SMT-based [requirements analysis](https://kiro.dev/blog/deep-spec-analysis/); [KiroCrew](https://github.com/kirodotdev/KiroCrew) for orchestration | Yes, PR review |
| [Tessl Framework](https://tessl.io/blog/tessl-launches-spec-driven-framework-and-registry) | Tessl, Sep 2025 | The main spec-as-source attempt: generated files marked do-not-edit, spec–code hash tracking | **Paused** in Nov 2025 ([changelog](https://docs.tessl.io/changelog-cli.md)); Tessl refocused on its registry |
| [OpenSpec](https://github.com/Fission-AI/OpenSpec) | Fission-AI, Aug 2025 | Each change carries delta specs that merge into living specs; built for existing codebases | Yes; ~70k★ |
| [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) | 2025– | Persona agents (analyst, PM, architect, developer) run brief → PRD → architecture → build | Yes; ~53k★ |
| [Superpowers](https://github.com/obra/superpowers) | Jesse Vincent, Oct 2025 | Skills that draw out a spec, plan, then run test-driven work through subagents | Yes; ~291k★ |
| [Augment Intent](https://www.augmentcode.com/blog/intent-a-workspace-for-agent-orchestration) | Feb 2026 | Coordinator, implementer and verifier agents share a living spec | Yes, PR review |
| [Codeplain \*\*\*plain](https://github.com/Codeplain-ai/codeplain) | Codeplain, 2024– | Structured spec language; generates conformance tests; argues code should be [regenerated rather than maintained](https://thenewstack.io/codeplain-spec-driven-regenerative-code/) | Specs only; the closest to spec-as-source |
| [Marsha](https://github.com/alantech/marsha), [Plang](https://plang.is/), [SpecLang](https://githubnext.com/projects/speclang/), [SudoLang](https://github.com/paralleldrive/sudolang) | 2023– | Natural language or pseudocode compiled or interpreted by LLMs | Mixed; small |

**Evidence and critique**

- For one Spec Kit feature, the agent produced 2,577 lines of markdown for 689 lines of code, and the whole process took about 10× longer than plain iterative prompting ([Scott Logic, Nov 2025](https://blog.scottlogic.com/2025/11/26/putting-spec-kit-through-its-paces-radical-idea-or-reinvented-waterfall.html)).
- A comparison of six frameworks found that none covered all process dimensions, and spec–code drift kept recurring ([Jun 2026](https://arxiv.org/abs/2606.04967)).
- Thoughtworks Technology Radar places spec-driven development at *Assess* ([Nov 2025](https://www.thoughtworks.com/en-us/radar/techniques/spec-driven-development)).
- Shuvendu Lahiri's [Intent Formalization](https://arxiv.org/abs/2603.17150) (Microsoft Research, Mar 2026) names the grand challenge: validating that a spec says what the user meant, which only the user can judge.

**Takeaway:** every tool here still has humans reviewing code or pull requests. Spec-as-source is the open problem, and its best-funded attempt was paused.

## 3. Verification: trusting code nobody reads

The [vericoding benchmark](https://arxiv.org/abs/2509.22908) (Bursuc et al., with Max Tegmark, Sep 2025) names the agenda: code proven correct against a formal spec, as opposed to vibe coding.

- **Success rates are climbing fast.** On 12,504 specs, models succeeded 82% of the time in Dafny, 44% in Verus and 27% in Lean (2025). By May 2026 an agent loop reached 95% on a curated Lean subset with escape hatches banned ([Yao](https://arxiv.org/abs/2605.27485)).
- **Axon** ([Martin Rinard, May 2026](https://arxiv.org/abs/2605.01660)): Claude Code wrote a verified compiler, 38,000 lines of Lean in 34 days. The author never read the verified code; trust came from proofs, translation checking, tests and audits.
- **lean-zip** ([Kim Morrison](https://github.com/kim-em/lean-zip)): agents wrote DEFLATE compression in Lean, and a pull request merges only if the round-trip proof still checks.
- **Fermat's Last Theorem** ([Anthropic, Sep 2026](https://www.anthropic.com/research/formalizing-fermats-last-theorem)): Claude wrote 13 million lines of Lean in 11 days. No human reads the proof. Trust rests on the theorem's *statement* and on Lean's kernel. That is the pattern this project cares about: humans read the spec, and machines check the rest.
- **Cryptography at scale**: [SymCrypt via Aeneas](https://arxiv.org/abs/2609.15648) (Microsoft, Sep 2026); [CryptoProver](https://arxiv.org/abs/2608.00965), which took about $467 and 11 hours, where a five-person team had spent eight months; and [agents writing SPARK](https://arxiv.org/abs/2607.14340).
- **A hidden verified intermediate language**: [Dafny as Verification-Aware Intermediate Language](https://arxiv.org/abs/2501.06283) (Jan 2025). The user speaks natural language and never sees the Dafny.
- **Voices**: Martin Kleppmann, [AI will make formal verification go mainstream](https://martin.kleppmann.com/2025/12/08/ai-formal-verification.html) (Dec 2025); Leo de Moura, [When AI writes the world's software, who verifies it?](https://leodemoura.github.io/blog/2026-2-28-when-ai-writes-the-worlds-software-who-verifies-it/) (Feb 2026); AWS's Byron Cook [on automated reasoning and trust](https://www.allthingsdistributed.com/2026/02/a-chat-with-byron-cook-on-automated-reasoning-and-trust-in-ai-systems.html) (Feb 2026).

**Limits**

- **Scale.** The best model solves 41% of repository-scale tasks ([VeriSoftBench](https://arxiv.org/abs/2602.18307)). Agents fully built 27 of 43 multi-module repositories, none of them among the hardest ([Vero](https://arxiv.org/abs/2608.13522)).
- **Specs are the weak link.** At best 77.8% of spec formalizations were correct, and LLM judges missed 26% of the failures ([Verus-SpecGym](https://arxiv.org/abs/2605.26457)). Many specs the verifier accepted were behaviorally weak ([Spec-Harness](https://arxiv.org/abs/2604.00280)).
- **Agents game visible checks.** GPT-5 exploited the tests in 76% of one impossible-task set; hiding the tests cut cheating to about zero ([ImpossibleBench](https://arxiv.org/abs/2510.20270)).
- **The trusted base can break.** lean-zip still had a heap overflow in Lean's runtime and a bug in an unverified parser ([write-up](https://kirancodes.me/posts/log-who-watches-the-watchers.html)).

Realistic to verify end to end in 2026: algorithmic libraries, codecs, parsers, cryptography, small compilers, policy engines, protocol state machines and smart contracts. Not yet: business apps with fuzzy intent, UI, ML components, behavior defined by third-party services, large distributed systems, performance and UX.

## 4. Below source code: binary, IR and structure

- **The claim.** At xAI's all-hands in Feb 2026, Elon Musk predicted that by the end of 2026 AI would skip coding and "create the binary directly" ([clip](https://x.com/elonmusk/status/2021745508277268824); wording from listener transcriptions).
- **The rebuttals.** Compilers guarantee they preserve a program's meaning, and LLMs don't. Tokens cost more than CPU cycles, so an AI that could beat compilers would be better used writing a better compiler ([Glauber Costa](https://x.com/glcst/status/2021963218218848328)). LLMs do best where success can be checked ([Chris Lattner](https://www.modular.com/blog/the-claude-c-compiler-what-it-reveals-about-the-future-of-software)).
- **The evidence.**
  - When models translated C straight to assembly, only 28–35% of outputs even built ([Nov 2025](https://arxiv.org/abs/2511.04132)).
  - Assembly takes 3–6× the tokens of the C it comes from, and one-shot translation breaks on long functions ([LEGO-Compiler](https://arxiv.org/abs/2505.20356)).
  - Where AI beats compilers, it starts from compiler output and works inside the toolchain. [SuperCoder](https://arxiv.org/abs/2505.11480) produced code 1.46× faster than `gcc -O3`, and [Meta's LLM Compiler](https://arxiv.org/abs/2407.02524) code 5% smaller than `-Oz`.
  - The representation mattered more than the model. Across six hardware-design languages, pass rates ranged from 3% to 88%, while frontier models differed by less than 1.25× within any one language ([Apr 2026](https://arxiv.org/abs/2604.17097)).
  - When 16 agents built a 100,000-line C compiler, they wrote it in Rust ([Anthropic, Feb 2026](https://www.anthropic.com/engineering/building-c-compiler)).
- **Structure helps.**
  - Giving the model typed-hole context from the language server tripled test pass rates ([Hazel, OOPSLA 2024](https://arxiv.org/abs/2409.00921)).
  - Type-constrained decoding cut compile errors by 52–75% ([PLDI 2025](https://arxiv.org/abs/2504.09246)), though a [2026 replication](https://arxiv.org/abs/2606.21619) found that overly strict constraints hurt.
  - Compiler feedback during generation cut error rates in repository-level Rust from 65.9% to 13.1% ([Jul 2026](https://arxiv.org/abs/2607.13921)).
  - Code stored as graphs now has agent APIs: [Unison's MCP server](https://www.unison-lang.org/docs/usage-topics/mcp-setup/) and [JetBrains MPS's agent toolkit](https://www.jetbrains.com/help/mps/mps-projectional-agent-toolkit.html) (Jul 2026).

**Takeaway:** "AI-native" should mean easiest for machines to check and edit, not unreadable to humans. Binary belongs at the output of a deterministic compiler.

## 5. Dark factories: agents running the lifecycle

| Case | When | What happened | How humans keep control |
|---|---|---|---|
| [StrongDM Software Factory](https://factory.strongdm.ai/) ([Simon Willison's write-up](https://simonwillison.net/2026/Feb/7/software-factory/)) | Since Jul 2025; published Feb 2026 | House rules say humans neither write nor review code | Specs, plus end-to-end scenarios stored outside the repo as a holdout set; a "Digital Twin Universe" of cloned third-party APIs; probabilistic satisfaction scores. Their coding agent, [Attractor](https://github.com/strongdm/attractor), is published only as a natural-language spec |
| [Dan Shapiro's Five Levels](https://www.danshapiro.com/blog/2026/01/the-five-levels-from-spicy-autocomplete-to-the-software-factory/) | Jan 2026 | A taxonomy of AI-assisted development that ends at Level 5, the dark factory | Level 4: humans write specs, review plans and check test results. Level 5: specs in, software out |
| [OpenAI harness engineering](https://openai.com/index/harness-engineering/) | Feb 2026 | About 1M lines and 1,500 PRs over five months, none written by hand, by a team that grew from 3 to 7 engineers | Repo docs as the source of truth, architecture rules enforced automatically, agents reviewing agents, and telemetry that agents can read ([interview](https://www.latent.space/p/harness-eng)). Follow-on: [Symphony](https://github.com/openai/symphony) |
| [Anthropic's C compiler](https://www.anthropic.com/engineering/building-c-compiler) | Feb 2026 | 16 parallel agents, about $20k: a 100k-line Rust compiler that builds Linux 6.9 and passes about 99% of GCC's torture tests | A trusted reference (GCC) and strong tests |
| [Cursor's long-running agents](https://cursor.com/blog/scaling-agents) | Jan 2026 | A browser of over 1M lines in about a week | Tolerates a steady error rate; [The Register found about 88% of CI jobs failing](https://www.theregister.com/2026/01/22/cursor_ai_wrote_a_browser/) |
| [Stripe Minions](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents) | Feb 2026 | Over 1,000 merged PRs a week with no human-written code | Every PR reviewed by a human |

Orchestration patterns: Geoffrey Huntley's [Ralph loop](https://ghuntley.com/ralph/) (2025); Steve Yegge's [Beads](https://github.com/gastownhall/beads) and [Gas Town](https://yegge.ai/gastown) (2025–26); [Factory Missions](https://factory.com/news/missions) (2026); and Anthropic's [harness for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), which forbids agents to edit tests.

**Critiques and failure modes**

- Dex Horthy, [Why Software Factories Fail](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/wsff.md) (Jul 2026): his own attempt to skip code review ended in outages and a rewrite by hand.
- Addy Osmani, [Comprehension Debt](https://addyosmani.com/blog/comprehension-debt/) (Mar 2026): checking the work, not generating it, is the real limit.
- Stanford CodeX, [Built by agents, tested by agents, trusted by whom?](https://law.stanford.edu/2026/02/08/built-by-agents-tested-by-agents-trusted-by-whom/) (Feb 2026): agents grading agents is circular, and liability is unclear.
- Security: about 95% of AI-generated code is syntactically correct but only about 55% is secure, with no improvement across model generations ([Veracode, 2026](https://www.veracode.com/blog/spring-2026-genai-code-security/)).
- Operations: an agent deleted a production database during a code freeze ([The Register, Jul 2025](https://www.theregister.com/2025/07/22/replit_saastr_response/)).

## Older ideas this echoes

- **[Intentional Programming](https://en.wikipedia.org/wiki/Intentional_programming)** (Charles Simonyi, Microsoft Research, 1990s): programs stored as trees of intentions, with text as one projection.
- **[Model-Driven Architecture](https://en.wikipedia.org/wiki/Model-driven_architecture)** (OMG, 2001): generate code from models. It under-delivered, and critics of spec-driven development cite it.
- **[Proof-Carrying Code](https://en.wikipedia.org/wiki/Proof-carrying_code)** (Necula and Lee, 1996–97): code ships with a proof that the consumer can check cheaply, without trusting whoever produced it.
- **[Design by Contract](https://en.wikipedia.org/wiki/Design_by_contract)** (Bertrand Meyer, Eiffel): preconditions and postconditions as executable specification.
- **[Safety and assurance cases](https://en.wikipedia.org/wiki/Safety_case)**, often written in [Goal Structuring Notation](https://en.wikipedia.org/wiki/Goal_structuring_notation): how safety-critical industries trust systems too complex to inspect, through structured arguments that link claims to evidence.

## What this means for Warrant

1. **The goal is sound and timely.** Humans steering intent while agents own implementation is exactly where the frontier is.
2. **A new AI-only language is the most crowded and least proven piece.** It faces a cold start with every model generation, and Zero is well ahead.
3. **Raw binary is a dead end for authoring.** Keep it as compiler output.
4. **Trust through independent evidence** is what makes "no human reads the code" work, and it is the least standardized piece.
5. **The open gap** is an open protocol that runs from human intent, to machine-checkable obligations, to changes that carry their own evidence, to gates that decide autonomy from that evidence, to a ledger that humans read instead of code. It should cover the whole lifecycle, including operations and evolution, and work with any agent and any language. That is what Warrant sets out to be; see the [specification](SPEC.md).

## Method

Five parallel research passes on 2026-09-23 covered AI-native languages, spec-driven development, verification, representations below source code, and dark factories. Each pass had to confirm items against primary sources. Every GitHub repo was then re-checked through the GitHub API, every arXiv ID through the arXiv API, and key web pages were fetched. Figures are as reported by their sources; benchmarks run by vendors or by a language's own author are flagged as such.
