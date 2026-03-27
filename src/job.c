#include "include/job.h"

#include <stdlib.h>
#include <string.h>

#include "include/eigen.h"

job *jobs[MAX_JOBS] = {NULL};
int current_idx = -1;
int previous_idx = -1;

int job_create(pid_t pid, int bg, char *cmd) {
    job *new_job = malloc(sizeof(job));

    new_job->pid = pid;
    new_job->bg = bg;
    new_job->state = RUNNING;
    new_job->cmd = strdup(cmd);

    for (int i = 0; i < MAX_JOBS; i++) {
        if (!jobs[i]) {
            jobs[i] = new_job;
            new_job->jid = i;

            previous_idx = current_idx;
            current_idx = i;

            return new_job->jid;
        }
    }

    // Free the memory if didn't find empty space
    free(new_job);
    return -1;
}

int find_idx(int idx) {
    for (int j = MAX_JOBS - 1; j > -1; j--) {
        if (jobs[j] != NULL && j != idx) {
            return j;
        }
    }
    return -1;
}

int job_delete() {
    for (int i = 0; i < MAX_JOBS; i++) {
        if (jobs[i] && (jobs[i]->state & DONE)) {
            if (current_idx == i) {
                current_idx = previous_idx;
                previous_idx = find_idx(previous_idx);
            }
            if (previous_idx == i) {
                previous_idx = find_idx(current_idx);
            }
            printf("[%d]\tDone\t\t%s\n", jobs[i]->jid + 1, jobs[i]->cmd);
            free(jobs[i]);
            jobs[i] = NULL;
        }
    }
    return 0;
}

int job_free() {
    for (int i = 0; i < MAX_JOBS; i++) {
        if (jobs[i]) {
            free(jobs[i]);
        }
    }
    return 0;
}

int job_find(int pid) {
    for (int i = 0; i < MAX_JOBS; i++) {
        if (jobs[i] != NULL && jobs[i]->pid == pid) {
            return jobs[i]->jid;
        }
    }
    return -1;
}
