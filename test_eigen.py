import pexpect
import time


def start_shell():
    child = pexpect.spawn(
        "./bin/Eigen_no_asan",
        encoding="utf-8",
        timeout=3,
    )
    child.expect_exact("> ")
    return child


def test_foreground_ctrl_c():
    child = start_shell()

    child.sendline("sleep 30")
    time.sleep(0.2)
    child.sendcontrol("c")
    child.expect_exact("> ")

    child.sendline("echo alive")
    child.expect("alive")
    child.expect_exact("> ")

    child.sendline("exit")
    child.expect(pexpect.EOF)


def test_foregound_ctrl_z():
    child = start_shell()

    child.sendline("sleep 30")
    time.sleep(0.2)
    child.sendcontrol("z")
    child.expect_exact("> ")


def test_background_completion():
    child = start_shell()

    child.sendline("sleep 0.2 &")
    child.expect_exact("> ")

    time.sleep(0.5)
    child.sendline("jobs")
    output = child.before
    child.expect_exact("> ")

    assert output is not None
    assert "RUNNING" not in output
