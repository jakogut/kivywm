from kivy.graphics.cgl cimport *

cdef extern from "graphics.h":
    # X11
    cdef struct _XDisplay:
        pass

    ctypedef _XDisplay Display

    cdef struct XVisualInfo:
        pass

    ctypedef int XID
    ctypedef XID Bool
    ctypedef XID Window
    ctypedef XID Drawable
    ctypedef XID Pixmap

    # GL
    ctypedef void *GLeglImageOES

    # GLX
    cdef struct __GLXFBConfigRec:
        pass

    ctypedef __GLXFBConfigRec GLXFBConfig

    cdef struct __GLXcontextRec:
        pass

    ctypedef __GLXcontextRec *GLXContext
    ctypedef XID GLXPixmap
    ctypedef XID GLXDrawable

    cdef int XFreePixmap(Display *, Pixmap) nogil
    cdef int XFree(void *) nogil
    cdef int glXDestroyPixmap(Display *, GLXPixmap) nogil

    # EGL
    ctypedef void *EGLClientBuffer
    ctypedef void *EGLConfig
    ctypedef void *EGLContext
    ctypedef void *EGLDisplay
    ctypedef void *EGLNativeDisplayType
    ctypedef void *EGLNativePixmapType
    ctypedef void *EGLSurface
    ctypedef void *EGLImage
    ctypedef void *EGLImageKHR
    ctypedef unsigned int EGLenum
    ctypedef int EGLint
    ctypedef EGLint EGLBoolean

# GLX
ctypedef void (*PFNGLXBINDTEXIMAGEEXTPROC)(Display *, GLXDrawable, const int, int *) nogil
ctypedef void (*PFNGLXRELEASETEXIMAGEEXTPROC)(Display *, GLXDrawable, const int) nogil

ctypedef struct GLX_Context:
    void (*glXBindTexImageEXT)(Display *, GLXDrawable, const int, int *) nogil
    void (*glXReleaseTexImageEXT)(Display *, GLXDrawable, const int) nogil

cdef GLX_Context *glx
cdef GLX_Context *glx_get_context()
cdef void glx_set_context(GLX_Context *ctx)
cpdef void glx_init() except *

# EGL
ctypedef EGLImageKHR (*PFNEGLCREATEIMAGEKHRPROC)(EGLDisplay, EGLContext, EGLenum, EGLClientBuffer, const EGLint *) nogil
ctypedef EGLBoolean (*PFNEGLDESTROYIMAGEKHRPROC)(EGLDisplay, EGLImageKHR) nogil
ctypedef void (*PFNGLEGLIMAGETARGETTEXTURE2DOESPROC)(GLenum, GLeglImageOES) nogil

ctypedef struct EGL_Context:
    EGLImageKHR (*eglCreateImageKHR)(EGLDisplay, EGLContext, EGLenum, EGLClientBuffer, const EGLint *) nogil
    EGLBoolean (*eglDestroyImageKHR)(EGLDisplay, EGLImageKHR) nogil
    void (*glEGLImageTargetTexture2DOES)(GLenum, GLeglImageOES) nogil

cdef EGL_Context *egl
cdef EGL_Context *egl_get_context()
cdef void egl_set_context(EGL_Context *ctx)
cpdef void egl_init() except *
