cdef extern from "graphics.h":
    void *eglGetProcAddress(const char *)

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
