#pragma once

typedef struct {
    void* (*initialize_runtime)(void);
    void (*delete_runtime)(void*);
} FfiRuntime;

void* initialize_runtime_Python(void);
void delete_runtime_Python(void* runtime);
