#ifndef JOB_H
#define JOB_H

#include <unistd.h>
#define MAX_JOBS 16

#define RUNNING 01
#define STOPPED 02
#define FINISHED 04

// Job control
typedef struct {
    int jid;
    pid_t pid;
    int bg;
    int state;
    char *cmd;
} job;

extern int bg;
extern job *jobs[MAX_JOBS];

#endif
