#include "include/eigen.h"
#include "include/hashmap.h"
#include <ctype.h>

#define EIGEN_CHECK_CAPACITY(ptr, pos, cap, inc, type)           \
    do {                                                         \
        if ((pos) >= (cap)) {                                    \
            size_t new_cap = (cap) + (inc);                      \
            void *temp = realloc((ptr), new_cap * sizeof(type)); \
            if (!temp) {                                         \
                free(ptr);                                       \
                return NULL;                                     \
            }                                                    \
            (ptr) = temp;                                        \
            (cap) = new_cap;                                     \
        }                                                        \
    } while (0)

char **eigen_split_line(char *line) {
    int bufsize = EIGEN_TOK_BUFSIZE;
    int state = NORMAL;
    int position = 0;

    char **tokens = malloc(bufsize * sizeof(char *));

    char *read = line;
    char *write = line;
    char *word = line;

    if (!tokens) {
        return NULL;
    }

    while (*read != '\0') {
        EIGEN_CHECK_CAPACITY(tokens, position, bufsize, EIGEN_TOK_BUFSIZE, char *);

        if (state == IN_QUOTE) {
            if (*read == '"') {
                state = NORMAL;
            } else {
                *write = *read;
                write++;
            }
        } else if (state == NORMAL) {
            if (*read == '"') {
                state = IN_QUOTE;
            } else if (isspace(*read)) {
                // Handle successive space
                if (write > word) {
                    *write = '\0';
                    tokens[position++] = strdup(word);
                    write++;
                    word = write;
                } else {
                    word = write;
                }
            } else {
                *write = *read;
                write++;
            }
        }
        read++;
    }

    // Handle the last word
    if (write > word) {
        *write = '\0';
        tokens[position++] = strdup(word);
    }
    tokens[position] = NULL;

    return tokens;
}

char **replace_variable(char **tokens) {
    for (int i = 0; tokens[i] != NULL; i++) {
        if (tokens[i][0] == '$') {
            // Keep single $
            if (tokens[i][1] == '\0') continue;

            // Truncate
            char h;
            int j;
            for (j = 1; (h = tokens[i][j]) != '\0'; j++) {
                if (!isalpha(h) && !isdigit(h) && h != '_') {
                    tokens[i][j] = '\0';
                    break;
                }
            }

            // Lookup
            char *val_name = tokens[i] + 1;
            char *val = lookup(shell_env, val_name);
            if (val == NULL) {
                val = "";
            }

            // Restore
            tokens[i][j] = h;
            char *sp = tokens[i] + j;

            size_t new_len = strlen(val) + strlen(sp) + 1;
            char *new_token = malloc(new_len);

            if (new_token != NULL) {
                strcpy(new_token, val);
                strcat(new_token, sp);
                free(tokens[i]);
                tokens[i] = new_token;
            }
        }
    }
    return tokens;
}

void free_tokens(char **tokens) {
    if (!tokens) return;

    for (int i = 0; tokens[i] != NULL; i++) {
        free(tokens[i]);
    }

    free(tokens);
}

