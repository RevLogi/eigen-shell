# Eigen Shell

A lightweight, custom Unix-like shell written in C from scratch to explore OS concepts, system calls, and low-level memory management.

## Features & To-Do List

### Core Execution & Memory
- [x] Basic REPL loop with standard Fork-Exec-Wait process execution.
- [x] Script execution (batch mode) with support for ignoring `#` comments.
- [x] Lexical analysis with basic double-quote (`""`) state handling.
- [x] Robust memory model using deep copy (`strdup`) and clean garbage collection.

### Built-ins & Environment
- [x] Custom dynamic Hash Map built from scratch for environment variables.
- [x] `export` command with OS environment synchronization (`setenv`).
- [x] `cd` command supporting `~` (home) and `-` (previous directory).
- [x] Basic utilities: `help`, `clear`, and `exit`.
- [x] Variable expansion (`$VAR`) supporting suffix concatenation.

### Interactive CLI (via Linenoise)
- [x] Command history saving and loading (`history.txt`).
- [x] Tab-completion for basic built-in commands.
- [x] Contextual syntax hints for specific commands.

### 🚧 Roadmap (Pending)
- [ ] Extend `~` (tilde) expansion globally (e.g., `ls ~/Documents`).
- [ ] Implement Inter-Process Communication (Pipes `|`).
- [ ] Implement I/O Redirection (`>`, `<`, `>>`).
- [ ] Add Signal Handling (intercept `SIGINT`/`SIGTSTP` to protect the shell).
- [ ] Implement Background Jobs & Job Control (`&`, `jobs`, `fg`, `bg`).
