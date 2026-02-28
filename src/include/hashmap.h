#ifndef HASHMAP_H
#define HASHMAP_H

typedef struct Node {
    char *val;
    char *key;
    struct Node *next;
} Node;

typedef struct {
    Node **buckets;
    int size;
    int count;
} MyHashMap;
extern MyHashMap *shell_env;

// hashmap.c
MyHashMap *initial();
void install(MyHashMap *obj, char *key, char *value);
char *lookup(MyHashMap *obj, char *key);
void uninstall(MyHashMap *obj, char *key);
void free_exports(MyHashMap *obj);

#endif

