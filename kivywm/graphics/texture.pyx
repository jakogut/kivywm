from kivy.graphics.texture cimport Texture as KivyTexture
from kivywm.graphics.extensions cimport *
from kivywm.graphics.tfp cimport bindTexImage

def texture_create_from_pixmap(pixmap, size):
    colorfmt = 'rgba'
    cdef Texture texture = Texture(size[0], size[1], GL_TEXTURE_2D,
          colorfmt=colorfmt, bufferfmt='ubyte', mipmap=0,
          callback=None, icolorfmt=colorfmt)

    texture.bind_pixmap(pixmap)
    texture.set_min_filter('linear')
    texture.set_mag_filter('linear')
    return texture

cdef class Texture(KivyTexture):
    cdef void *_image

    create_from_pixmap = staticmethod(texture_create_from_pixmap)

    def __init__(self, *args, **kwargs):
        super(Texture, self).__init__(*args, **kwargs)
        self._image = NULL

    def bind_pixmap(self, pixmap):
        self.bind()
        bindTexImage(pixmap)
        self.flip_vertical()
