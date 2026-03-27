# Eigen Shell

Eigen is a small Unix-like shell written in C. Its purpose is to demonstrate a
basic shell loop and the `fork` / `exec` / `wait` process model.

## MVP Features

- [x] Interactive command prompt
- [x] External command execution with `fork` and `execvp`
- [x] Basic argument splitting and double-quoted arguments
- [x] Script-file execution with whole-line `#` comments
- [x] Core built-ins: `cd` and `exit`
- [x] Extra built-ins: `export`, `jobs`, `help`, and `clear`
- [x] Simple `$VAR` expansion
- [x] Command history and basic completion

## Basic Job Control

Job control is intentionally limited to one process per job. The existing
implementation is close to complete and remains part of the project scope:

- [x] Start a background command with `&`
- [x] Fixed-size job table and basic `jobs` output
- [x] Initial `SIGCHLD`-based completion tracking
- [ ] Track Running, Stopped, and Done states reliably
- [ ] Restore terminal control after every foreground job
- [ ] Resume the latest job with `fg` and `bg`
- [ ] Keep the shell alive after Ctrl-C and Ctrl-Z

Pipeline jobs and full POSIX job-control semantics are not required.

## Build and Run

```sh
make
./bin/Eigen
```

Run a script with:

```sh
./bin/Eigen path/to/script.eigen
```

## Out of Scope

Pipes, I/O redirection, multi-process jobs, full quote/escape rules, command
chaining, globbing, command substitution, and POSIX/Bash compatibility are
intentionally out of scope.

The project is complete when the MVP features work reliably; the items above do
not need to become a roadmap.

See [`docs/PROJECT_GUIDE.md`](../docs/PROJECT_GUIDE.md) for the short completion
checklist.
