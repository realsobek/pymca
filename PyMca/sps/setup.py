#!/usr/bin/env python

"""Setup script for the SPS module distribution."""

import os, sys, glob
from distutils.core import setup
from distutils.extension import Extension
ext_modules = [Extension(
                        name = 'spslut',
                        sources=['Src/sps_lut.c',
                                 'Src/spslut_py.c'],
                        include_dirs  = ['Include'],
                   )]
if sys.platform == "win32":
    define_macros = [('WIN32',None)]
else:
    define_macros = []
    ext_modules.append( Extension(
                            name = 'sps',
                            sources=['Src/sps.c',
                                     'Src/sps_py.c'],
                            include_dirs  = ['Include']))
setup (
        name         = "sps",
        version      = "1.0",
        description  = "shared memory and spec",
        author       = "BLISS Group",
        author_email = "rey@esrf.fr",
        url          = "http://www.esrf.fr/computing/bliss/",

        # Description of the modules and packages in the distribution

        extra_path   = 'Pybliss',
        ext_modules  = ext_modules)
