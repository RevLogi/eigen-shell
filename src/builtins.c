#include "include/builtins.h"

#include <limits.h>
#include <stdio.h>

#include "include/eigen.h"
#include "include/hashmap.h"
#include "include/job.h"
#include "include/linenoise.h"

static char *oldpwd = NULL;
char *builtin_str[] = {"cd", "clear", "export", "jobs", "help", "exit"};

int (*builtin_func[])(char **) = {&eigen_cd,   &eigen_clear, &eigen_export,
                                  &eigen_jobs, &eigen_help,  &eigen_exit};

int eigen_num_builtins() { return sizeof(builtin_func) / sizeof(char *); }

int eigen_cd(char **args) {
    char cwd[PATH_MAX];
    char *target_path;

    // We must capture the cwd before calling chdir().
    // Once chdir() succeeds, the kernel updates the process state,
    // and the "previous" directory path is lost forever.
    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        perror("Eigen: getcwd");
        return 1;
    }

    if (args[1] == NULL || strcmp(args[1], "~") == 0) {
        target_path = getenv("HOME");
    } else if (strcmp(args[1], "-") == 0) {
        if (oldpwd == NULL) {
            fprintf(stderr, "Eigen: OLDPWD not set\n");
            return 1;
        }
        target_path = oldpwd;
        printf("%s\n", target_path);
    } else {
        // Extend ~ expansion globally
        if (args[1][1] == '~') {
            char *home_path = getenv("HOME");
            int home_len = strlen(home_path);
            int orig_len = strlen(args[1]);

            char *target_path = (char *)malloc(home_len + orig_len - 1);
            if (!target_path) perror("Malloc failed");

            for (int i = 0; i < home_len; i++) {
                target_path[i] = home_path[i];
            }

            for (int j = 1; j < orig_len; j++) {
                target_path[home_len + j - 1] = args[1][j];
            }
        } else {
            target_path = args[1];
        }
    }

    if (chdir(target_path) != 0) {
        perror("Eigen");
    } else {
        // oldpwd is a static variable, it persists across function calls.
        // We should follow the "free-before-alloc" pattern to prevent memory leak.
        if (oldpwd != NULL) {
            free(oldpwd);
        }
        oldpwd = strdup(cwd);
    }
    return 1;
}

int eigen_clear(char **args) {
    linenoiseClearScreen();
    return 1;
}

int eigen_export(char **args) {
    if (args[1] == NULL) {
        for (int i = 0; i < shell_env->size; i++) {
            Node *curr = shell_env->buckets[i];
            while (curr != NULL) {
                printf("declare -x %s=\"%s\"\n", curr->key, curr->val);
                curr = curr->next;
            }
        }
        return 1;
    }

    char *key = args[1];
    char *cursor = args[1];
    char *val = NULL;
    while (*cursor != '\0') {
        if (*cursor == '=') {
            *cursor = '\0';
            val = cursor + 1;
            break;
        }
        cursor++;
    }

    if (val != NULL) {
        install(shell_env, key, val);
        setenv(key, val, 1);
    }

    return 1;
}

int eigen_jobs() {
    job_delete();
    for (int i = 0; i < MAX_JOBS; i++) {
        if (jobs[i] == NULL) continue;

        char mark = ' ';
        if (current_idx == i) mark = '+';
        if (previous_idx == i) mark = '-';
        char *state;
        if (jobs[i]->state == RUNNING) {
            state = strdup("RUNNING");
        } else if (jobs[i]->state == STOPPED) {
            state = strdup("STOPPED");
        } else {
            state = strdup("DONE");
        }
        printf("[%d]%c\t%s\t\t%s\n", jobs[i]->jid + 1, mark, state, jobs[i]->cmd);
    }
    return 1;
}

int eigen_help(char **args) {
    printf("The following are built-in:\n");

    for (int i = 0; i < eigen_num_builtins(); i++) {
        printf("  %s", builtin_str[i]);
    }
    printf("\n");
    return 1;
}

int eigen_exit(char **args) {
    job_free();
    printf("exit\n");
    return 0;
}
