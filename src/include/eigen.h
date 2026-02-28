#ifndef EIGEN_H
#define EIGEN_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
#include <ctype.h>

// Macros
#define EIGEN_RL_BUFSIZE 1024
#define EIGEN_TOK_BUFSIZE 64
#define EIGEN_TOK_DELIM " \t\r\n\a"
#define NORMAL 0
#define IN_QUOTE 1

// utils.c
char** replace_variable(char** tokens);
char** eigen_split_line(char* line);
void free_tokens(char **tokens);

// builtins.c
int eigen_cd(char** args);
int eigen_help(char** args);
int eigen_export(char** args);
int eigen_exit(char** args);
int eigen_clear(char** args);

// main.c
int eigen_launch(char** args);
int eigen_execute(char** args);
void eigen_loop(void);
int run_script(char* filename);

#endif
