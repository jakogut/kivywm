cdef extern from "graphics.h":
    void *glXGetProcAddress(GLubyte *)

cdef GLX_Context g_glx
cdef GLX_Context *glx = &g_glx

cdef GLX_Context *glx_get_context():
    return glx

cdef void glx_set_context(GLX_Context *ctx):
    global glx
    glx = ctx

cpdef void glx_init() except *:
    glx.glXBindTexImageEXT = <PFNGLXBINDTEXIMAGEEXTPROC>glXGetProcAddress("glXBindTexImageEXT")
    glx.glXReleaseTexImageEXT = <PFNGLXRELEASETEXIMAGEEXTPROC>glXGetProcAddress("glXReleaseTexImageEXT")


