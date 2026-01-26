# CLI Reference (Generated)

This file is generated from the live Typer command tree to keep it aligned with the code.

Do not edit by hand.

To regenerate:

```bash
uv run python scripts/generate_cli_reference.py
```

## Command Tree

- `erdos`
  - `erdos ask`
  - `erdos convert`
  - `erdos dashboard`
  - `erdos ingest`
  - `erdos lean`
    - `erdos lean check`
    - `erdos lean copilot`
      - `erdos lean copilot serve`
    - `erdos lean formalize`
    - `erdos lean import`
    - `erdos lean init`
    - `erdos lean prove`
    - `erdos lean status`
  - `erdos list`
  - `erdos logs`
  - `erdos loop`
    - `erdos loop run`
  - `erdos refs`
    - `erdos refs problem`
    - `erdos refs s2`
      - `erdos refs s2 citations`
      - `erdos refs s2 cited-by`
      - `erdos refs s2 references`
    - `erdos refs zbmath`
  - `erdos research`
    - `erdos research attempt`
      - `erdos research attempt list`
      - `erdos research attempt log`
    - `erdos research exa`
      - `erdos research exa search`
    - `erdos research fmt`
    - `erdos research hypothesis`
      - `erdos research hypothesis add`
      - `erdos research hypothesis list`
      - `erdos research hypothesis update`
    - `erdos research init`
    - `erdos research lead`
      - `erdos research lead add`
      - `erdos research lead list`
      - `erdos research lead update`
    - `erdos research note`
    - `erdos research open`
    - `erdos research status`
    - `erdos research synthesize`
    - `erdos research task`
      - `erdos research task add`
      - `erdos research task list`
      - `erdos research task update`
    - `erdos research validate`
  - `erdos search`
  - `erdos show`
  - `erdos sync`
    - `erdos sync all`
    - `erdos sync proof`
    - `erdos sync statements`
    - `erdos sync submodule`
    - `erdos sync website`

## Help Output

### `erdos`

```text

 Usage: erdos [OPTIONS] COMMAND [ARGS]...

 CLI toolkit for Erdős problem research.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --version             -v                             Show version and exit.  │
│ --json                                               Output as JSON for      │
│                                                      machine consumption.    │
│ --log-level                   [debug|info|warn|erro  Logging level: DEBUG,   │
│                               r]                     INFO, WARN, ERROR.      │
│                                                      [default: INFO]         │
│ --install-completion                                 Install completion for  │
│                                                      the current shell.      │
│ --show-completion                                    Show completion for the │
│                                                      current shell, to copy  │
│                                                      it or customize the     │
│                                                      installation.           │
│ --help                -h                             Show this message and   │
│                                                      exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list        List Erdős problems with optional filters.                       │
│ show        Show detailed problem information.                               │
│ refs        List problem references, query Semantic Scholar, or look up      │
│             zbMATH.                                                          │
│ search      Search problem statements.                                       │
│ lean        Lean 4 theorem prover commands.                                  │
│ ingest      Ingest literature metadata and cache.                            │
│ ask         Ask questions about Erdős problems using RAG.                    │
│ logs        Query and summarize run logs.                                    │
│ loop        Iterative Lean proof loop.                                       │
│ convert     Convert PDF files to text/markdown.                              │
│ research    Manage per-problem research workspace and state.                 │
│ sync        Sync problem data from multiple sources.                         │
│ dashboard   View research progress dashboard.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos ask`

```text

 Usage: erdos ask [OPTIONS] PROBLEM_ID QUESTION_ARG COMMAND [ARGS]...

 Ask questions about Erdős problems using RAG.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id        INTEGER RANGE  Problem ID [required]                  │
│ *    question_arg      TEXT           Question or '-' for stdin [required]   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --limit        -n      INTEGER RANGE              Maximum sources to         │
│                        [1<=x<=1000]               retrieve                   │
│                                                   [default: 5]               │
│ --build-index                                                                │
│ --no-llm                                                                     │
│ --llm-cmd              TEXT                       Override LLM command       │
│                                                   (default: from             │
│                                                   ERDOS_LLM_COMMAND). Pass   │
│                                                   an empty value to disable. │
│ --help         -h                                 Show this message and      │
│                                                   exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos convert`

```text

 Usage: erdos convert [OPTIONS] PDF_PATH COMMAND [ARGS]...

 Convert PDF files to text/markdown.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    pdf_path      PATH  Path to PDF file to convert [required]              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --output       -o      PATH                  Output file path (default:      │
│                                              stdout)                         │
│ --format       -f      [markdown|text|json]  Output format: markdown, text,  │
│                                              or json                         │
│                                              [default: markdown]             │
│ --converter    -c      TEXT                  Converter to use: marker        │
│                                              (default), pdfplumber           │
│                                              [default: marker]               │
│ --use-llm                                    Enable LLM-enhanced extraction  │
│                                              (Marker only)                   │
│ --llm-service          TEXT                  LLM service: gemini, claude,    │
│                                              openai, ollama                  │
│ --force-ocr                                  Force OCR even if text is       │
│                                              extractable (Marker only)       │
│ --device       -d      TEXT                  Torch device for Marker: cpu,   │
│                                              cuda, mps (sets TORCH_DEVICE    │
│                                              env var)                        │
│ --help         -h                            Show this message and exit.     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos dashboard`

```text

 Usage: erdos dashboard [OPTIONS] COMMAND [ARGS]...

 View research progress dashboard.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --problem           INTEGER                     Start in detail view for a   │
│                                                 specific problem.            │
│ --problems          TEXT                        Comma-separated problem IDs  │
│                                                 to include.                  │
│ --recent            TEXT                        Time window for attempts:    │
│                                                 7d, 30d, 90d, or 'all'.      │
│                                                 [default: 30d]               │
│ --refresh           INTEGER RANGE [0<=x<=3600]  Enable interactive mode      │
│                                                 (non-zero) with manual 'r'   │
│                                                 to refresh. Set 0 for        │
│                                                 single-render.               │
│                                                 [default: 5]                 │
│ --help      -h                                  Show this message and exit.  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos ingest`

```text

 Usage: erdos ingest [OPTIONS] [PROBLEM_ID] COMMAND [ARGS]...

 Ingest literature metadata and cache.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   problem_id      [PROBLEM_ID]  Problem ID (omit for batch mode)             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force           -f                                                         │
│ --no-download                                                                │
│ --no-network                                                                 │
│ --timeout                 FLOAT                                              │
│ --delay                   FLOAT RANGE [x>=0.0]      [default: 3.0]           │
│ --mailto                  TEXT                                               │
│ --source                  [openalex|arxiv|crossref  Metadata source:         │
│                           ]                         openalex (default),      │
│                                                     arxiv, or crossref       │
│                                                     [default: openalex]      │
│ --all                                               Process all problems     │
│                                                     (batch mode)             │
│ --status                  [open|proved|disproved|p  Filter by status: open,  │
│                           artially_solved|unknown]  proved, disproved,       │
│                                                     partially_solved,        │
│                                                     unknown                  │
│ --prize-min               INTEGER                   Minimum prize amount     │
│ --prize-max               INTEGER                   Maximum prize amount     │
│ --tag                     TEXT                      Filter by tag (can be    │
│                                                     repeated)                │
│ --limit                   INTEGER RANGE             Max problems to process  │
│                           [1<=x<=1000]                                       │
│ --skip                    INTEGER RANGE [x>=0]      Skip first N problems    │
│ --resume                                            Resume from last         │
│                                                     incomplete batch         │
│ --dry-run                                           Show what would be       │
│                                                     processed                │
│ --max-concurrent          INTEGER                   Max parallel operations  │
│                                                     (ingest: 1)              │
│                                                     [default: 1]             │
│ --pdf                                               Enable PDF conversion    │
│                                                     for non-arXiv references │
│ --no-pdf                                            Skip PDFs entirely       │
│                                                     (metadata only)          │
│ --pdf-converter           TEXT                      PDF converter: marker    │
│                                                     (default), pdfplumber    │
│                                                     [default: marker]        │
│ --use-llm                                           Enable LLM-enhanced PDF  │
│                                                     extraction               │
│ --help            -h                                Show this message and    │
│                                                     exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos lean`

```text

 Usage: erdos lean [OPTIONS] COMMAND [ARGS]...

 Lean 4 theorem prover commands.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ init        Initialize Lean 4 project with mathlib.                          │
│ check       Check a Lean file for compilation errors.                        │
│ formalize   Generate Lean skeletons for problems.                            │
│ prove       Run Aristotle prove-from-file on a Lean file.                    │
│ status      Show formalization status for problems.                          │
│ import      Import upstream formalization for a problem.                     │
│ copilot     Lean Copilot integration commands.                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos lean check`

```text

 Usage: erdos lean check [OPTIONS] FILE

 Check a Lean file for compilation errors.

 Example: erdos lean check formal/lean/Erdos/Problem006.lean

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    file      PATH  Lean file to check. [required]                          │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --path  -p      PATH  Path to Lean project (default: formal/lean/)           │
│ --help  -h            Show this message and exit.                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos lean copilot`

```text

 Usage: erdos lean copilot [OPTIONS] COMMAND [ARGS]...

 Lean Copilot integration commands.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ serve   Start the Lean Copilot external API server.                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos lean copilot serve`

```text

 Usage: erdos lean copilot serve [OPTIONS]

 Start the Lean Copilot external API server.

 Implements the external model API for Lean Copilot:
 - POST /generate - Generate tactic suggestions

 Requires the 'copilot' extra: uv sync --extra copilot

 Example:
     erdos lean copilot serve --port 8080

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --port       -p      INTEGER  Server port [default: 8000]                    │
│ --host       -H      TEXT     Bind address [default: 127.0.0.1]              │
│ --llm-cmd            TEXT     Override LLM command for /generate (bypasses   │
│                               router)                                        │
│ --log-level          TEXT     Logging verbosity [default: info]              │
│ --help       -h               Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos lean formalize`

```text

 Usage: erdos lean formalize [OPTIONS] [PROBLEM_ID]

 Generate Lean skeletons for problems.

 Single mode: Pass a PROBLEM_ID to formalize one problem.

 Batch mode: Omit PROBLEM_ID and use --all or filter options (--status, --tag)
 to process multiple problems. Supports parallel execution with
 --max-concurrent.

 Use --import-upstream to import existing formalizations instead.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   problem_id      [PROBLEM_ID]  Problem ID to formalize (omit for batch      │
│                                 mode).                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --path             -p      PATH                     Path to Lean project     │
│                                                     (default: formal/lean/)  │
│ --force            -f                               Overwrite existing file  │
│ --import-upstream                                   Import upstream          │
│                                                     formalization instead of │
│                                                     generating skeleton      │
│ --no-network                                        Use cached upstream file │
│                                                     only (requires           │
│                                                     --import-upstream)       │
│ --all                                               Process all problems     │
│                                                     (batch mode)             │
│ --status                   [open|proved|disproved|  Filter by status: open,  │
│                            partially_solved|unknow  proved, disproved,       │
│                            n]                       partially_solved,        │
│                                                     unknown                  │
│ --tag                      TEXT                     Filter by tag (can be    │
│                                                     repeated)                │
│ --limit                    INTEGER RANGE            Max problems to process  │
│                            [1<=x<=1000]                                      │
│ --skip-existing                                     Skip problems with       │
│                                                     existing Lean files      │
│ --dry-run                                           Show what would be       │
│                                                     processed                │
│ --max-concurrent           INTEGER                  Max parallel Lean        │
│                                                     compilations (default:   │
│                                                     4)                       │
│                                                     [default: 4]             │
│ --help             -h                               Show this message and    │
│                                                     exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos lean import`

```text

 Usage: erdos lean import [OPTIONS] PROBLEM_ID

 Import upstream formalization for a problem.

 Fetches from google-deepmind/formal-conjectures by default.

 Example: erdos lean import 6

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID to import formalization for.  │
│                                     [required]                               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --path                  -p      PATH  Path to Lean project (default:         │
│                                       formal/lean/)                          │
│ --source                        TEXT  Override source URL                    │
│ --force                 -f            Overwrite existing local file          │
│ --dry-run                             Show what would be imported without    │
│                                       writing                                │
│ --no-network                          Use cached upstream file only          │
│ --skip-lean-validation                Do not run Lean check on imported file │
│ --help                  -h            Show this message and exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos lean init`

```text

 Usage: erdos lean init [OPTIONS]

 Initialize Lean 4 project with mathlib.

 Creates lakefile.lean, lean-toolchain, and directory structure.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --path        -p      PATH  Path to Lean project (default: formal/lean/)     │
│ --no-mathlib                Initialize a minimal project without mathlib     │
│                             (faster, offline).                               │
│ --help        -h            Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos lean prove`

```text

 Usage: erdos lean prove [OPTIONS] INPUT_FILE

 Run Aristotle prove-from-file on a Lean file.

 Requires ARISTOTLE_API_KEY environment variable to be set.
 Writes output to a separate file (never overwrites the input).

 Example: erdos lean prove Problem006.lean --output Problem006.solved.lean

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    input_file      PATH  Lean file to prove. [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --output                -o      PATH     Output file path (required; must │
│                                             differ from input).              │
│                                             [required]                       │
│    --timeout               -t      INTEGER  Maximum seconds to wait for      │
│                                             completion.                      │
│                                             [default: 600]                   │
│    --informal                               Pass --informal flag to          │
│                                             Aristotle.                       │
│    --formal-input-context                   Pass --formal-input-context flag │
│                                             to Aristotle.                    │
│    --help                  -h               Show this message and exit.      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos lean status`

```text

 Usage: erdos lean status [OPTIONS] [PROBLEM_ID]

 Show formalization status for problems.

 Without PROBLEM_ID, shows summary counts.
 With PROBLEM_ID, shows detailed status for that problem.

 Example: erdos lean status 6

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   problem_id      [PROBLEM_ID]  Problem ID (optional; shows summary if       │
│                                 omitted).                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --path      -p      PATH  Path to Lean project (default: formal/lean/)       │
│ --upstream                Check upstream metadata for formalization status   │
│ --local                   Check local formal/lean/Erdos/ directory           │
│ --help      -h            Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos list`

```text

 Usage: erdos list [OPTIONS] COMMAND [ARGS]...

 List Erdős problems with optional filters.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --status     -s      TEXT                        Filter by status: open,     │
│                                                  proved, disproved,          │
│                                                  partially_solved            │
│ --prize-min          INTEGER RANGE [x>=0]        Minimum prize amount in USD │
│ --prize-max          INTEGER RANGE [x>=0]        Maximum prize amount in USD │
│ --tag        -t      TEXT                        Filter by tag (can be       │
│                                                  repeated)                   │
│ --limit      -n      INTEGER RANGE [1<=x<=1000]  Maximum number of results   │
│                                                  [default: 100]              │
│ --help       -h                                  Show this message and exit. │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos logs`

```text

 Usage: erdos logs [OPTIONS] COMMAND [ARGS]...

 Query and summarize run logs.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --problem-id  -p      INTEGER                     Filter by problem ID.      │
│ --command             TEXT                        Filter by command name     │
│                                                   (e.g., 'erdos lean         │
│                                                   check').                   │
│ --since               TEXT                        Filter logs after date     │
│                                                   (e.g., '7d', '2h',         │
│                                                   '2026-01-15').             │
│ --status              TEXT                        Filter by 'success' or     │
│                                                   'failure'.                 │
│ --limit       -n      INTEGER RANGE [1<=x<=1000]  Max entries to return.     │
│                                                   [default: 50]              │
│ --summary                                         Show aggregated summary    │
│                                                   instead of individual      │
│                                                   entries.                   │
│ --help        -h                                  Show this message and      │
│                                                   exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos loop`

```text

 Usage: erdos loop [OPTIONS] COMMAND [ARGS]...

 Iterative Lean proof loop.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ run   Run iterative proof loop for a problem.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos loop run`

```text

 Usage: erdos loop run [OPTIONS] PROBLEM_ID

 Run iterative proof loop for a problem.

 This command runs an iterative "propose → apply → check" cycle to assist
 Lean formalization. Each iteration:

 1. Checks the current Lean file for errors
 2. Builds a prompt with the file, errors, and problem context
 3. Calls an external LLM to propose a fix
 4. Validates and applies the fix (if --no-apply is not set)
 5. Repeats until success or max iterations

 Safety guardrails:
 - Only modifies files under formal/lean/Erdos/
 - Rejects patches that add sorry or admit (by default)
 - Rejects patches larger than configured limits
 - Aborts if file shrinks by > 20%

 Example (propose only; does not write to disk):

     ERDOS_LLM_COMMAND="./scripts/llm.sh" erdos loop run 6 --no-apply

 Example (auto-apply):

     ERDOS_LLM_COMMAND="./scripts/llm.sh" erdos loop run 6

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID to work on. [required]        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --path                  -p      PATH                  Path to Lean project   │
│                                                       (default:              │
│                                                       formal/lean/)          │
│ --max-iter              -n      INTEGER RANGE [x>=1]  Maximum iterations     │
│                                                       (default: 10).         │
│                                                       [default: 10]          │
│ --no-apply                                            Propose changes only;  │
│                                                       never write to disk.   │
│ --timeout                       INTEGER RANGE [x>=1]  Lean check timeout in  │
│                                                       seconds (default:      │
│                                                       120).                  │
│                                                       [default: 120]         │
│ --allow-sorry-increase          INTEGER RANGE [x>=0]  Allow patch to         │
│                                                       increase sorry count   │
│                                                       by up to N (default:   │
│                                                       0).                    │
│                                                       [default: 0]           │
│ --max-patch-lines               INTEGER RANGE [x>=1]  Reject patches larger  │
│                                                       than this many lines   │
│                                                       (default: 50).         │
│                                                       [default: 50]          │
│ --max-patch-bytes               INTEGER RANGE [x>=1]  Reject patches larger  │
│                                                       than this many bytes   │
│                                                       (default: 8192).       │
│                                                       [default: 8192]        │
│ --rag-limit                     INTEGER RANGE [x>=0]  Maximum retrieved      │
│                                                       context chunks in      │
│                                                       prompt (default: 5).   │
│                                                       [default: 5]           │
│ --llm-cmd                       TEXT                  Override LLM command   │
│                                                       (default: from         │
│                                                       ERDOS_LLM_COMMAND env  │
│                                                       var).                  │
│ --help                  -h                            Show this message and  │
│                                                       exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos refs`

```text

 Usage: erdos refs [OPTIONS] COMMAND [ARGS]...

 List problem references, query Semantic Scholar, or look up zbMATH.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ problem   List references for a problem.                                     │
│ s2        Semantic Scholar citation commands.                                │
│ zbmath    zbMATH Open API commands.                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos refs problem`

```text

 Usage: erdos refs problem [OPTIONS] PROBLEM_ID

 List references for a problem.

 Example: erdos refs problem 6

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID to list references for.       │
│                                     [required]                               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos refs s2`

```text

 Usage: erdos refs s2 [OPTIONS] COMMAND [ARGS]...

 Semantic Scholar citation commands.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ citations    Get citation contexts for a paper.                              │
│ cited-by     List papers that cite the given paper (no context snippets).    │
│ references   List papers referenced by the given paper (outgoing citations). │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos refs s2 citations`

```text

 Usage: erdos refs s2 citations [OPTIONS] IDENTIFIER

 Get citation contexts for a paper.

 Returns papers that cite the given paper, with intent classification
 and context snippets showing WHY each paper cites this one.

 Examples:
     erdos refs s2 citations "10.4007/annals.2008.167.481"
     erdos refs s2 citations "math/0404188" --limit 20

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    identifier      TEXT  DOI, arXiv ID, or S2 paper ID. [required]         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --limit          INTEGER RANGE [1<=x<=1000]  Maximum citations to return.    │
│                                              [default: 10]                   │
│ --help   -h                                  Show this message and exit.     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos refs s2 cited-by`

```text

 Usage: erdos refs s2 cited-by [OPTIONS] IDENTIFIER

 List papers that cite the given paper (no context snippets).

 Faster than 'citations' when you just need the list of citing papers.

 Examples:
     erdos refs s2 cited-by "10.4007/annals.2008.167.481"
     erdos refs s2 cited-by "2301.00001" --limit 50

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    identifier      TEXT  DOI, arXiv ID, or S2 paper ID. [required]         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --limit          INTEGER RANGE [1<=x<=1000]  Maximum citing papers to        │
│                                              return.                         │
│                                              [default: 10]                   │
│ --help   -h                                  Show this message and exit.     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos refs s2 references`

```text

 Usage: erdos refs s2 references [OPTIONS] IDENTIFIER

 List papers referenced by the given paper (outgoing citations).

 Shows what papers this work cites, with intent and context when available.

 Examples:
     erdos refs s2 references "10.4007/annals.2008.167.481"
     erdos refs s2 references "math/0404188" --limit 25

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    identifier      TEXT  DOI, arXiv ID, or S2 paper ID. [required]         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --limit          INTEGER RANGE [1<=x<=1000]  Maximum references to return.   │
│                                              [default: 10]                   │
│ --help   -h                                  Show this message and exit.     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos refs zbmath`

```text

 Usage: erdos refs zbmath [OPTIONS] [IDENTIFIER] COMMAND [ARGS]...

 zbMATH Open API commands.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   identifier      [IDENTIFIER]  DOI to look up (e.g.,                        │
│                                 '10.4007/annals.2008.167.481').              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --zbl               TEXT                        zbMATH ID (e.g.,             │
│                                                 '1191.11025').               │
│ --title             TEXT                        Title keywords to search.    │
│ --msc               TEXT                        MSC code to search (e.g.,    │
│                                                 '11B05').                    │
│ --limit             INTEGER RANGE [1<=x<=1000]  Maximum results for search.  │
│                                                 [default: 20]                │
│ --year-min          INTEGER                     Minimum publication year     │
│                                                 (requires --msc).            │
│ --year-max          INTEGER                     Maximum publication year     │
│                                                 (requires --msc).            │
│ --help      -h                                  Show this message and exit.  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research`

```text

 Usage: erdos research [OPTIONS] COMMAND [ARGS]...

 Manage per-problem research workspace and state.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ init         Initialize the research workspace for a problem.                │
│ open         Print the absolute path to the per-problem research workspace.  │
│ note         Append a note to the per-problem scratchpad.                    │
│ status       Show a minimal dashboard for the research workspace.            │
│ fmt          Rewrite YAML records into canonical formatting.                 │
│ validate     Validate all YAML records in the workspace.                     │
│ synthesize   Generate/update `SYNTHESIS.md` deterministically (no LLM).      │
│ lead         Manage leads.                                                   │
│ hypothesis   Manage hypotheses.                                              │
│ task         Manage tasks.                                                   │
│ attempt      Manage attempts.                                                │
│ exa          Exa Research API integration.                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research attempt`

```text

 Usage: erdos research attempt [OPTIONS] COMMAND [ARGS]...

 Manage attempts.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ log    Log an attempt record.                                                │
│ list   List attempt records.                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research attempt list`

```text

 Usage: erdos research attempt list [OPTIONS] PROBLEM_ID

 List attempt records.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --result          [failed|partial|success]                                   │
│ --help    -h                                Show this message and exit.      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research attempt log`

```text

 Usage: erdos research attempt log [OPTIONS] PROBLEM_ID

 Log an attempt record.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --result                      [failed|partial|succ  [required]            │
│                                  ess]                                        │
│ *  --summary                     TEXT                  [required]            │
│    --kind                        [lean_loop|manual]    [default: lean_loop]  │
│    --lean-file                   TEXT                                        │
│    --loop-run-log,--lo…          TEXT                                        │
│    --help                -h                            Show this message and │
│                                                        exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research exa`

```text

 Usage: erdos research exa [OPTIONS] COMMAND [ARGS]...

 Exa Research API integration.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ search   Search Exa Research API for relevant literature.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research exa search`

```text

 Usage: erdos research exa search [OPTIONS] PROBLEM_ID QUERY

 Search Exa Research API for relevant literature.

 Examples:
 erdos research exa search 6 "What approaches have been tried for sum-free
 sets?"
 erdos research exa search 42 "Progress on arithmetic progressions"
 --max-results 10
 erdos research exa search 124 "Graph coloring bounds" --save-leads

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
│ *    query           TEXT           Natural language research query          │
│                                     [required]                               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --max-results          INTEGER  Maximum number of sources to return          │
│                                 [default: 5]                                 │
│ --save-leads                    Auto-create lead records from results        │
│ --help         -h               Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research fmt`

```text

 Usage: erdos research fmt [OPTIONS] PROBLEM_ID

 Rewrite YAML records into canonical formatting.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research hypothesis`

```text

 Usage: erdos research hypothesis [OPTIONS] COMMAND [ARGS]...

 Manage hypotheses.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ add      Add a hypothesis record.                                            │
│ list     List hypothesis records.                                            │
│ update   Update a hypothesis record.                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research hypothesis add`

```text

 Usage: erdos research hypothesis add [OPTIONS] PROBLEM_ID

 Add a hypothesis record.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --statement           TEXT                      Hypothesis statement      │
│                                                    [required]                │
│    --status              [active|refuted|proven|i  [default: active]         │
│                          ncorporated]                                        │
│    --confidence          [low|medium|high]         [default: medium]         │
│    --notes               TEXT                                                │
│    --help        -h                                Show this message and     │
│                                                    exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research hypothesis list`

```text

 Usage: erdos research hypothesis list [OPTIONS] PROBLEM_ID

 List hypothesis records.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --status          [active|refuted|proven|incor                               │
│                   porated]                                                   │
│ --help    -h                                    Show this message and exit.  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research hypothesis update`

```text

 Usage: erdos research hypothesis update [OPTIONS] PROBLEM_ID HYP_ID

 Update a hypothesis record.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
│ *    hyp_id          TEXT           Hypothesis ID (filename stem) [required] │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --status              [active|refuted|proven|inc                             │
│                       orporated]                                             │
│ --confidence          [low|medium|high]                                      │
│ --notes               TEXT                                                   │
│ --help        -h                                  Show this message and      │
│                                                   exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research init`

```text

 Usage: erdos research init [OPTIONS] PROBLEM_ID

 Initialize the research workspace for a problem.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research lead`

```text

 Usage: erdos research lead [OPTIONS] COMMAND [ARGS]...

 Manage leads.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ add      Add a lead record.                                                  │
│ list     List lead records.                                                  │
│ update   Update a lead record.                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research lead add`

```text

 Usage: erdos research lead add [OPTIONS] PROBLEM_ID

 Add a lead record.

 Optionally enrich with metadata from external APIs:
 - --fetch-citations: Add Semantic Scholar citation intent to notes
 - --fetch-msc: Add zbMATH MSC codes as tags (requires DOI)

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --title                    TEXT                   Lead title [required]   │
│    --doi                      TEXT                                           │
│    --arxiv-id                 TEXT                                           │
│    --url                      TEXT                                           │
│    --status                   [new|investigating|pr  [default: new]          │
│                               omising|dead_end|inco                          │
│                               rporated]                                      │
│    --priority                 [low|medium|high]      [default: medium]       │
│    --notes                    TEXT                                           │
│    --fetch-citations                                 Fetch citation intent   │
│                                                      from Semantic Scholar   │
│                                                      (SPEC-030).             │
│    --fetch-msc                                       Fetch MSC codes from    │
│                                                      zbMATH (SPEC-031).      │
│                                                      Requires DOI.           │
│    --help             -h                             Show this message and   │
│                                                      exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research lead list`

```text

 Usage: erdos research lead list [OPTIONS] PROBLEM_ID

 List lead records.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --status            [new|investigating|promisin                              │
│                     g|dead_end|incorporated]                                 │
│ --priority          [low|medium|high]                                        │
│ --help      -h                                   Show this message and exit. │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research lead update`

```text

 Usage: erdos research lead update [OPTIONS] PROBLEM_ID LEAD_ID

 Update a lead record.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
│ *    lead_id         TEXT           Lead ID (filename stem) [required]       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --status            [new|investigating|promisin                              │
│                     g|dead_end|incorporated]                                 │
│ --priority          [low|medium|high]                                        │
│ --notes             TEXT                                                     │
│ --help      -h                                   Show this message and exit. │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research note`

```text

 Usage: erdos research note [OPTIONS] PROBLEM_ID TEXT_ARG

 Append a note to the per-problem scratchpad.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
│ *    text_arg        TEXT           Note text, or '-' to read from stdin     │
│                                     [required]                               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research open`

```text

 Usage: erdos research open [OPTIONS] PROBLEM_ID

 Print the absolute path to the per-problem research workspace.

 This command intentionally does not require the workspace to exist yet.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research status`

```text

 Usage: erdos research status [OPTIONS] PROBLEM_ID

 Show a minimal dashboard for the research workspace.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research synthesize`

```text

 Usage: erdos research synthesize [OPTIONS] PROBLEM_ID

 Generate/update `SYNTHESIS.md` deterministically (no LLM).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research task`

```text

 Usage: erdos research task [OPTIONS] COMMAND [ARGS]...

 Manage tasks.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ add      Add a task record.                                                  │
│ list     List task records.                                                  │
│ update   Update a task record.                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research task add`

```text

 Usage: erdos research task add [OPTIONS] PROBLEM_ID

 Add a task record.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --title             TEXT                       Task title [required]      │
│    --status            [todo|doing|blocked|done]  [default: todo]            │
│    --priority          [low|medium|high]          [default: medium]          │
│    --help      -h                                 Show this message and      │
│                                                   exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research task list`

```text

 Usage: erdos research task list [OPTIONS] PROBLEM_ID

 List task records.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --status            [todo|doing|blocked|done]                                │
│ --priority          [low|medium|high]                                        │
│ --help      -h                                 Show this message and exit.   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research task update`

```text

 Usage: erdos research task update [OPTIONS] PROBLEM_ID TASK_ID

 Update a task record.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
│ *    task_id         TEXT           Task ID (filename stem) [required]       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --status            [todo|doing|blocked|done]                                │
│ --priority          [low|medium|high]                                        │
│ --help      -h                                 Show this message and exit.   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos research validate`

```text

 Usage: erdos research validate [OPTIONS] PROBLEM_ID

 Validate all YAML records in the workspace.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos search`

```text

 Usage: erdos search [OPTIONS] [QUERY] COMMAND [ARGS]...

 Search problem statements.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   query      [QUERY]  Search query (supports FTS5 syntax when index exists). │
│                       Not required when using --msc.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --limit             -n      INTEGER RANGE           Maximum results to       │
│                             [1<=x<=1000]            return                   │
│                                                     [default: 10]            │
│ --problem           -p      INTEGER                 Filter to a specific     │
│                                                     problem ID               │
│ --build-index                                       Build/rebuild the search │
│                                                     index                    │
│ --semantic          -s                              Use semantic (vector)    │
│                                                     search                   │
│ --hybrid                                            Hybrid search            │
│ --bm25-only                                         Force BM25-only search   │
│                                                     (no vectors)             │
│ --alpha                     FLOAT RANGE             Hybrid weight (0.0=BM25  │
│                             [0.0<=x<=1.0]           only, 1.0=semantic only, │
│                                                     default: 0.5)            │
│ --build-embeddings                                  Build/rebuild semantic   │
│                                                     embeddings               │
│ --embedding-model           TEXT                    Embedding model name     │
│                                                     [default:                │
│                                                     sentence-transformers/a… │
│ --msc                       TEXT                    Search zbMATH by MSC     │
│                                                     code (e.g., '11B05').    │
│                                                     Incompatible with other  │
│                                                     modes.                   │
│ --year-min                  INTEGER                 Minimum publication year │
│                                                     (for --msc mode)         │
│ --year-max                  INTEGER                 Maximum publication year │
│                                                     (for --msc mode)         │
│ --help              -h                              Show this message and    │
│                                                     exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos show`

```text

 Usage: erdos show [OPTIONS] PROBLEM_ID COMMAND [ARGS]...

 Show detailed problem information.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID to display. [required]        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos sync`

```text

 Usage: erdos sync [OPTIONS] COMMAND [ARGS]...

 Sync problem data from multiple sources.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ submodule    Update the teorth/erdosproblems submodule to latest remote.     │
│ website      Fetch structured data from erdosproblems.com and update local   │
│              dataset.                                                        │
│ proof        Extract proof repository links from the forum thread            │
│              (optionally verify).                                            │
│ statements   Sync Lean statement from DeepMind formal-conjectures.           │
│ all          Run all sync operations in sequence.                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos sync all`

```text

 Usage: erdos sync all [OPTIONS]

 Run all sync operations in sequence.

 By default, only updates the submodule. Specify --problems to sync
 specific problems from website, proof links, and statements.

 The operations run in this order:
 1. website - Update local dataset entries for selected problems
 2. proof - Extract proof repository links (discover-only)
 3. statements - Import Lean statements from DeepMind
 4. submodule - Update submodule + merge metadata into the local dataset

 Examples:
     erdos sync all                      # Update submodule only
     erdos sync all --problems 6,347     # Sync problems 6 and 347
     erdos sync all --skip-statements    # Skip Lean imports
     erdos sync all --problems 6 --dry-run

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --problems         -p      TEXT  Comma-separated problem IDs to sync         │
│                                  (default: submodule only).                  │
│ --lean-path                PATH  Path to Lean project (default:              │
│                                  formal/lean/).                              │
│ --force            -f            Overwrite local modifications.              │
│ --dry-run                        Run without writing to disk (still may read │
│                                  network if enabled).                        │
│ --no-network                     Use only cached data (submodule skipped).   │
│ --skip-submodule                 Skip submodule update.                      │
│ --skip-website                   Skip website fetch.                         │
│ --skip-proof                     Skip proof link extraction.                 │
│ --skip-statements                Skip Lean statement import.                 │
│ --help             -h            Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos sync proof`

```text

 Usage: erdos sync proof [OPTIONS] PROBLEM_ID

 Extract proof repository links from the forum thread (optionally verify).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID to extract proof links for    │
│                                     [required]                               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dry-run            Show what would be extracted without writing            │
│ --verify             Clone and verify proofs (runs untrusted build tooling)  │
│ --help     -h        Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos sync statements`

```text

 Usage: erdos sync statements [OPTIONS] PROBLEM_ID

 Sync Lean statement from DeepMind formal-conjectures.

 This wraps `erdos lean import` for use in the sync orchestration layer.
 The statement is imported from google-deepmind/formal-conjectures into
 formal/lean/Erdos/Problem{ID}.lean.

 Examples:
     erdos sync statements 347
     erdos sync statements 347 --force
     erdos sync statements 347 --dry-run

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID to sync statement for.        │
│                                     [required]                               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --path                  -p      PATH  Path to Lean project (default:         │
│                                       formal/lean/).                         │
│ --force                 -f            Overwrite local modifications.         │
│ --dry-run                             Show what would be done without        │
│                                       writing.                               │
│ --no-network                          Use only cached upstream data.         │
│ --skip-lean-validation                Do not run Lean check on imported      │
│                                       file.                                  │
│ --help                  -h            Show this message and exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos sync submodule`

```text

 Usage: erdos sync submodule [OPTIONS]

 Update the teorth/erdosproblems submodule to latest remote.

 By default, fetches updates from origin and checks out the latest commit.
 Use --check to only verify staleness without updating (useful for CI).

 Examples:
     erdos sync submodule           # Update to latest
     erdos sync submodule --check   # Check if stale (for CI)

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --check            Only check if submodule is stale (CI-friendly mode, exits │
│                    0/1)                                                      │
│ --help   -h        Show this message and exit.                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### `erdos sync website`

```text

 Usage: erdos sync website [OPTIONS] PROBLEM_ID

 Fetch structured data from erdosproblems.com and update local dataset.

 Extracts title, statement, tags, and references from the website.
 Updates data/problems_enriched.yaml with the merged data.

 Example:
     erdos sync website 6
     erdos sync website 6 --latex

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    problem_id      INTEGER RANGE  Problem ID to sync from                  │
│                                     erdosproblems.com                        │
│                                     [required]                               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --latex              Also fetch and save raw LaTeX source to                 │
│                      data/latex/<id>.tex                                     │
│ --dry-run            Show what would change without writing to disk          │
│ --help     -h        Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```
