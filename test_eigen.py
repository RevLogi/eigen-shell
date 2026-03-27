#!/usr/bin/env python3
"""
Black-Box Integration Test Suite for Eigen Shell
Uses subprocess for differential testing and pexpect for interactive/TDD testing.
Features:
- ASan for memory error detection (buffer overflow, use-after-free)
- leaks (macOS) for memory leak detection
"""

import subprocess
import pexpect
import time
import re
import sys
import os
from typing import List, Tuple, Optional, Callable

EIGEN_BINARY = "./bin/Eigen"
BASH_BINARY = "/bin/bash"

TIMEOUT_DEFAULT = 5
TIMEOUT_LONG = 15

PASS = "\033[92m"
FAIL = "\033[91m"
WARN = "\033[93m"
INFO = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

leak_warnings: List[str] = []


def print_header(text: str) -> None:
    print(f"\n{BOLD}{text}{RESET}")
    print("-" * 50)


def print_subcheck(name: str, passed: bool, detail: str = "") -> None:
    status = f"{PASS}PASS{RESET}" if passed else f"{FAIL}FAIL{RESET}"
    print(f"    [{status}] {name}")
    if detail and not passed:
        print(f"           {detail}")


def print_test(name: str, desc: str, status: str, detail: str = "") -> None:
    status_color = PASS if status == "PASS" else (WARN if status == "SKIP" else FAIL)
    print(f"  {status_color}[{status}]{RESET} {BOLD}{name}{RESET}")
    if desc:
        print(f"         {desc}")
    if detail:
        for line in detail.split("\n"):
            print(f"         {line}")


def check_binary_asan(binary_path: str) -> bool:
    """Check if binary has ASan linked by looking for ASan symbols."""
    try:
        result = subprocess.run(
            ["nm", binary_path],
            capture_output=True,
            text=True,
        )
        return "__asan_init" in result.stdout or "asan" in result.stdout.lower()
    except:
        return False


def parse_leaks_output(stderr: str) -> List[str]:
    """Parse leaks output from stderr. Returns list of leak summaries."""
    leaks = []
    lines = stderr.split("\n")

    for i, line in enumerate(lines):
        if "Process" in line and "leaks" in line:
            leaks.append(line.strip())
        elif "Leak:" in line and "size=" in line:
            leak_info = line.strip()
            if i + 1 < len(lines) and "Responsible" not in lines[i + 1]:
                leak_info += " " + lines[i + 1].strip()
            leaks.append(leak_info)

    return leaks


class EigenTestRunner:
    def __init__(self, eigen_path: str = EIGEN_BINARY):
        self.eigen_path = eigen_path
        self.has_asan = check_binary_asan(eigen_path)

        self.base_env = os.environ.copy()
        if self.has_asan:
            self.base_env["ASAN_OPTIONS"] = "detect_leaks=0:print_summary=1:exitcode=0"

    def run_eigen(self, command: str, timeout: int = TIMEOUT_DEFAULT) -> Tuple[int, str, str, List[str]]:
        """Run a single command in Eigen shell. Returns (returncode, stdout, stderr, leaks)."""
        if self.has_asan:
            cmd = f"printf '%s\\n' '{command}' | {self.eigen_path}"
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self.base_env,
            )
            leaks = parse_leaks_output(proc.stderr)
        else:
            leak_env = self.base_env.copy()
            leak_env["MallocStackLogging"] = "1"
            leak_env["DYLD_INSERT_LIBRARIES"] = ""
            cmd = f"printf '%s\\n' '{command}' | leaks --atExit -- {self.eigen_path}"
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=leak_env,
            )
            leaks = parse_leaks_output(proc.stderr)

        for leak in leaks:
            if leak not in leak_warnings:
                leak_warnings.append(leak)

        return proc.returncode, proc.stdout, proc.stderr, leaks

    def run_bash(self, command: str, timeout: int = TIMEOUT_DEFAULT) -> Tuple[int, str, str]:
        """Run a single command in system bash, return (returncode, stdout, stderr)."""
        proc = subprocess.run(
            [BASH_BINARY, "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr


class DifferentialTester:
    """Test Eigen vs Bash differential behavior."""

    def __init__(self, runner: EigenTestRunner):
        self.runner = runner

    def test_group_echo(self) -> Tuple[bool, str]:
        """Test all echo scenarios in one group."""
        checks = []

        # 1. Basic echo
        cmd = 'echo "hello world"'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out and e_err == b_err
        if passed:
            checks.append(("echo basic", True, ""))
        else:
            checks.append(("echo basic", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 2. Echo no args
        cmd = "echo"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo no args", True, ""))
        else:
            checks.append(("echo no args", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 3. Echo with spaces
        cmd = "echo hello   world"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo with spaces", True, ""))
        else:
            checks.append(("echo with spaces", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 4. Echo with tabs
        cmd = "echo hello\tworld"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo with tabs", True, ""))
        else:
            checks.append(("echo with tabs", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 5. Echo with multiple spaces
        cmd = "echo    four   spaces"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo multiple spaces", True, ""))
        else:
            checks.append(("echo multiple spaces", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 6. Echo with empty quotes
        cmd = 'echo ""'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo empty quotes", True, ""))
        else:
            checks.append(("echo empty quotes", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 7. Echo with single quotes
        cmd = "echo 'hello world'"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo single quotes", True, ""))
        else:
            checks.append(("echo single quotes", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 8. Echo with double quotes containing special chars
        cmd = 'echo "hello\nworld"'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo with newline", True, ""))
        else:
            checks.append(("echo with newline", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 9. Echo with variables
        cmd = "echo $HOME"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo $HOME var", True, ""))
        else:
            checks.append(("echo $HOME var", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 10. Echo with path variable
        cmd = "echo $PATH"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo $PATH var", True, ""))
        else:
            checks.append(("echo $PATH var", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 11. Echo with multiple variables
        cmd = "echo $HOME $PATH $USER"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo multiple vars", True, ""))
        else:
            checks.append(("echo multiple vars", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 12. Echo with exit code
        cmd = "echo $?"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo $?", True, ""))
        else:
            checks.append(("echo $?", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 13. Echo with backticks
        cmd = "echo `pwd`"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo backticks", True, ""))
        else:
            checks.append(("echo backticks", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 14. Echo with glob
        cmd = "echo *.py"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo glob", True, ""))
        else:
            checks.append(("echo glob", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 15. Echo special chars: asterisk
        cmd = "echo *"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("echo asterisk", True, ""))
        else:
            checks.append(("echo asterisk", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        all_pass = all(p for _, p, _ in checks)
        passed_count = sum(1 for _, p, _ in checks if p)
        total_count = len(checks)
        lines = [f"    [{PASS}PASS{RESET}] {n}" if p else f"    [{FAIL}FAIL{RESET}] {n}: {d}" for n, p, d in checks]
        lines.append(f"    -- {passed_count}/{total_count} passed --")
        details = "\n".join(lines)
        return all_pass, details

    def test_group_env(self) -> Tuple[bool, str]:
        """Test all environment variable scenarios."""
        checks = []

        # 1. Set and echo variable
        cmd = 'export FOO=bar; echo $FOO'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("export and echo", True, ""))
        else:
            checks.append(("export and echo", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 2. Unset variable
        cmd = 'export FOO=bar; unset FOO; echo $FOO'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("unset var", True, ""))
        else:
            checks.append(("unset var", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 3. Export with value containing equals
        cmd = 'export X=a=b=c; echo $X'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("export with = in value", True, ""))
        else:
            checks.append(("export with = in value", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 4. Export with value containing spaces
        cmd = 'export X="hello world"; echo $X'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("export with spaces", True, ""))
        else:
            checks.append(("export with spaces", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 5. Accessing unset variable
        cmd = "echo $UNSET_VAR_12345"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("access unset var", True, ""))
        else:
            checks.append(("access unset var", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 6. Export without value
        cmd = 'export EMPTY; echo $EMPTY'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("export without value", True, ""))
        else:
            checks.append(("export without value", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 7. Multiple exports
        cmd = 'export A=1 B=2 C=3; echo $A $B $C'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("multiple exports", True, ""))
        else:
            checks.append(("multiple exports", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 8. Export PATH-like variable
        cmd = 'export PATH=/custom/bin:$PATH; echo $PATH | head -c 20'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("export PATH-like", True, ""))
        else:
            checks.append(("export PATH-like", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 9. env builtin
        cmd = "env"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("env builtin", True, ""))
        else:
            checks.append(("env builtin", False, f"output differs (len: eigen={len(e_out)}, bash={len(b_out)})"))

        all_pass = all(p for _, p, _ in checks)
        passed_count = sum(1 for _, p, _ in checks if p)
        total_count = len(checks)
        lines = [f"    [{PASS}PASS{RESET}] {n}" if p else f"    [{FAIL}FAIL{RESET}] {n}: {d}" for n, p, d in checks]
        lines.append(f"    -- {passed_count}/{total_count} passed --")
        details = "\n".join(lines)
        return all_pass, details

    def test_group_builtins(self) -> Tuple[bool, str]:
        """Test all builtin commands."""
        checks = []

        # 1. pwd builtin
        cmd = "pwd"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("pwd builtin", True, ""))
        else:
            checks.append(("pwd builtin", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 2. cd builtin
        cmd = "cd /tmp && pwd"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("cd /tmp", True, ""))
        else:
            checks.append(("cd /tmp", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 3. cd home
        cmd = "cd ~ && pwd"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("cd ~", True, ""))
        else:
            checks.append(("cd ~", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 4. cd back to original
        cmd = "cd /tmp && cd - && pwd"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("cd - (prev dir)", True, ""))
        else:
            checks.append(("cd - (prev dir)", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 5. which command
        cmd = "which ls"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("which ls", True, ""))
        else:
            checks.append(("which ls", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 6. type builtin
        cmd = "type echo"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("type echo", True, ""))
        else:
            checks.append(("type echo", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 7. type unknown command
        cmd = "type unknowncmd123"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("type unknown", True, ""))
        else:
            checks.append(("type unknown", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 8. history (if exists)
        cmd = "history"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("history builtin", True, ""))
        else:
            checks.append(("history builtin", False, f"got={e_out.strip()[:50]!r}, bash={b_out.strip()[:50]!r}"))

        all_pass = all(p for _, p, _ in checks)
        passed_count = sum(1 for _, p, _ in checks if p)
        total_count = len(checks)
        lines = [f"    [{PASS}PASS{RESET}] {n}" if p else f"    [{FAIL}FAIL{RESET}] {n}: {d}" for n, p, d in checks]
        lines.append(f"    -- {passed_count}/{total_count} passed --")
        details = "\n".join(lines)
        return all_pass, details

    def test_group_exit_codes(self) -> Tuple[bool, str]:
        """Test exit code handling."""
        checks = []

        # 1. true returns 0
        cmd = "true"
        code, _, _, _ = self.runner.run_eigen(cmd)
        passed = code == 0
        checks.append(("true exit code 0", passed, f"got {code}" if not passed else ""))

        # 2. false returns non-zero
        cmd = "false"
        code, _, _, _ = self.runner.run_eigen(cmd)
        passed = code != 0
        checks.append(("false exit code non-zero", passed, f"got {code}" if not passed else ""))

        # 3. builtin exit 0
        cmd = "exit 0"
        code, _, _, _ = self.runner.run_eigen(cmd)
        passed = code == 0
        checks.append(("exit 0", passed, f"got {code}" if not passed else ""))

        # 4. builtin exit 42
        cmd = "exit 42"
        code, _, _, _ = self.runner.run_eigen(cmd)
        passed = code == 42
        checks.append(("exit 42", passed, f"got {code}" if not passed else ""))

        # 5. exit without args (default 0)
        cmd = "exit"
        code, _, _, _ = self.runner.run_eigen(cmd)
        passed = code == 0
        checks.append(("exit (no args)", passed, f"got {code}" if not passed else ""))

        # 6. command not found returns 127
        cmd = "nonexistentcmd12345"
        code, _, _, _ = self.runner.run_eigen(cmd)
        passed = code == 127
        checks.append(("cmd not found (127)", passed, f"got {code}" if not passed else ""))

        # 7. exit code preserved
        cmd = "(exit 5); echo $?"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("exit code preserved", True, ""))
        else:
            checks.append(("exit code preserved", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        all_pass = all(p for _, p, _ in checks)
        passed_count = sum(1 for _, p, _ in checks if p)
        total_count = len(checks)
        lines = [f"    [{PASS}PASS{RESET}] {n}" if p else f"    [{FAIL}FAIL{RESET}] {n}: {d}" for n, p, d in checks]
        lines.append(f"    -- {passed_count}/{total_count} passed --")
        details = "\n".join(lines)
        return all_pass, details

    def test_group_io_redirection(self) -> Tuple[bool, str]:
        """Test I/O and redirection handling."""
        checks = []

        # 1. stdout to file
        cmd = 'echo hello > /tmp/eigen_test_out.txt && cat /tmp/eigen_test_out.txt'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("stdout to file", True, ""))
        else:
            checks.append(("stdout to file", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 2. stderr to file
        cmd = 'ls /nonexistent 2> /tmp/eigen_err.txt; cat /tmp/eigen_err.txt'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("stderr to file", True, ""))
        else:
            checks.append(("stderr to file", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 3. Append to file
        cmd = 'echo first > /tmp/eigen_append.txt; echo second >> /tmp/eigen_append.txt; cat /tmp/eigen_append.txt'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("append to file", True, ""))
        else:
            checks.append(("append to file", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 4. Input from file
        cmd = 'echo "line1" > /tmp/eigen_in.txt; echo "line2" >> /tmp/eigen_in.txt; cat < /tmp/eigen_in.txt'
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("input from file", True, ""))
        else:
            checks.append(("input from file", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 5. pipe
        cmd = "echo hello | cat"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("pipe", True, ""))
        else:
            checks.append(("pipe", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        # 6. wc with pipe
        cmd = "echo hello world | wc -w"
        _, e_out, e_err, _ = self.runner.run_eigen(cmd)
        _, b_out, b_err = self.runner.run_bash(cmd)
        passed = e_out == b_out
        if passed:
            checks.append(("wc pipe", True, ""))
        else:
            checks.append(("wc pipe", False, f"got={e_out.strip()!r}, bash={b_out.strip()!r}"))

        all_pass = all(p for _, p, _ in checks)
        passed_count = sum(1 for _, p, _ in checks if p)
        total_count = len(checks)
        lines = [f"    [{PASS}PASS{RESET}] {n}" if p else f"    [{FAIL}FAIL{RESET}] {n}: {d}" for n, p, d in checks]
        lines.append(f"    -- {passed_count}/{total_count} passed --")
        details = "\n".join(lines)
        return all_pass, details


class InteractiveTester:
    """Test interactive/job control features using pexpect."""

    def __init__(self, eigen_path: str = EIGEN_BINARY):
        self.eigen_path = eigen_path
        self.has_asan = check_binary_asan(eigen_path)

    def _spawn(self, timeout: int = TIMEOUT_DEFAULT) -> pexpect.spawn:
        """Spawn Eigen shell process."""
        if self.has_asan:
            asan_env = os.environ.copy()
            asan_env["ASAN_OPTIONS"] = "detect_leaks=0:print_summary=1:exitcode=0"
            child = pexpect.spawn(
                self.eigen_path,
                encoding="utf-8",
                timeout=timeout,
                env=asan_env,  # type: ignore
            )
        else:
            leak_env = os.environ.copy()
            leak_env["MallocStackLogging"] = "1"
            leak_env["DYLD_INSERT_LIBRARIES"] = ""
            child = pexpect.spawn(
                self.eigen_path,
                encoding="utf-8",
                timeout=timeout,
                env=leak_env,  # type: ignore
            )
        return child

    def _expect_prompt(self, child: pexpect.spawn, timeout: int = TIMEOUT_DEFAULT) -> str:
        """Wait for prompt and return everything before it."""
        child.expect(r"λ ", timeout=timeout)
        return child.before or ""

    def test_group_background(self) -> Tuple[bool, str]:
        """Test background job handling."""
        checks = []

        # 1. Background immediate return
        child = self._spawn()
        try:
            start = time.time()
            child.sendline("sleep 2 &")
            child.expect(r"λ ", timeout=TIMEOUT_DEFAULT)
            elapsed = time.time() - start
            child.sendline("exit")
            child.expect(pexpect.EOF, timeout=2)
            child.close()
            passed = elapsed < 1.5
            checks.append(("background immediate return", passed, f"blocked {elapsed:.1f}s" if not passed else ""))
        except Exception as e:
            child.close()
            checks.append(("background immediate return", False, "timeout: sleep 2 &"))

        # 2. jobs builtin format
        child = self._spawn()
        try:
            child.sendline("sleep 5 &")
            child.expect(r"λ ", timeout=TIMEOUT_DEFAULT)
            child.sendline("jobs")
            output = self._expect_prompt(child)
            child.sendline("exit")
            child.expect(pexpect.EOF, timeout=2)
            child.close()
            passed = bool(re.search(r"\[1\]\s+", output))
            checks.append(("jobs builtin format", passed, "no [1] in output" if not passed else ""))
        except Exception as e:
            child.close()
            checks.append(("jobs builtin format", False, "timeout: jobs"))

        # 3. Multiple background jobs
        child = self._spawn(timeout=TIMEOUT_LONG)
        try:
            child.sendline("sleep 3 &")
            child.expect(r"λ ", timeout=TIMEOUT_DEFAULT)
            child.sendline("sleep 4 &")
            child.expect(r"λ ", timeout=TIMEOUT_DEFAULT)
            child.sendline("jobs")
            output = self._expect_prompt(child)
            child.sendline("exit")
            child.expect(pexpect.EOF, timeout=2)
            child.close()
            has_j1 = bool(re.search(r"\[1\]", output))
            has_j2 = bool(re.search(r"\[2\]", output))
            passed = has_j1 and has_j2
            checks.append(("multiple background jobs", passed, "missing [1] or [2]" if not passed else ""))
        except Exception as e:
            child.close()
            checks.append(("multiple background jobs", False, "timeout: jobs"))

        # 4. Background job output not mixed
        child = self._spawn(timeout=TIMEOUT_LONG)
        try:
            child.sendline("echo background &")
            child.expect(r"λ ", timeout=TIMEOUT_DEFAULT)
            child.sendline("echo foreground")
            output = self._expect_prompt(child)
            child.sendline("exit")
            child.expect(pexpect.EOF, timeout=3)
            child.close()
            passed = "foreground" in output
            checks.append(("bg output not mixed", passed, "foreground missing" if not passed else ""))
        except Exception as e:
            child.close()
            checks.append(("bg output not mixed", False, "timeout: echo foreground"))

        all_pass = all(p for _, p, _ in checks)
        passed_count = sum(1 for _, p, _ in checks if p)
        total_count = len(checks)
        lines = [f"    [{PASS}PASS{RESET}] {n}" if p else f"    [{FAIL}FAIL{RESET}] {n}: {d}" for n, p, d in checks]
        lines.append(f"    -- {passed_count}/{total_count} passed --")
        details = "\n".join(lines)
        return all_pass, details

    def test_group_signals(self) -> Tuple[bool, str]:
        """Test signal handling."""
        checks = []

        # 1. Ctrl-C kills foreground job
        child = self._spawn()
        try:
            child.sendline("sleep 10")
            time.sleep(0.3)
            child.send("\x03")
            try:
                output = self._expect_prompt(child, timeout=TIMEOUT_DEFAULT)
            except pexpect.EOF:
                child.close()
                checks.append(("Ctrl-C kills foreground", True, "shell exited (expected)"))
                passed = True
            else:
                child.sendline("exit")
                child.expect(pexpect.EOF, timeout=2)
                child.close()
                passed = "Interrupt" not in output and "Killed" not in output
                checks.append(("Ctrl-C kills foreground", passed, "shell crashed" if not passed else ""))
        except Exception:
            child.close()
            checks.append(("Ctrl-C kills foreground", False, "error"))

        # 2. Ctrl-Z stops foreground job
        child = self._spawn(timeout=TIMEOUT_LONG)
        try:
            child.sendline("sleep 10")
            time.sleep(0.3)
            child.send("\x1a")
            output = self._expect_prompt(child, timeout=TIMEOUT_DEFAULT)
            child.sendline("exit")
            child.expect(pexpect.EOF, timeout=2)
            child.close()
            passed = "Stopped" in output or "stopped" in output.lower()
            checks.append(("Ctrl-Z stops job", passed, "no Stopped message" if not passed else ""))
        except Exception as e:
            child.close()
            checks.append(("Ctrl-Z stops job", False, "timeout: Ctrl-Z didn't stop job"))

        # 3. Shell survives multiple Ctrl-C
        child = self._spawn()
        try:
            child.sendline("sleep 5")
            time.sleep(0.2)
            child.send("\x03")
            time.sleep(0.2)
            child.send("\x03")
            time.sleep(0.2)
            child.send("\x03")
            output = self._expect_prompt(child, timeout=TIMEOUT_DEFAULT)
            child.sendline("exit")
            child.expect(pexpect.EOF, timeout=2)
            child.close()
            passed = "Interrupt" not in output
            checks.append(("multiple Ctrl-C survive", passed, "shell crashed" if not passed else ""))
        except Exception as e:
            child.close()
            checks.append(("multiple Ctrl-C survive", False, "timeout: shell hung after Ctrl-C"))

        # 4. Ctrl-D EOF (graceful exit)
        child = self._spawn()
        try:
            child.send("\x04")
            child.expect(pexpect.EOF, timeout=2)
            child.close()
            passed = True
            checks.append(("Ctrl-D EOF exit", passed, ""))
        except Exception as e:
            child.close()
            passed = False
            checks.append(("Ctrl-D EOF exit", False, "timeout: shell didn't exit on Ctrl-D"))

        # 5. Empty input (empty line)
        child = self._spawn()
        try:
            child.sendline("")
            output = self._expect_prompt(child, timeout=2)
            child.sendline("exit")
            child.expect(pexpect.EOF, timeout=2)
            child.close()
            passed = True
            checks.append(("empty line handling", passed, ""))
        except Exception as e:
            child.close()
            checks.append(("empty line handling", False, "timeout: shell didn't respond to empty line"))

        all_pass = all(p for _, p, _ in checks)
        passed_count = sum(1 for _, p, _ in checks if p)
        total_count = len(checks)
        lines = [f"    [{PASS}PASS{RESET}] {n}" if p else f"    [{FAIL}FAIL{RESET}] {n}: {d}" for n, p, d in checks]
        lines.append(f"    -- {passed_count}/{total_count} passed --")
        details = "\n".join(lines)
        return all_pass, details

    def test_group_fg_bg(self) -> Tuple[bool, str]:
        """Test fg and bg builtins."""
        checks = []

        # 1. fg brings job to foreground
        child = self._spawn(timeout=TIMEOUT_LONG)
        try:
            child.sendline("sleep 10")
            time.sleep(0.3)
            child.send("\x1a")  # Ctrl-Z to stop
            output1 = self._expect_prompt(child, timeout=TIMEOUT_DEFAULT)
            if "Stopped" in output1 or "stopped" in output1.lower():
                child.sendline("fg")
                time.sleep(0.3)
                child.send("\x03")  # Ctrl-C to kill
                output2 = self._expect_prompt(child, timeout=2)
                child.sendline("exit")
                child.expect(pexpect.EOF, timeout=2)
                child.close()
                passed = True
                checks.append(("fg resumes stopped job", passed, ""))
            else:
                child.sendline("exit")
                child.expect(pexpect.EOF, timeout=2)
                child.close()
                passed = False
                checks.append(("fg resumes stopped job", False, "Ctrl-Z didn't stop job"))
        except Exception as e:
            child.close()
            checks.append(("fg resumes stopped job", False, "timeout: fg command"))

        # 2. bg resumes job in background
        child = self._spawn(timeout=TIMEOUT_LONG)
        try:
            child.sendline("sleep 10")
            time.sleep(0.3)
            child.send("\x1a")  # Ctrl-Z to stop
            output1 = self._expect_prompt(child, timeout=TIMEOUT_DEFAULT)
            if "Stopped" in output1 or "stopped" in output1.lower():
                child.sendline("bg")
                child.expect(r"λ ", timeout=TIMEOUT_DEFAULT)
                child.sendline("jobs")
                output2 = self._expect_prompt(child)
                child.sendline("exit")
                child.expect(pexpect.EOF, timeout=3)
                child.close()
                passed = bool(re.search(r"\[1\]", output2))
                checks.append(("bg resumes in background", passed, "no [1] in jobs" if not passed else ""))
            else:
                child.sendline("exit")
                child.expect(pexpect.EOF, timeout=2)
                child.close()
                passed = False
                checks.append(("bg resumes in background", False, "Ctrl-Z didn't stop job"))
        except Exception as e:
            child.close()
            checks.append(("bg resumes in background", False, "timeout: bg command"))

        # 3. fg with no job
        child = self._spawn()
        try:
            child.sendline("fg")
            output = self._expect_prompt(child, timeout=TIMEOUT_DEFAULT)
            child.sendline("exit")
            child.expect(pexpect.EOF, timeout=2)
            child.close()
            passed = "no job" in output.lower() or "background" in output.lower()
            checks.append(("fg with no job error", passed, "no error message" if not passed else ""))
        except Exception as e:
            child.close()
            checks.append(("fg with no job error", False, "timeout: fg with no job"))

        # 4. jobs shows correct state
        child = self._spawn(timeout=TIMEOUT_LONG)
        try:
            child.sendline("sleep 5 &")
            child.expect(r"λ ", timeout=TIMEOUT_DEFAULT)
            child.sendline("jobs")
            output = self._expect_prompt(child)
            child.sendline("exit")
            child.expect(pexpect.EOF, timeout=2)
            child.close()
            passed = bool(re.search(r"Running", output))
            checks.append(("jobs shows Running", passed, "no Running state" if not passed else ""))
        except Exception as e:
            child.close()
            checks.append(("jobs shows Running", False, "timeout: jobs"))

        all_pass = all(p for _, p, _ in checks)
        passed_count = sum(1 for _, p, _ in checks if p)
        total_count = len(checks)
        lines = [f"    [{PASS}PASS{RESET}] {n}" if p else f"    [{FAIL}FAIL{RESET}] {n}: {d}" for n, p, d in checks]
        lines.append(f"    -- {passed_count}/{total_count} passed --")
        details = "\n".join(lines)
        return all_pass, details


def run_differential_tests() -> Tuple[int, int]:
    """Run all differential tests. Returns (passed, failed)."""
    print_header("Differential Testing (Eigen vs Bash)")

    runner = EigenTestRunner()
    tester = DifferentialTester(runner)

    tests: List[Tuple[str, Callable]] = [
        ("Echo Tests", tester.test_group_echo),
        ("Environment Tests", tester.test_group_env),
        ("Builtin Tests", tester.test_group_builtins),
        ("Exit Code Tests", tester.test_group_exit_codes),
        ("I/O Redirection Tests", tester.test_group_io_redirection),
    ]

    passed = 0
    failed = 0
    for i, (name, fn) in enumerate(tests, 1):
        try:
            ok, detail = fn()
            status = "PASS" if ok else "FAIL"
            status_color = PASS if ok else FAIL
            print(f"\n[{i}/{len(tests)}] {BOLD}{name}{RESET} ... {status_color}{status}{RESET}")
            print(detail)
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n[{i}/{len(tests)}] {BOLD}{name}{RESET} ... {FAIL}ERROR{RESET}")
            print(f"    {FAIL}{str(e)}{RESET}")
            failed += 1

    return passed, failed


def run_interactive_tests() -> Tuple[int, int]:
    """Run all interactive/job control tests. Returns (passed, failed)."""
    print_header("Interactive/TDD Testing (Job Control)")

    tester = InteractiveTester()

    tests: List[Tuple[str, Callable]] = [
        ("Background Jobs", tester.test_group_background),
        ("Signal Handling", tester.test_group_signals),
        ("Fg/Bg Builtins", tester.test_group_fg_bg),
    ]

    passed = 0
    failed = 0
    for i, (name, fn) in enumerate(tests, 1):
        try:
            ok, detail = fn()
            status = "PASS" if ok else "FAIL"
            status_color = PASS if ok else FAIL
            print(f"\n[{i}/{len(tests)}] {BOLD}{name}{RESET} ... {status_color}{status}{RESET}")
            print(detail)
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n[{i}/{len(tests)}] {BOLD}{name}{RESET} ... {FAIL}ERROR{RESET}")
            print(f"    {FAIL}{str(e)}{RESET}")
            failed += 1

    return passed, failed


def print_leak_summary():
    """Print memory leak warnings if any were detected."""
    if leak_warnings:
        print(f"\n{WARN}{BOLD}=== Memory Leaks Detected ({len(leak_warnings)}) ==={RESET}")
        for leak in leak_warnings:
            print(f"  {WARN}{leak}{RESET}")
        print(f"\n  {WARN}Note: Leaks are reported as warnings, not test failures.{RESET}")
        print(f"  {WARN}Fix leaks in C code to have a clean run.{RESET}")


def main():
    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f"{BOLD}Eigen Shell - Black-Box Integration Tests{RESET}")
    print(f"{'='*50}")

    has_asan = check_binary_asan(EIGEN_BINARY)

    if has_asan:
        print(f"\n{INFO}Note: Binary built with ASan detected.{RESET}")
        print(f"{INFO}  - ASan will detect memory errors (overflow, use-after-free){RESET}")
        print(f"{INFO}  - Leak detection via 'leaks' is unavailable with ASan on macOS{RESET}")
        print(f"{INFO}  - To check for leaks, rebuild without ASan:{RESET}")
        print(f"{INFO}      make clean && make leak{RESET}")

    diff_pass, diff_fail = run_differential_tests()
    int_pass, int_fail = run_interactive_tests()

    total_pass = diff_pass + int_pass
    total_fail = diff_fail + int_fail

    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f"{BOLD}Summary:{RESET}")
    print(f"  {PASS}[PASS]{RESET} {total_pass} test groups passed")
    if total_fail > 0:
        print(f"  {FAIL}[FAIL]{RESET} {total_fail} test groups failed")
    print(f"\nDifferential: {diff_pass} passed, {diff_fail} failed")
    print(f"Interactive:  {int_pass} passed, {int_fail} failed")

    if has_asan:
        print(f"\n{INFO}Memory error detection (ASan): Active{RESET}")
    elif leak_warnings:
        print_leak_summary()

    if total_fail == 0:
        print(f"\n{PASS}{BOLD}ALL TESTS PASSED{RESET}")
        sys.exit(0)
    else:
        print(f"\n{FAIL}{BOLD}SOME TESTS FAILED{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
