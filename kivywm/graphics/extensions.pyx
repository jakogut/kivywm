cdef extern from "graphics.h":
    void *glXGetProcAddress(GLubyte *)
    void *eglGetProcAddress(const char *)

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

cdef EGL_Context g_egl
cdef EGL_Context *egl = &g_egl

cdef EGL_Context *egl_get_context():
    return egl

cdef void egl_set_context(EGL_Context *ctx):
    global egl
    egl = ctx

cpdef void egl_init() except *:
    egl.eglCreateImageKHR = <PFNEGLCREATEIMAGEKHRPROC>eglGetProcAddress("eglCreateImageKHR")
    egl.eglDestroyImageKHR = <PFNEGLDESTROYIMAGEKHRPROC>eglGetProcAddress("eglDestroyImageKHR")
    egl.glEGLImageTargetTexture2DOES = <PFNGLEGLIMAGETARGETTEXTURE2DOESPROC>eglGetProcAddress("glEGLImageTargetTexture2DOES")
