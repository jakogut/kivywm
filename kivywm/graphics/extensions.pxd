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

    # GLX
    cdef struct __GLXFBConfigRec:
        pass

    ctypedef __GLXFBConfigRec GLXFBConfig

    cdef struct __GLXcontextRec:
        pass

    ctypedef __GLXcontextRec *GLXContext
    ctypedef XID GLXPixmap
    ctypedef XID GLXDrawable

    cdef int XFreePixmap(Display *, Pixmap)
    cdef int XFree(void *)
    cdef int glXDestroyPixmap(Display *, GLXPixmap)

# GLX
ctypedef void (*PFNGLXBINDTEXIMAGEEXTPROC)(Display *, GLXDrawable, const int, int *) nogil
ctypedef void (*PFNGLXRELEASETEXIMAGEEXTPROC)(Display *, GLXDrawable, const int) nogil

ctypedef struct GLX_Context:
    void (*glXBindTexImageEXT)(Display *, GLXDrawable, const int, int *)
    void (*glXReleaseTexImageEXT)(Display *, GLXDrawable, const int)

cdef GLX_Context *glx
cdef GLX_Context *glx_get_context()
cdef void glx_set_context(GLX_Context *ctx)
cpdef void glx_init() except *
