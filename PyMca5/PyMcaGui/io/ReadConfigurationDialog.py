#/*##########################################################################
# Copyright (C) 2019 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#############################################################################*/
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """This module provides tools to read configurations from ini files
and from their representation in an HDF5 file"""

import sys
if sys.version_info < (3,):
    from StringIO import StringIO
else:
    from io import StringIO
from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
try:
    from h5py import is_hdf5
    from PyMca5.PyMcaGui.io.hdf5.HDF5Widget import getDatasetValueDialog
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False

_HDF5_EXTENSIONS = [".h5", ".hdf5", ".hdf", ".nxs", ".nx"]

def getFitConfiguration(parent=None, filetypelist=None, message=None,
                        currentdir=None, mode="OPEN", getfilter=None,
                        single=True, currentfilter=None, native=None):
    if filetypelist is None:
        filetypelist = ["Fit configuration files (*.cfg)"]
        if HAS_H5PY:
            filetypelist.append(
                    "Fit results file (*%s)" % " *".join(_HDF5_EXTENSIONS))
        filetypelist.append("All files (*)")
    if message is None:
        message = "Choose fit configuration file"
    return getConfigurationFileContents(parent=parent,
                                        filetypelist=filetypelist,
                                        message=message,
                                        currentdir=currentdir,
                                        mode=mode,
                                        getfilter=getfilter,
                                        single=single,
                                        currentfilter=currentdir,
                                        native=native)

def getConfigurationFileContents(parent=None, filetypelist=None, message=None,
                                 currentdir=None, mode="OPEN", getfilter=None,
                                 single=True, currentfilter=None, native=None):
    if filetypelist is None:
        filetypelist = ["Configuration from .ini files (*.ini)"]
        if HAS_H5PY:
            filetypelist.append(
                    "Configuration from HDF5 file (*%s)" % " *".join(_HDF5_EXTENSIONS))
        filetypelist.append("All files (*)")
    if message is None:
        message = "Choose configuration file"
    fileList = PyMcaFileDialogs.getFileList(parent=parent,
                    filetypelist=filetypelist, message=message,
                    currentdir=currentdir,
                    mode="OPEN",            # input ignored
                    getfilter=getfilter,
                    single=True,            # input ignored
                    currentfilter=currentfilter,
                    native=native)
    if not len(fileList):
        return None
    if getfilter:
        filename, usedfilter = fileList[:2]
    else:
        filename = fileList[0]

    cfg = ConfigDict.ConfigDict()
    if HAS_H5PY and is_hdf5(filename):
        # we have to select a dataset
        msg = 'Select the configuration dataset by a double click'
        initxt = getDatasetValueDialog(filename,
                                  value=True,
                                  message=msg,
                                  parent=parent)
        if not initxt:
            return None
        cfg.readfp(StringIO(initxt))
    else:
        cfg.read(filename)

    if getfilter:
        return cfg, filterused
    else:
        return cfg

if __name__ == "__main__":
    app = qt.QApplication([])
    print(getFitConfiguration())
    app = None
