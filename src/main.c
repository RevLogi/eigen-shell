#include <errno.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

#include "include/builtins.h"
#include "include/eigen.h"
#include "include/hashmap.h"
#include "include/job.h"
#include "include/linenoise.h"

MyHashMap *shell_env = NULL;

static bool shell_interactive = false;
static int shell_terminal = STDIN_FILENO;
static pid_t shell_pgid = -1;

typedef void (*sig_handler)(int);

static void set_signal(int sig, sig_handler handler) {
    struct sigaction sa = {0};
    sa.sa_handler = handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;
    if (sigaction(sig, &sa, NULL) < 0) {
        perror("sigaction");
        exit(EXIT_FAILURE);
    }
}

static void ignore_signal(int sig) { set_signal(sig, SIG_IGN); }
static void install_sigchld_handler(void) { set_signal(SIGCHLD, sigchld_handler); }
static void restore_signal(int sig) { set_signal(sig, SIG_DFL); }

static void init_job_control(void) {
    shell_terminal = STDIN_FILENO;

    // Start in background
    while (tcgetpgrp(shell_terminal) != getpgrp()) {
        kill(-getpgrp(), SIGTTIN);
    }

    ignore_signal(SIGINT);
    ignore_signal(SIGQUIT);
    ignore_signal(SIGTSTP);
    ignore_signal(SIGTTIN);
    ignore_signal(SIGTTOU);
    install_sigchld_handler();

    pid_t pid = getpid();
    if (getpgrp() != pid) {
        if (setpgid(0, 0) < 0) {
            perror("setpgid");
            exit(EXIT_FAILURE);
        }
    }

    shell_pgid = getpgrp();

    if (tcsetpgrp(shell_terminal, shell_pgid) < 0) {
        perror("tcgetpgrp");
        exit(EXIT_FAILURE);
    }
}

int main(int argc, char **argv) {
    // Initialize shell env
    shell_env = initial();

    shell_interactive = (argc == 1) && isatty(STDIN_FILENO);

    if (shell_interactive) {
        init_job_control();
    }

    // Batch mode
    if (argc > 1) {
        return run_script(argv[1]);
    }

    // Run command loop.
    eigen_loop();

    free_exports(shell_env);
    return EXIT_SUCCESS;
}

int run_script(char *filename) {
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        perror("Wrong filename");
        return 1;
    }

    char *line = NULL;
    size_t len = 0;

    // Iterate through the file line by line.
    // getline() automatically handles buffer reallocation.
    while (getline(&line, &len, fp) != -1) {
        // getline() inlude the trailing newline.
        // execvp() treats it as part of the command name.
        // We use strcspn to locate and delete it.
        line[strcspn(line, "\n")] = 0;

        // Rationale: Skip command to allow annotation.
        if (line[0] == '#') continue;

        char **args = eigen_split_line(line);
        // TODO:
        int status = eigen_execute(args, line);

        free_tokens(args);
    }

    free(line);
    fclose(fp);
    return 0;
}

/* * Execute a program.
 * * Uses the standard Fork-Exec-Wait pattern:
 * 1. Fork: Create a clone of the current process.
 * 2. Exec: Replace the clone's memory with the new program.
 * 3. Wait: Pause parent execution until the child finished.
 */
int eigen_launch(char **args, char *line) {
    pid_t pid;
    int status;

    job_delete();

    if (args[0] == NULL) {
        return 1;  // Ignore empty command
    }

    // Block SIGCHLD to prevent race condition
    sigset_t mask_all, mask_one, prev_one;
    if (sigfillset(&mask_all) == -1) _exit(1);
    if (sigemptyset(&mask_one) == -1) _exit(1);
    if (sigaddset(&mask_one, SIGCHLD)) _exit(1);

    // Create a child process.
    // Both two process will execute the following code.
    // Return 0 to the child process and child process ID to the parent process.
    if (sigprocmask(SIG_BLOCK, &mask_one, &prev_one)) _exit(1);

    pid = fork();
    if (pid == 0) {
        // Child process
        restore_signal(SIGINT);
        restore_signal(SIGTSTP);
        restore_signal(SIGQUIT);
        restore_signal(SIGTTIN);
        restore_signal(SIGTTOU);
        restore_signal(SIGCHLD);

        // Set independent process id
        if (setpgid(0, 0) < 0) {
            perror("setpgid");
            _exit(1);
        }

        sigprocmask(SIG_SETMASK, &prev_one, NULL);

        execvp(args[0], args);

        // exec only returns on failure
        perror("Eigen");
        _exit(127);
    } else if (pid < 0) {
        // Error forking
        perror("Eigen");
    } else {
        // Parent process
        // Also calls setpgid to avoid race with child
        if (setpgid(pid, pid) < 0) {
            perror("setpgid");
            _exit(1);
        }

        if (!bg) {
            // Foreground process
            if (shell_interactive) {
                tcsetpgrp(shell_terminal, pid);
            }

            do {
                // Wait for child process
                waitpid(pid, &status, WUNTRACED);
            } while (!WIFEXITED(status) && !WIFSIGNALED(status) && !WIFSTOPPED(status));

            if (shell_interactive) {
                tcsetpgrp(shell_terminal, shell_pgid);
            }

            if (WIFSIGNALED(status)) {
                printf("Child exited with code %d\n", WTERMSIG(status));
            }
            sigprocmask(SIG_SETMASK, &prev_one, NULL);
        } else {
            // Background process
            int jid = job_create(pid, bg, line);
            if (jid == -1) {
                perror("Too many jobs");
            }

            // Don't wait for child process
            printf("[%d] %d %s\n", jid + 1, pid, line);
            sigprocmask(SIG_SETMASK, &prev_one, NULL);
        }
    }

    // Let the main loop continue
    return 1;
}

int eigen_execute(char **args, char *line) {
    if (args == NULL || args[0] == NULL) {
        return 1;
    }

    args = replace_variable(args);

    for (int i = 0; i < eigen_num_builtins(); i++) {
        if (strcmp(args[0], builtin_str[i]) == 0) {
            // Find the correspond function and execute
            return (*builtin_func[i])(args);
        }
    }

    // If it is not a builtin, call launch to execute
    return eigen_launch(args, line);
}

void completion(const char *buf, linenoiseCompletions *lc) {
    if (buf[0] == 'e') {
        linenoiseAddCompletion(lc, "exit");
        linenoiseAddCompletion(lc, "echo");
    }
    if (buf[0] == 'c') {
        linenoiseAddCompletion(lc, "cd");
        linenoiseAddCompletion(lc, "clear");
    }
}

char *hints(const char *buf, int *color, int *bold) {
    if (!strcasecmp(buf, "git remote add")) {
        *color = 90;
        *bold = 0;
        return " <name> <url>";
    }
    return NULL;
}

void eigen_loop(void) {
    // Use the linenoise https://github.com/antirez/linenoise.git
    linenoiseSetCompletionCallback(completion);
    linenoiseSetHintsCallback(hints);
    linenoiseHistoryLoad("history.txt");

    for (;;) {
        errno = 0;
        char *line = linenoise("> ");
        if (line == NULL) {
            if (errno == EAGAIN) {
                continue;
            }
            break;
        }
        if (line[0] == '\0') {
            linenoiseFree(line);
            continue;
        }

        linenoiseHistoryAdd(line);
        linenoiseHistorySave("history.txt");
        char **args = eigen_split_line(line);
        int running_status = eigen_execute(args, line);
        free_tokens(args);
        linenoiseFree(line);

        if (!running_status) {
            break;
        }
    }
}

void sigchld_handler(int sig) {
    int olderrno = errno, status;
    pid_t pid;

    while ((pid = waitpid(-1, &status, WNOHANG | WUNTRACED | WCONTINUED)) > 0) {
        int jid = job_find(pid);

        // Foreground job
        if (jid == -1) {
            continue;
        }

        // Background job
        if (WIFEXITED(status)) {
            jobs[jid]->state = FINISHED;
        } else if (WIFSIGNALED(status)) {
            jobs[jid]->state = FINISHED;
        } else if (WIFSTOPPED(status)) {
            jobs[jid]->state = STOPPED;
        } else if (WIFCONTINUED(status)) {
            jobs[jid]->state = RUNNING;
        }
    }

    errno = olderrno;
}
