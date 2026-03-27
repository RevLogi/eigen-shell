#include <signal.h>

#include "include/builtins.h"
#include "include/eigen.h"
#include "include/hashmap.h"
#include "include/job.h"
#include "include/linenoise.h"

MyHashMap *shell_env = NULL;
char *line_bk = NULL;

int main(int argc, char **argv) {
    // Initialize shell env
    shell_env = initial();

    // Enable signal handling
    signal(SIGCHLD, sigchld_handler);

    // Enable batch mode.
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
        perror("Eigen");
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

    sigset_t mask_all, mask_one, prev_one;
    if (sigfillset(&mask_all) == -1) _exit(1);
    if (sigemptyset(&mask_one) == -1) _exit(1);
    if (sigaddset(&mask_one, SIGCHLD)) _exit(1);
    signal(SIGCHLD, sigchld_handler);
    // Block SIGCHLD to prevent race condition
    if (sigprocmask(SIG_BLOCK, &mask_one, &prev_one)) _exit(1);

    // Create a child process.
    // Both two process will execute the following code.
    // Return 0 to the child process and child process ID to the parent process.
    pid = fork();
    if (pid == 0) {
        // Child process
        sigprocmask(SIG_SETMASK, &prev_one, NULL);
        if (execvp(args[0], args) == -1) {
            perror("Eigen");
        }
        exit(EXIT_SUCCESS);
    } else if (pid < 0) {
        // Error forking
        perror("Eigen");
    } else {
        // Parent process
        if (!bg) {
            // Foreground process
            do {
                // Wait for child process
                waitpid(pid, &status, WUNTRACED);
            } while (!WIFEXITED(status) && !WIFSIGNALED(status));
            if (WIFSIGNALED(status)) {
                printf("Child exited with code %d\n", WEXITSTATUS(status));
            }
        } else {
            // Background process
            sigprocmask(SIG_SETMASK, &mask_all, NULL);
            int jid = job_create(pid, bg, line);
            if (jid == -1) {
                perror("Too many jobs");
            }

            // Don't wait for child process
            printf("[%d] %d\n", jid + 1, pid);
        }
        sigprocmask(SIG_SETMASK, &prev_one, NULL);
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
    char *line;
    char **args;
    int status;

    // Use the linenoise https://github.com/antirez/linenoise.git
    linenoiseSetCompletionCallback(completion);
    linenoiseSetHintsCallback(hints);
    linenoiseHistoryLoad("history.txt");

    while ((line = linenoise("λ ")) != NULL) {
        if (line[0] != '\0') {
            linenoiseHistoryAdd(line);
            linenoiseHistorySave("history.txt");
            // eigen_split_line makes in-place mutation to line
            // For jobs command to use, we need to make a backup
            line_bk = strdup(line);
            args = eigen_split_line(line);
            status = eigen_execute(args, line_bk);
            free_tokens(args);
        }
        linenoiseFree(line);

        if (status == 0) break;
    }
}

void sigchld_handler(int sig) {
    sigset_t mask, prev_mask;
    pid_t pid;
    int jid;

    if (sigfillset(&mask) == -1) {
        _exit(1);
    }

    // WNOHANG | WUNTRACED guarantees immediate return
    // Prevents from waiting for every job to be finished
    while ((pid = waitpid(-1, NULL, WNOHANG | WUNTRACED)) > 0) {
        if (sigprocmask(SIG_BLOCK, &mask, &prev_mask) == -1) {
            _exit(1);
        }
        if ((jid = job_find(pid)) != -1) {
            jobs[jid]->state = DONE;
        }
        if (sigprocmask(SIG_SETMASK, &prev_mask, NULL) == -1) {
            _exit(1);
        }
    }
}
