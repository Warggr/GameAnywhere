#include "core.h"
#include <Python.h>
#include <assert.h>

void* initialize_runtime_Python(void) {
    Py_Initialize();
    return NULL;
}

void delete_runtime_Python(void* _runtime){
    (void) _runtime;
    assert(Py_FinalizeEx() == 0);
}
