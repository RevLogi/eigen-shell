#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "include/hashmap.h"

#define INITIAL 6
#define LOAD_FACTOR 0.75

unsigned long hash_string(char *str) {
    unsigned long hash = 5381;
    int c;
    while ((c = *str++))
        hash = ((hash << 5) + hash) + c;
    return hash;
}

MyHashMap *initial() {
    MyHashMap *obj = malloc(sizeof(MyHashMap));

    obj->size = INITIAL;
    obj->buckets = calloc(INITIAL, sizeof(Node *));
    obj->count = 0;

    return obj;
}

void migrateList(Node *curr, Node **newBuckets, int newSize) {
    if (curr == NULL) return;

    Node *nextNode = curr->next;

    unsigned long rawHash = hash_string(curr->key);
    int newIndex = rawHash % newSize;

    curr->next = newBuckets[newIndex];
    newBuckets[newIndex] = curr;

    migrateList(nextNode, newBuckets, newSize);
}

void resize(MyHashMap *obj) {
    int oldSize = obj->size;
    int newSize = obj->size * 2;

    Node **newBuckets = calloc(newSize, sizeof(Node *));
    if (!newBuckets) return;

    for (int i = 0; i < obj->size; i++) {
        if (obj->buckets[i] != NULL) {
            migrateList(obj ->buckets[i], newBuckets, newSize);
        }
    }

    free(obj->buckets);

    obj->buckets = newBuckets;
    obj->size = newSize;
}

void install(MyHashMap *obj, char *key, char *value) {
    if ((double)obj->count / obj->size >= LOAD_FACTOR) {
        resize(obj);
    }

    unsigned long rawHash = hash_string(key);
    int hash = rawHash % obj->size;
    Node *curr = obj->buckets[hash];

    while (curr != NULL) {
        if (strcmp(curr->key, key) == 0) {
            free(curr->val);
            curr->val = strdup(value);
            return;
        }
        curr = curr->next;
    }

    Node *newNode = malloc(sizeof(Node));
    newNode->key = strdup(key);
    newNode->val = strdup(value);

    newNode->next = obj->buckets[hash];
    obj->buckets[hash] = newNode;

    obj->count++;
}

char *lookup(MyHashMap *obj, char *key) {
    unsigned long rawHash = hash_string(key);
    int hash = rawHash % obj->size;

    Node *curr = obj->buckets[hash];

    while (curr != NULL) {
        if (strcmp(curr->key, key) == 0) {
            return curr->val;
        }
        curr = curr->next;
    }

    return NULL;
}

void uninstall(MyHashMap *obj, char *key) {
    unsigned long rawHash = hash_string(key);
    int hash = rawHash % obj->size;

    Node *curr = obj->buckets[hash];
    Node *prev = NULL;

    while (curr != NULL) {
        if (strcmp(curr->key, key) == 0) {
            if (prev == NULL) {
                obj->buckets[hash] = curr->next;
            } else {
                prev->next = curr->next;
            }
            free(curr);
            obj->count--;
            return;
        }
        prev = curr;
        curr = curr->next;
    }
}

void free_exports(MyHashMap *obj) {
    for (int i = 0; i < obj->size;i++) {
        Node *curr = obj->buckets[i];
        while (curr != NULL) {
            Node *temp = curr;
            curr = curr->next;
            free(temp->key);
            free(temp->val);
            free(temp);
        }
    }

    free(obj->buckets);
    free(obj);
}

