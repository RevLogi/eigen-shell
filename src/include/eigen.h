#ifndef EIGEN_H
#define EIGEN_H

#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

// Macros
#define EIGEN_RL_BUFSIZE 1024
#define EIGEN_TOK_BUFSIZE 64
#define EIGEN_TOK_DELIM " \t\r\n\a"
#define NORMAL 0
#define IN_QUOTE 1

// utils.c
char **replace_variable(char **tokens);
char **eigen_split_line(char *line);
void free_tokens(char **tokens);

// job.c
int job_create(pid_t pid, int bg, char *cmd);
int job_delete();
int job_free();
int job_find(int pid);

// builtins.c
int eigen_cd(char **args);
int eigen_help(char **args);
int eigen_export(char **args);
int eigen_exit(char **args);
int eigen_clear(char **args);
int eigen_fg(char **args);
int eigen_bg(char **args);
int eigen_jobs();

// main.c
int eigen_launch(char **args, char *line);
int eigen_execute(char **args, char *line);
void eigen_loop(void);
int run_script(char *filename);
void sigchld_handler(int sig);

#endif
