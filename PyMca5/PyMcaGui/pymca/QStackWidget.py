#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2022 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF.
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import traceback
import numpy
import weakref
import logging
_logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # We are going to read. Disable file locking.
    os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
    _logger.info("%s set to %s" % ("HDF5_USE_FILE_LOCKING",
                                    os.environ["HDF5_USE_FILE_LOCKING"]))
    try:
        # make sure hdf5plugins are imported
        import hdf5plugin
    except:
        _logger.info("Failed to import hdf5plugin")
    # we have to get the Qt binding prior to import PyMcaQt
    import getopt
    options = ''
    longoptions = ["fileindex=","old",
                   "filepattern=", "begin=", "end=", "increment=",
                   "nativefiledialogs=", "imagestack=", "image=",
                   "backend=", "binding=", "logging=", "debug="]
    opts, args = getopt.getopt(
                 sys.argv[1:],
                 options,
                 longoptions)
    binding = None
    for opt, arg in opts:
        if opt in ('--debug'):
            if arg.lower() not in ['0', 'false']:
                debugreport = 1
                _logger.setLevel(logging.DEBUG)
            # --debug is also parsed later for the global logging level
        elif opt in ('--binding'):
            binding = arg.lower()
            if binding == "pyqt5":
                import PyQt5.QtCore
            elif binding == "pyside2":
                import PySide2.QtCore
            elif binding == "pyside6":
                import PySide6.QtCore
            else:
                raise ValueError("Unsupported Qt binding <%s>" % binding)
    from PyMca5.PyMcaCore.LoggingLevel import getLoggingLevel
    logging.basicConfig(level=getLoggingLevel(opts))

from PyMca5.PyMcaGui import PyMcaQt as qt
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = qt.safe_str
try:
    # try to import silx prior to importing matplotlib to prevent
    # unnecessary warning
    import silx.gui.plot
except:
    pass

from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaCore import DataObject
from PyMca5.PyMcaGui.pymca import McaWindow
from PyMca5.PyMcaCore import StackBase
from PyMca5.PyMcaCore import McaStackExport
from PyMca5.PyMcaGui.misc import CloseEventNotifyingWidget
from PyMca5.PyMcaGui.plotting import MaskImageWidget
convertToRowAndColumn = MaskImageWidget.convertToRowAndColumn

from PyMca5.PyMcaGui.pymca import RGBCorrelator
from PyMca5.PyMcaGui.pymca.RGBCorrelatorWidget import ImageShapeDialog
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict
from PyMca5.PyMcaGui.pymca import StackSelector
from PyMca5 import PyMcaDirs
from PyMca5.PyMcaIO import ArraySave
HDF5 = ArraySave.HDF5

# _logger.setLevel(logging.DEBUG)
QTVERSION = qt.qVersion()
if _logger.getEffectiveLevel() == logging.DEBUG:
    StackBase.logger.setLevel(logging.DEBUG)


class QStackWidget(StackBase.StackBase,
                   CloseEventNotifyingWidget.CloseEventNotifyingWidget):
    def __init__(self, parent=None,
                 mcawidget=None,
                 rgbwidget=None,
                 vertical=False,
                 master=True):
        StackBase.StackBase.__init__(self)
        CloseEventNotifyingWidget.CloseEventNotifyingWidget.__init__(self,
                                                                     parent)

        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))
        self.setWindowTitle("PyMCA - ROI Imaging Tool")
        screenHeight = qt.QDesktopWidget().height()
        if screenHeight > 0:
            if QTVERSION < '4.5.0':
                self.setMaximumHeight(int(0.99*screenHeight))
            self.setMinimumHeight(int(0.5*screenHeight))
        screenWidth = qt.QDesktopWidget().width()
        if screenWidth > 0:
            if QTVERSION < '4.5.0':
                self.setMaximumWidth(int(screenWidth)-5)
            self.setMinimumWidth(min(int(0.5*screenWidth),800))
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(2)
        self.mcaWidget = mcawidget
        self.rgbWidget = rgbwidget
        self.master = master
        self._slaveList = None
        self._masterStack = None
        self.stackSelector = None
        self._build(vertical=vertical)
        self._buildBottom()
        self._buildConnections()
        self.__ROIConnected = True

    def _build(self, vertical=False):
        box = qt.QSplitter(self)
        if vertical:
            box.setOrientation(qt.Qt.Vertical)
            boxmainlayout = qt.QVBoxLayout(box)
        else:
            box.setOrientation(qt.Qt.Horizontal)
            boxmainlayout = qt.QHBoxLayout(box)

        self.stackWindow = qt.QWidget(box)
        self.stackWindow.mainLayout = qt.QVBoxLayout(self.stackWindow)
        self.stackWindow.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.stackWindow.mainLayout.setSpacing(0)

        self.stackWidget = MaskImageWidget.MaskImageWidget(self.stackWindow,
                                                    selection=False,
                                                    standalonesave=False,
                                                    imageicons=False,
                                                    aspect=True)
        self._stackSaveMenu = qt.QMenu()
        if HDF5:
            if self.master:
                self._stackSaveMenu.addAction(QString("Export All Stacks Workspace"),
                                                         self.exportStackList)
            self._stackSaveMenu.addAction(QString("Export Stack Workspace"),
                                                         self.exportStack)
            self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as Spectra"),
                                             self.saveStackAsNeXusSpectra)
            self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as Images"),
                                             self.saveStackAsNeXusImages)
            self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as Compressed Spectra"),
                                             self.saveStackAsNeXusCompressedSpectra)
            self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as Compressed Images"),
                                             self.saveStackAsNeXusCompressedImages)
            self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as Float32 Spectra"),
                                             self.saveStackAsFloat32NeXusSpectra)
            self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as Float64 Spectra"),
                                             self.saveStackAsFloat64NeXusSpectra)
            self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as Float32 Images"),
                                             self.saveStackAsFloat32NeXusImages)
            self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as Float64 Images"),
                                             self.saveStackAsFloat64NeXusImages)
            self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as HDF5 /data"),
                                             self.saveStackAsSimplestHDF5)
        self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as Monochromatic TIFF Images"),
                                             self.saveStackAsMonochromaticTiffImages)
        self._stackSaveMenu.addAction(QString("Save Zoomed Stack Region as Float32 TIFF Images"),
                                             self.saveStackAsFloat32TiffImages)
        self._stackSaveMenu.addAction(QString("Standard Graphics"),
                            self.stackWidget.graphWidget._saveIconSignal)
        self.stackWidget.graphWidget.saveToolButton.clicked.connect( \
                     self._stackSaveToolButtonSignal)

        self.stackGraphWidget = self.stackWidget.graphWidget

        self.roiWindow = qt.QWidget(box)
        self.roiWindow.mainLayout = qt.QVBoxLayout(self.roiWindow)
        self.roiWindow.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.roiWindow.mainLayout.setSpacing(0)
        standaloneSaving = True
        self.roiWidget = MaskImageWidget.MaskImageWidget(parent=self.roiWindow,
                                                         rgbwidget=self.rgbWidget,
                                                         selection=True,
                                                         colormap=True,
                                                         imageicons=True,
                                                         standalonesave=standaloneSaving,
                                                         profileselection=True,
                                                         aspect=True)
        infotext = 'Toggle background subtraction from current image\n'
        infotext += 'subtracting a straight line between the ROI limits.'
        self.roiBackgroundIcon = qt.QIcon(qt.QPixmap(IconDict["subtract"]))
        self.roiBackgroundButton = self.roiWidget.graphWidget._addToolButton(\
                                    self.roiBackgroundIcon,
                                    self._roiSubtractBackgroundClicked,
                                    infotext,
                                    toggle=True,
                                    state=False,
                                    position=6)
        self.roiGraphWidget = self.roiWidget.graphWidget
        self.stackWindow.mainLayout.addWidget(self.stackWidget)
        self.roiWindow.mainLayout.addWidget(self.roiWidget)
        box.addWidget(self.stackWindow)
        box.addWidget(self.roiWindow)
        boxmainlayout.addWidget(self.stackWindow)
        boxmainlayout.addWidget(self.roiWindow)
        self.mainLayout.addWidget(box)


        #add some missing icons
        offset = 8
        infotext = 'If checked, spectra will be added normalized to the number\n'
        infotext += 'of pixels. Be carefull if you are preparing a batch and you\n'
        infotext += 'fit the normalized spectra because the data in the batch will\n'
        infotext += 'have a different weight because they are not normalized.'
        self.normalizeIcon = qt.QIcon(qt.QPixmap(IconDict["normalize16"]))
        self.normalizeButton = self.stackGraphWidget._addToolButton( \
                                        self.normalizeIcon,
                                        self.normalizeIconChecked,
                                        infotext,
                                        toggle=True,
                                        state=False,
                                        position=6)
        offset += 1

        if self.master:
            self.loadIcon = qt.QIcon(qt.QPixmap(IconDict["fileopen"]))
            self.loadStackButton = self.stackGraphWidget._addToolButton( \
                                        self.loadIcon,
                                        self.loadSlaveStack,
                                        'Load another stack of same shape',
                                        position=offset)
            offset += 1

        self.pluginIcon = qt.QIcon(qt.QPixmap(IconDict["plugin"]))
        infotext = "Call/Load Stack Plugins"
        self.stackGraphWidget._addToolButton(self.pluginIcon,
                                             self._pluginClicked,
                                             infotext,
                                             toggle=False,
                                             state=False,
                                             position=offset)

    def setStack(self, *var, **kw):
        self.stackWidget.setImageData(None)
        self.roiWidget.setImageData(None)
        StackBase.StackBase.setStack(self, *var, **kw)
        if (1 in self._stack.data.shape) and\
           isinstance(self._stack.data, numpy.ndarray):
            oldshape = self._stack.data.shape
            dialog = ImageShapeDialog(self, shape=oldshape[0:2])
            dialog.setModal(True)
            ret = dialog.exec()
            if ret:
                shape = dialog.getImageShape()
                dialog.close()
                del dialog
                self._stack.data.shape = [shape[0], shape[1], oldshape[2]]
                self.stackWidget.setImageData(None)
                self.roiWidget.setImageData(None)
                StackBase.StackBase.setStack(self, self._stack, **kw)
        try:
            if 'SourceName' in self._stack.info:
                if type(self._stack.info['SourceName']) == type([]):
                    if len(self._stack.info['SourceName']) == 1:
                        title = qt.safe_str(self._stack.info['SourceName'][0])
                    else:
                        f0 = qt.safe_str(self._stack.info['SourceName'][0])
                        f1 = qt.safe_str(self._stack.info['SourceName'][-1])
                        try:
                            f0 = os.path.basename(f0)
                            f1 = os.path.basename(f1)
                        except:
                            pass
                        title = "Stack from %s to %s"  % (f0, f1)
                else:
                    title = qt.safe_str(self._stack.info['SourceName'])
                self.setWindowTitle(title)
        except:
            # TODO: give a reasonable title
            pass

    def normalizeIconChecked(self):
        pass

    def _roiSubtractBackgroundClicked(self):
        if not len(self._ROIImageList):
            return
        xScale = self._stack.info.get("xScale", None)
        yScale = self._stack.info.get("yScale", None)
        if self.roiBackgroundButton.isChecked():
            self.roiWidget.graphWidget.graph.setGraphTitle( \
                                self._ROIImageNames[0] + " Net")
            self.roiWidget.setImageData(self._ROIImageList[0] - \
                                        self._ROIImageList[-1],
                                        xScale=xScale,
                                        yScale=yScale)
        else:
            self.roiWidget.graphWidget.graph.setGraphTitle( \
                                self._ROIImageNames[0])
            self.roiWidget.setImageData(self._ROIImageList[0],
                                        xScale=xScale,
                                        yScale=yScale)

    def _stackSaveToolButtonSignal(self):
        self._stackSaveMenu.exec(self.cursor().pos())

    def _getOutputHDF5Filename(self, nexus=False):
        fileTypes = "HDF5 Files (*.h5)\nHDF5 Files (*.hdf)"
        message = "Enter output filename"
        wdir = PyMcaDirs.outputDir
        filename = PyMcaFileDialogs.getFileList(self,
                                        message=message,
                                        mode="SAVE",
                                        currentdir=wdir,
                                        filetypelist=[fileTypes],
                                        getfilter=False,
                                        single=True)

        if len(filename):
            filename = filename[0]
        if len(filename):
            try:
                fname = qt.safe_str(filename)
                if fname.endswith('.h5') or\
                   fname.endswith('.hdf'):
                    return fname
                else:
                    return fname + ".h5"
            except UnicodeEncodeError:
                msg = qt.QMessageBox(self)
                msg.setWindowTitle("Encoding error")
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Please use ASCII characters in file name and path")
                msg.exec()
        return ""

    def _getOutputTiffFilename(self):
        fileTypes = "TIFF Files (*.tif *.tiff *.TIF *.TIFF)"
        message = "Enter output filename"
        wdir = PyMcaDirs.outputDir
        filename = PyMcaFileDialogs.getFileList(self,
                                        message=message,
                                        mode="SAVE",
                                        currentdir=wdir,
                                        filetypelist=[fileTypes],
                                        getfilter=False,
                                        single=True)
        if len(filename):
            filename = filename[0]
        if len(filename):
            try:
                fname = qt.safe_str(filename)
                if fname.endswith('.tif') or\
                   fname.endswith('.tiff') or\
                   fname.endswith('.TIF') or\
                   fname.endswith('.TIFF'):
                    return fname
                else:
                    return fname + ".tif"
            except UnicodeEncodeError:
                msg = qt.QMessageBox(self)
                msg.setWindowTitle("Encoding error")
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Please use ASCII characters in file name and path")
                msg.exec()
        return ""

    def saveStackAsMonochromaticTiffImages(self, dtype=None):
        if dtype is None:
            dtype = self._stack.data.dtype
        if dtype in [numpy.uint32, numpy.uint64]:
            dtype = numpy.float32
        elif dtype in [numpy.int32, numpy.int64]:
            dtype = numpy.float32

        filename = self._getOutputTiffFilename()
        if not len(filename):
            return

        mcaIndex = self._stack.info.get('McaIndex', -1)
        dataView = self._getCroppedView()

        ArraySave.save3DArrayAsMonochromaticTiff(dataView,
                                    filename,
                                    labels=None,
                                    dtype=dtype,
                                    mcaindex=mcaIndex)

    def saveStackAsFloat32TiffImages(self):
        return self.saveStackAsMonochromaticTiffImages(dtype=numpy.float32)

    def _getCroppedView(self):
        mcaIndex = self._stack.info.get('McaIndex', -1)
        #get limits
        y0, y1 = self.stackWidget.graph.getGraphYLimits()
        x0, x1 = self.stackWidget.graph.getGraphXLimits()
        xScale = self._stack.info.get("xScale", None)
        yScale = self._stack.info.get("yScale", None)
        if mcaIndex in [0]:
            shape = [self._stack.data.shape[1], self._stack.data.shape[2]]
        elif mcaIndex in [1]:
            shape = [self._stack.data.shape[0], self._stack.data.shape[2]]
        else:
            shape = [self._stack.data.shape[0], self._stack.data.shape[1]]
        row0, col0 = convertToRowAndColumn( \
                     x0, y0, shape, xScale=xScale, yScale=yScale, safe=True)
        row1, col1 = convertToRowAndColumn( \
                     x1, y1, shape, xScale=xScale, yScale=yScale, safe=True)

        #this should go to array save ...
        shape = self._stack.data.shape
        if mcaIndex in [0]:
            row0 = int(max([row0+0.5, 0]))
            row1 = int(min([row1+0.5, self._stack.data.shape[1]]))
            col0 = int(max([col0+0.5, 0]))
            col1 = int(min([col1+0.5, self._stack.data.shape[2]]))
            view = self._stack.data[:, row0:row1+1, col0:col1+1]
        elif mcaIndex in [1]:
            row0 = int(max([row0+0.5, 0]))
            row1 = int(min([row1+0.5, self._stack.data.shape[0]]))
            col0 = int(max([col0+0.5, 0]))
            col1 = int(min([col1+0.5, self._stack.data.shape[2]]))
            view = self._stack.data[row0:row1+1, : , col0:col1+1]
        else:
            row0 = int(max([row0+0.5, 0]))
            row1 = int(min([row1+0.5, self._stack.data.shape[0]]))
            col0 = int(max([col0+0.5, 0]))
            col1 = int(min([col1+0.5, self._stack.data.shape[1]]))
            view = self._stack.data[row0:row1+1, col0:col1+1, :]
        return view

    def exportStackList(self, filename=None):
        if filename is None:
            filename = self._getOutputHDF5Filename()
            if not len(filename):
                return
            # the user already confirmed overwriting and McaStackExport does not
            # delete an existing file
            if os.path.exists(filename):
                os.remove(filename)
        McaStackExport.exportStackList(self.getStackDataObjectList(), filename)

    def exportStack(self, filename=None):
        if filename is None:
            filename = self._getOutputHDF5Filename()
            if not len(filename):
                return
            # the user already confirmed overwriting and McaStackExport does not
            # delete an existing file
            if os.path.exists(filename):
                os.remove(filename)
        McaStackExport.exportStackList([self.getStackDataObject()], filename)

    def saveStackAsNeXus(self, dtype=None, interpretation=None, compression=False):
        mcaIndex = self._stack.info.get('McaIndex', -1)
        if interpretation is None:
            if mcaIndex in [0]:
                interpretation = "image"
            else:
                interpretation = "spectrum"
        if interpretation not in ["spectrum", "image"]:
            raise ValueError("Unknown data interpretation %s" % interpretation)
        filename = self._getOutputHDF5Filename()
        if not len(filename):
            return

        # get only the seen stack portion
        view = self._getCroppedView()

        # the current graph axis is saved
        axes = [None] * len(self._stack.data.shape)
        labels = [None] * len(self._stack.data.shape)
        try:
            xLabel = qt.safe_str(self.mcaWidget.graph.getGraphXLabel())
        except:
            xLabel = None
        try:
            xData, y, legend, info = self.mcaWidget.getActiveCurve()[:4]
        except:
            xData = self._mcaData0.x[0]
            xLabel = 'Channels'
        if interpretation == 'image':
            labels[0] = xLabel
            axes[0] = xData
        else:
            labels[-1] = xLabel
            axes[-1] = xData
        try:
            ArraySave.save3DArrayAsHDF5(view,
                                    filename,
                                    axes=axes,
                                    labels=labels,
                                    dtype=dtype,
                                    mode='nexus',
                                    mcaindex=mcaIndex,
                                    interpretation=interpretation,
                                    compression=compression)
        except:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setWindowTitle("Save error")
            msg.setText("An error has occured while saving the data:")
            msg.setInformativeText(qt.safe_str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def saveStackAsNeXusSpectra(self, compression=False):
        self.saveStackAsNeXus(interpretation="spectrum",
                              compression=compression)

    def saveStackAsNeXusImages(self):
        self.saveStackAsNeXus(interpretation="image", compression=False)

    def saveStackAsNeXusCompressedSpectra(self):
        self.saveStackAsNeXusSpectra(compression=True)

    def saveStackAsNeXusCompressedImages(self):
        self.saveStackAsNeXus(interpretation="image", compression=True)

    def saveStackAsFloat32NeXusSpectra(self):
        self.saveStackAsNeXus(dtype=numpy.float32, interpretation="spectrum")

    def saveStackAsFloat64NeXusSpectra(self):
        self.saveStackAsNeXus(dtype=numpy.float64, interpretation="spectrum")

    def saveStackAsFloat32NeXusImages(self):
        self.saveStackAsNeXus(dtype=numpy.float32, interpretation="image")

    def saveStackAsFloat64NeXusImages(self):
        self.saveStackAsNeXus(dtype=numpy.float64, interpretation="image")

    def saveStackAsNeXusPlus(self):
        filename = self._getOutputHDF5Filename()
        if not len(filename):
            return
        ArraySave.save3DArrayAsHDF5(self._stack.data, filename,
                                    labels=None, dtype=None, mode='nexus+')

    def saveStackAsSimpleHDF5(self):
        filename = self._getOutputHDF5Filename()
        if not len(filename):
            return
        ArraySave.save3DArrayAsHDF5(self._stack.data, filename,
                                    labels=None, dtype=None, mode='simple')

    def saveStackAsSimplestHDF5(self):
        filename = self._getOutputHDF5Filename()
        if not len(filename):
            return
        view = self._getCroppedView()
        ArraySave.save3DArrayAsHDF5(view, filename,
                                    labels=None, dtype=None, mode='simplest')

    def loadStack(self):
        if self._stackImageData is not None:
            #clear with a small stack
            stack = DataObject.DataObject()
            stack.data = numpy.zeros((100, 100, 100), numpy.float32)
            self.setStack(stack)
        if self.stackSelector is None:
            self.stackSelector = StackSelector.StackSelector(self)
        stack = self.stackSelector.getStack()
        if (type(stack) == type([])) or isinstance(stack, list):
            #aifira like, two stacks
            self.setStack(stack[0])
            self._slaveList = None
            if len(stack) > 1:
                for i in range(1, len(stack)):
                    if stack[i] is not None:
                        slave = QStackWidget(master=False,
                                             rgbwidget=self.rgbWidget)
                        slave.setStack(stack[i])
                        if slave is not None:
                            if i == 1:
                                self.setSlave(slave)
                            else:
                                self.addSlave(slave)
        else:
            self.setStack(stack)

    def loadSlaveStack(self):
        if self._slaveList is not None:
            actionList = ['Replace Slaves',
                          'Load Slaves',
                          'Show Slaves',
                          'Merge Slaves',
                          'Delete Slaves']
            menu = qt.QMenu(self)
            for action in actionList:
                text = QString(action)
                menu.addAction(text)
            a = menu.exec(qt.QCursor.pos())
            if a is None:
                return None
            if qt.safe_str(a.text()).startswith("Replace"):
                _logger.info("Replacing slave stacks")
                self._closeSlave()
            elif qt.safe_str(a.text()).startswith("Load"):
                _logger.info("Loading an additional slave stack")
                #self._closeSlave()
            elif qt.safe_str(a.text()).startswith("Show"):
                _logger.info("Showing all the slaves")
                for slave in self._slaveList:
                    slave.show()
                    slave.raise_()
                return
            elif qt.safe_str(a.text()).startswith("Merge"):
                masterStackDataObject = self.getStackDataObject()
                try:
                    # Use views to ensure no casting is done in case of
                    # different dtype to save memory.
                    # This is risky when the original stack is integers
                    # due to the possibility to overflow.
                    for slave in self._slaveList:
                        masterStackDataObject.data[:] = \
                                            masterStackDataObject.data[:] + \
                                            slave.getStackData()
                except:
                    msg = qt.QMessageBox(self)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setWindowTitle("Stack Summing Error")
                    msg.setText("An error has occurred while summing the master and slave stacks")
                    msg.setInformativeText(qt.safe_str(sys.exc_info()[1]))
                    msg.setDetailedText(traceback.format_exc())
                    msg.exec()
                if "McaLiveTime" in masterStackDataObject.info:
                    try:
                        for slave in self._slaveList:
                            info = slave.getStackInfo()
                            if "McaLiveTime" in info:
                                info["McaLiveTime"].shape = \
                                   masterStackDataObject.info["McaLiveTime"].shape
                                masterStackDataObject.info["McaLiveTime"] += \
                                        info["McaLiveTime"]
                            else:
                                raise ValueError("No compatible time information")
                    except:
                        msg = qt.QMessageBox(self)
                        msg.setIcon(qt.QMessageBox.Critical)
                        msg.setWindowTitle("Stack Time Summing Error")
                        txt = "An error has occurred cumulating the master and slave times\n"
                        txt += "Time information is lost"
                        del masterStackDataObject.info["McaLiveTime"]
                        msg.setText(txt)
                        msg.setInformativeText(qt.safe_str(sys.exc_info()[1]))
                        msg.setDetailedText(traceback.format_exc())
                        msg.exec()
                self._closeSlave()
                self.setStack(masterStackDataObject)
                return
            else:
                _logger.info("Deleting all the slaves")
                self._closeSlave()
                return
        if self.stackSelector is None:
            self.stackSelector = StackSelector.StackSelector(self)

        try:
            stack = self.stackSelector.getStack()
        except:
            txt = "%s" % sys.exc_info()[1]
            if txt.startswith("Incomplete selection"):
                return
            msg = qt.QMessageBox(self)
            msg.setWindowTitle("Error loading slave stack")
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("%s: %s" % (sys.exc_info()[0], sys.exc_info()[1]))
            msg.exec()
            return
        if stack is None:
            return
        if (type(stack) == type([])) or (isinstance(stack, list)):
            #self._closeSlave()
            for i in range(len(stack)):
                if stack[i] is not None:
                    slave = QStackWidget(master=False,
                                         rgbwidget=widget.rgbWidget)
                    slave.setStack(stack[i])
                    widget.addSlave(slave)
                    stack[i] = None
        else:
            slave = QStackWidget(rgbwidget=self.rgbWidget,
                                 master=False)
            slave.setStack(stack)
            self.addSlave(slave)

    def _closeSlave(self):
        if self._slaveList is None:
            return
        for slave in self._slaveList:
            slave.close()
        slave = None
        self._slaveList = None
        # make sure memory is released
        import gc
        gc.collect()

    def setSlave(self, slave):
        if self._slaveList is None:
            self._slaveList = []
        for slave in self._slaveList:
            slave.close()
        self._slaveList = None
        self.addSlave(slave)

    def addSlave(self, slave):
        _logger.info("Adding slave with id %d" % id(slave))
        if self._slaveList is None:
            self._slaveList = []
        slave.setSelectionMask(self.getSelectionMask())
        slave.show()
        slave._setMaster(self)
        self._slaveList.append(slave)

    def _setMaster(self, master=None):
        if self.master:
            self._masterStack = None
            return
        if master is None:
            master = self
        self._masterStack = weakref.proxy(master)

    def getStackDataObjectList(self):
        stackList = []
        if self.master:
            # master, join all slaves
            stackList.append(self.getStackDataObject())
            if self._slaveList is not None:
                for slave in self._slaveList:
                    stackList.append(slave.getStackDataObject())
        else:
            # slave, join master
            stackList.append(self._masterStack.getStackDataObject())
            stackList.append(self.getStackDataObject())
        return stackList

    def _pluginClicked(self):
        actionList = []
        menu = qt.QMenu(self)
        text = QString("Reload Plugins")
        menu.addAction(text)
        actionList.append(text)
        text = QString("Set User Plugin Directory")
        menu.addAction(text)
        actionList.append(text)
        global _logger
        if _logger.getEffectiveLevel() == logging.DEBUG:
            text = QString("Toggle DEBUG mode OFF")
        else:
            text = QString("Toggle DEBUG mode ON")
        menu.addAction(text)
        actionList.append(text)
        menu.addSeparator()
        callableKeys = ["Dummy0", "Dummy1", "Dummy2"]
        additionalItems = []
        SORTED = True
        for m in self.pluginList:
            if m == "PyMcaPlugins.StackPluginBase":
                continue
            module = sys.modules[m]
            if hasattr(module, 'MENU_TEXT'):
                text = QString(module.MENU_TEXT)
            else:
                text = os.path.basename(module.__file__)
                if text.endswith('.pyc'):
                    text = text[:-4]
                elif text.endswith('.py'):
                    text = text[:-3]
                text = QString(text)
            methods = self.pluginInstanceDict[m].getMethods()
            if not len(methods):
                continue
            if SORTED:
                additionalItems.append((text, m))
            else:
                menu.addAction(text)
                actionList.append(text)
                callableKeys.append(m)
        additionalItems.sort()
        for text, m in additionalItems:
            menu.addAction(text)
            actionList.append(text)
            callableKeys.append(m)
        a = menu.exec(qt.QCursor.pos())
        if a is None:
            return None
        idx = actionList.index(a.text())
        if idx == 0:
            n = self.getPlugins()
            if n < 1:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Information)
                msg.setText("Problem loading plugins")
                msg.exec()
            return
        if idx == 1:
            dirName = qt.safe_str(qt.QFileDialog.getExistingDirectory(self,
                                "Enter user plugins directory",
                                os.getcwd()))
            if len(dirName):
                pluginsDir = self.getPluginDirectoryList()
                pluginsDirList = [pluginsDir[0], dirName]
                self.setPluginDirectoryList(pluginsDirList)
            return
        if idx == 2:
            if _logger.getEffectiveLevel() == logging.DEBUG:
                _logger.setLevel(logging.DEBUG)
                StackBase.logger.setLevel(logging.DEBUG)
            else:
                _logger.setLevel(logging.NOTSET)
                StackBase.logger.setLevel(logging.NOTSET)
            return
        key = callableKeys[idx]
        methods = self.pluginInstanceDict[key].getMethods()
        if len(methods) == 1:
            idx = 0
        else:
            actionList = []
            #methods.sort()
            menu = qt.QMenu(self)
            for method in methods:
                text = QString(method)
                pixmap = self.pluginInstanceDict[key].getMethodPixmap(method)
                tip = QString(self.pluginInstanceDict[key].getMethodToolTip(\
                                                                    method))
                if pixmap is not None:
                    action = qt.QAction(qt.QIcon(qt.QPixmap(pixmap)),
                                        text,
                                        self)
                else:
                    action = qt.QAction(text, self)
                if tip is not None:
                    action.setToolTip(tip)
                menu.addAction(action)
                actionList.append((text, pixmap, tip, action))
            menu.hovered.connect(self._actionHovered)
            a = menu.exec(qt.QCursor.pos())
            if a is None:
                return None
            idx = -1
            for action in actionList:
                if a.text() == action[0]:
                    idx = actionList.index(action)
        try:
            self.pluginInstanceDict[key].applyMethod(methods[idx])
        except:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setWindowTitle("Plugin error")
            msg.setText("An error has occured while executing the plugin:")
            msg.setInformativeText(qt.safe_str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
            if _logger.getEffectiveLevel() == logging.DEBUG:
                raise

    def _actionHovered(self, action):
        tip = action.toolTip()
        if qt.safe_str(tip) != qt.safe_str(action.text()):
            qt.QToolTip.showText(qt.QCursor.pos(), tip)


    def _buildBottom(self):
        n = 0
        self.tab = None
        if self.mcaWidget is None:
            n += 1
        if self.rgbWidget is None:
            n += 1
        if n == 1:
            if self.mcaWidget is None:
                self.mcaWidget = McaWindow.McaWindow(self)
                self.mcaWidget.setWindowTitle("PyMCA - Mca Window")
                self.mainLayout.addWidget(self.mcaWidget)
            if self.rgbWidget is None:
                self.rgbWidget = RGBCorrelator.RGBCorrelator(self)
                self.mainLayout.addWidget(self.rgbWidget)
        elif n == 2:
            self.tab = qt.QTabWidget(self)
            self.mcaWidget = McaWindow.McaWindow() #vertical=False
            #self.mcaWidget.graph.setMinimumWidth(0.5 * \
            #                            qt.QWidget.sizeHint(self).width())
            self.tab.setMaximumHeight(int(1.3 * \
                                          qt.QWidget.sizeHint(self).height()))
            self.mcaWidget.setWindowTitle("PyMCA - Mca Window")
            self.tab.addTab(self.mcaWidget, "MCA")
            self.rgbWidget = RGBCorrelator.RGBCorrelator()
            self.tab.addTab(self.rgbWidget, "RGB Correlator")
            self.mainLayout.addWidget(self.tab)
        self.mcaWidget.setMiddleROIMarkerFlag(True)

    def _buildAndConnectButtonBox(self):
        #the MCA selection
        self.mcaButtonBox = qt.QWidget(self.stackWindow)
        self.mcaButtonBoxLayout = qt.QHBoxLayout(self.mcaButtonBox)
        self.mcaButtonBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.mcaButtonBoxLayout.setSpacing(0)
        self.addMcaButton = qt.QPushButton(self.mcaButtonBox)
        self.addMcaButton.setText("ADD MCA")
        self.removeMcaButton = qt.QPushButton(self.mcaButtonBox)
        self.removeMcaButton.setText("REMOVE MCA")
        self.replaceMcaButton = qt.QPushButton(self.mcaButtonBox)
        self.replaceMcaButton.setText("REPLACE MCA")
        self.mcaButtonBoxLayout.addWidget(self.addMcaButton)
        self.mcaButtonBoxLayout.addWidget(self.removeMcaButton)
        self.mcaButtonBoxLayout.addWidget(self.replaceMcaButton)

        self.stackWindow.mainLayout.addWidget(self.mcaButtonBox)

        self.addMcaButton.clicked.connect(self.__addMcaClicked)
        self.removeMcaButton.clicked.connect(self._removeMcaClicked)
        self.replaceMcaButton.clicked.connect(self._replaceMcaClicked)

        if self.rgbWidget is not None:
            # The IMAGE selection
            self.roiWidget.buildAndConnectImageButtonBox()

    def _buildConnections(self):
        self._buildAndConnectButtonBox()

        #ROI Image
        widgetList = [self.stackWidget, self.roiWidget]
        if self.rgbWidget is not None:
            if hasattr(self.rgbWidget, "sigMaskImageWidgetSignal"):
                widgetList.append(self.rgbWidget)

        for widget in widgetList:
            widget.sigMaskImageWidgetSignal.connect(self._maskImageWidgetSlot)

        #self.stackGraphWidget.graph.canvas().setMouseTracking(1)

        # infoText gives problems with recent matplotlib versions
        # self.stackGraphWidget.setInfoText("    X = ???? Y = ???? Z = ????")
        # self.stackGraphWidget.showInfo()

        self.stackGraphWidget.graph.sigPlotSignal.connect( \
                                    self._stackGraphSignal)

        self.mcaWidget.sigROISignal.connect(self._mcaWidgetSignal)
        self.roiWidget.graphWidget.graph.sigPlotSignal.connect( \
                                    self._stackGraphSignal)

    def showOriginalImage(self):
        self.stackGraphWidget.graph.setGraphTitle("Original Stack")
        if self._stackImageData is None:
            self.stackGraphWidget.graph.clear()
            return
        xScale = self._stack.info.get("xScale", None)
        yScale = self._stack.info.get("yScale", None)
        self.stackWidget.setImageData(self._stackImageData,
                                      xScale=xScale,
                                      yScale=yScale)

    def showOriginalMca(self):
        goodData = numpy.isfinite(self._mcaData0.y[0].sum())
        if goodData:
            self.sendMcaSelection(self._mcaData0, action="ADD")

    def handleNonFiniteData(self):
        self._addMcaClicked(action="ADD")
        msg = qt.QMessageBox(self)
        msg.setIcon(qt.QMessageBox.Information)
        msg.setWindowTitle("Non finite data")
        text = "Your data contain infinite values or nans.\n"
        text += "Pixels containing those values will be ignored."
        msg.setText(text)
        msg.exec()
        return

    def calculateROIImages(self, index1, index2, imiddle=None, energy=None):
        #overwrite base method to update the default energy with the one
        # currently used in the graph
        activeCurve = self.mcaWidget.getActiveCurve()
        if activeCurve is None:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Information)
            msg.setWindowTitle("No active curve selected")
            text = "Please select the MCA active curve."
            msg.setText(text)
            msg.exec()
            return
        x, y, legend, info = activeCurve[:4]
        return StackBase.StackBase.calculateROIImages(self,
                                                      index1,
                                                      index2,
                                                      imiddle=imiddle,
                                                      energy=x)

    def showROIImageList(self, imageList, image_names=None):
        xScale = self._stack.info.get("xScale", None)
        yScale = self._stack.info.get("yScale", None)
        if self.roiBackgroundButton.isChecked():
            self.roiWidget.graphWidget.graph.setGraphTitle(image_names[0] + \
                                                           " Net")
            self.roiWidget.setImageData(imageList[0]-imageList[-1],
                                        xScale=xScale,
                                        yScale=yScale)
        else:
            self.roiWidget.graphWidget.graph.setGraphTitle(image_names[0])
            self.roiWidget.setImageData(imageList[0],
                                        xScale=xScale,
                                        yScale=yScale)
        self._ROIImageList = imageList
        self._ROIImageNames = image_names
        self._stackROIImageListUpdated()

    def addImage(self, image, name, info=None, replace=False, replot=True):
        self.rgbWidget.addImage(image, name)
        if self.tab is None:
            if self.master:
                self.rgbWidget.show()
        else:
            self.tab.setCurrentWidget(self.rgbWidget)

    def removeImage(self, title):
        self.rgbWidget.removeImage(title)

    def replaceImage(self, image, title, info=None, replace=True, replot=True):
        self.rgbWidget.reset()
        self.rgbWidget.addImage(image, title)
        if self.rgbWidget.isHidden():
            self.rgbWidget.show()
        if self.tab is None:
            self.rgbWidget.show()
            self.rgbWidget.raise_()
        else:
            self.tab.setCurrentWidget(self.rgbWidget)

    def _addImageClicked(self, image, title):
        self.addImage(image, title)

    def _removeImageClicked(self, title):
        self.rgbWidget.removeImage(title)

    def _replaceImageClicked(self, image, title):
        self.replaceImage(image, title)

    def __getLegend(self):
        if self._selectionMask is None:
            legend = "Stack SUM"
        elif self._selectionMask.sum() == 0:
            legend = "Stack SUM"
        else:
            title = qt.safe_str(self.roiGraphWidget.graph.getGraphTitle())
            legend = "Stack " + title + " selection"
        return legend

    def __addMcaClicked(self):
        self._addMcaClicked("ADD")

    def _addMcaClicked(self, action=None):
        if action in [None, False]:
            action = "ADD"
        if self._stackImageData is None:
            return

        if self.normalizeButton.isChecked():
            dataObject = self.calculateMcaDataObject(normalize=True)
        else:
            dataObject = self.calculateMcaDataObject(normalize=False)
        legend = self.__getLegend()

        if self.normalizeButton.isChecked():
            if self._selectionMask is None:
                npixels = self._stackImageData.shape[0] * \
                          self._stackImageData.shape[1]
            else:
                npixels = self._selectionMask.sum()
                if npixels == 0:
                    npixels = self._stackImageData.shape[0] * \
                              self._stackImageData.shape[1]
            legend += "/%d" % npixels
        return self.sendMcaSelection(dataObject,
                                     key="Selection",
                                     legend=legend,
                                     action=action)

    def _removeMcaClicked(self):
        #remove the mca
        #dataObject = self.__mcaData0
        #send a dummy object
        dataObject = DataObject.DataObject()
        legend = self.__getLegend()
        if self.normalizeButton.isChecked():
            legend += "/"
            curves = self.mcaWidget.getAllCurves(just_legend=True)
            for curve in curves:
                if curve.startswith(legend):
                    legend = curve
                    break
        self.sendMcaSelection(dataObject, legend=legend, action="REMOVE")

    def _replaceMcaClicked(self):
        #replace the mca
        self.__ROIConnected = False
        self._addMcaClicked(action="REPLACE")
        self.__ROIConnected = True

    def sendMcaSelection(self, mcaObject, key=None, legend=None, action=None):
        if action is None:
            action = "ADD"
        if key is None:
            key = "SUM"
        if legend is None:
            legend = "Stack SUM"
            if self.normalizeButton.isChecked():
                npixels = self._stackImageData.shape[0] *\
                          self._stackImageData.shape[1]
                legend += "/%d" % npixels
        sel = {}
        sel['SourceName'] = "EDF Stack"
        sel['Key'] = key
        sel['legend'] = legend
        sel['dataobject'] = mcaObject
        if action == "ADD":
            self.mcaWidget._addSelection([sel])
        elif action == "REMOVE":
            self.mcaWidget._removeSelection([sel])
        elif action == "REPLACE":
            self.mcaWidget._replaceSelection([sel])
        elif action == "GET_CURRENT_SELECTION":
            return sel
        if self.tab is None:
            self.mcaWidget.show()
            self.mcaWidget.raise_()
        else:
            self.tab.setCurrentWidget(self.mcaWidget)

    def setSelectionMask(self, mask, instance_id=None):
        if mask is not None:
            if self._stackImageData is not None:
                if mask.shape != self._stackImageData.shape:
                    _logger.info("Reshaping mask")
                    mask.shape = self._stackImageData.shape
        self._selectionMask = mask
        if instance_id == id(self):
            return

        if self._slaveList is not None:
            _logger.debug("MASTER  setSelectionMask CALLED")
        elif self._masterStack is not None:
            _logger.debug("SLAVE setSelectionMask CALLED")

        #inform built in widgets
        widgetList = [self.stackWidget, self.roiWidget]
        for widget in widgetList:
            if instance_id != id(widget):
                if mask is None:
                    if hasattr(widget, "_resetSelection"):
                        widget._resetSelection(owncall=False)
                    else:
                        widget.setSelectionMask(mask, plot=True)
                else:
                    widget.setSelectionMask(mask, plot=True)

        if self.rgbWidget is not None:
            if hasattr(self.rgbWidget, "setSelectionMask"):
                self.rgbWidget.setSelectionMask(mask, instance_id=instance_id)

        #inform slave
        if self._slaveList is not None:
            #This is a master instance
            for slave in self._slaveList:
                instanceList = [id(slave),
                                id(slave.stackWidget),
                                id(slave.roiWidget)]
                for key in slave.pluginInstanceDict.keys():
                    instanceList.append(id(slave.pluginInstanceDict[key]))
                if instance_id not in instanceList:
                    #Originated by the master
                    _logger.warning("INFORMING SLAVE")
                    slave.setSelectionMask(mask, instance_id=id(self))

        if self._masterStack is not None:
            #This is a slave instance
            instanceList = [id(self.stackWidget),
                            id(self.roiWidget)]
            for key in self.pluginInstanceDict.keys():
                instanceList.append(id(self.pluginInstanceDict[key]))
            if instance_id in instanceList:
                #Originated by the slave
                _logger.debug("INFORMING MASTER")
                self._masterStack.setSelectionMask(mask, instance_id=id(self))

        #Inform plugins
        for key in self.pluginInstanceDict.keys():
            if key == "PyMcaPlugins.StackPluginBase":
                continue
            #I remove this optimization for the case the plugin
            #does not update itself the mask
            #if id(self.pluginInstanceDict[key]) != instance_id:
            self.pluginInstanceDict[key].selectionMaskUpdated()

    def getSelectionMask(self):
        return self._selectionMask

    def _maskImageWidgetSlot(self, ddict):
        if ddict['event'] == "selectionMaskChanged":
            self.setSelectionMask(ddict['current'], instance_id=ddict['id'])
            return
        if ddict['event'] == "resetSelection":
            self.setSelectionMask(None, instance_id=ddict['id'])
            return
        if ddict['event'] == "addImageClicked":
            self._addImageClicked(ddict['image'], ddict['title'])
            return
        if ddict['event'] == "replaceImageClicked":
            self._replaceImageClicked(ddict['image'], ddict['title'])
            return
        if ddict['event'] == "removeImageClicked":
            self._removeImageClicked(ddict['title'])
            return
        if ddict['event'] == "hFlipSignal":
            if ddict['id'] != id(self.stackWidget):
                self.stackWidget.graph.invertYAxis(ddict['current'])
                self.stackWidget.graph.replot()
            if ddict['id'] != id(self.roiWidget):
                self.roiWidget.graph.invertYAxis(ddict['current'])
                self.roiWidget.graph.replot()
            return

    def _stackGraphSignal(self, ddict):
        if ddict['event'] in ["mouseMoved", "MouseAt"]:
            x = round(ddict['y'])
            if x < 0:
                x = 0
            y = round(ddict['x'])
            if y < 0:
                y = 0
            if self._stackImageData is None:
                return
            limits = self._stackImageData.shape
            x = min(int(x), limits[0]-1)
            y = min(int(y), limits[1]-1)
            z = self._stackImageData[x, y]
            self.stackGraphWidget.setInfoText( \
                    "    X = %d Y = %d Z = %.4g" % (y, x, z))

        if ddict['event'] in ["mouseDoubleClicked"]:
            if ddict['button'] == "left":
                if self._stackImageData is None:
                    return
                # x and y arrive in scaled coordinates
                # we need to convert them to row and column
            if None in [ddict['x'], ddict['y']]:
                _logger.debug("Signal from outside region %s", ddict)
                return
            xScale = self._stack.info.get("xScale", None)
            yScale = self._stack.info.get("yScale", None)
            row, column = MaskImageWidget.convertToRowAndColumn(ddict['x'],
                                      ddict['y'],
                                      self._stackImageData.shape,
                                      xScale=xScale,
                                      yScale=yScale,
                                      safe=True)
            ddict['row'] = row
            ddict['col'] = column
            selectionMask = numpy.zeros(self._stackImageData.shape,
                                     numpy.uint8)
            selectionMask[row, column] = 1
            dataObject = self.calculateMcaDataObject(normalize=True,
                                                     mask=selectionMask)
            self.sendMcaSelection(dataObject,
                                     key="Selection",
                                     legend="MCA[%d,%d]" % (row, column),
                                     action="ADD")

    def _mcaWidgetSignal(self, ddict):
        if not self.__ROIConnected:
            return
        if ddict['event'] in ["currentROISignal", "ROISignal"]:
            self.updateROIImages(ddict)

    def getActiveCurve(self):
        legend = self.mcaWidget.getActiveCurve(just_legend=True)
        if legend is None:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Please select an active curve")
            msg.exec()
            return
        x, y, legend, info = self.mcaWidget.getActiveCurve()[:4]
        return x, y, legend, info

    def getGraphXLimits(self):
        return self.mcaWidget.getGraphXLimits()

    def getGraphYLimits(self):
        return self.mcaWidget.getGraphYLimits()

    def getGraphXLabel(self):
        return self.mcaWidget.getGraphXLabel()

    def getGraphYLabel(self):
        return self.mcaWidget.getGraphYLabel()

    def closeEvent(self, event):
        if self._slaveList is not None:
            self._closeSlave()
        # Inform plugins
        for key in self.pluginInstanceDict.keys():
            self.pluginInstanceDict[key].stackClosed()
        CloseEventNotifyingWidget.CloseEventNotifyingWidget.closeEvent(self, event)
        if (self._masterStack is None) and __name__ == "__main__":
            app = qt.QApplication.instance()
            allWidgets = app.allWidgets()
            for widget in allWidgets:
                try:
                    # we cannot afford to crash here
                    if id(widget) != id(self):
                        if widget.parent() is None:
                            widget.close()
                except:
                    _logger.debug("Error closing widget")
            from PyMca5.PyMcaGui.plotting import PyMcaPrintPreview
            PyMcaPrintPreview.resetSingletonPrintPreview()


def test():
    #create a dummy stack
    nrows = 100
    ncols = 200
    nchannels = 1024
    a = numpy.ones((nrows, ncols), numpy.float64)
    stackData = numpy.zeros((nrows, ncols, nchannels), numpy.float64)
    for i in range(nchannels):
        stackData[:, :, i] = a * i
    stackData[0:10, :, :] = 0
    w = QStackWidget()
    w.setStack(stackData, mcaindex=2)
    w.show()
    return w


if __name__ == "__main__":
    sys.excepthook = qt.exceptionHandler
    try:
        opts, args = getopt.getopt(
                     sys.argv[1:],
                     options,
                     longoptions)
    except:
        print("%s" % sys.exc_info()[1])
        sys.exit(1)
    fileindex = 0
    filepattern=None
    begin = None
    end = None
    imagestack=None
    increment=None
    backend=None
    PyMcaDirs.nativeFileDialogs=True

    for opt, arg in opts:
        if opt in '--begin':
            if "," in arg:
                begin = [int(x) for x in arg.split(",")]
            else:
                begin = [int(arg)]
        elif opt in '--end':
            if "," in arg:
                end = [int(x) for x in arg.split(",")]
            else:
                end = int(arg)
        elif opt in '--increment':
            if "," in arg:
                increment = [int(x) for x in arg.split(",")]
            else:
                increment = int(arg)
        elif opt in '--filepattern':
            filepattern = arg.replace('"', '')
            filepattern = filepattern.replace("'", "")
        elif opt in '--fileindex':
            fileindex = int(arg)
        elif opt in ['--imagestack', "--image"]:
            imagestack = int(arg)
        elif opt in '--nativefiledialogs':
            if int(arg):
                PyMcaDirs.nativeFileDialogs = True
            else:
                PyMcaDirs.nativeFileDialogs = False
        elif opt in '--backend':
            backend = arg
        #elif opt in '--old':
        #    import QEDFStackWidget
        #    sys.exit(QEDFStackWidget.runAsMain())
    if filepattern is not None:
        if (begin is None) or (end is None):
            raise ValueError("A file pattern needs at least a set of begin and end indices")
    app = qt.QApplication([])
    if sys.platform not in ["win32", "darwin"]:
        # some themes of Ubuntu 16.04 give black tool tips on black background
        app.setStyleSheet("QToolTip { color: #000000; background-color: #fff0cd; border: 1px solid black; }")
    if backend is not None:
        # set the default backend
        try:
            from PyMca5.PyMcaGraph.Plot import Plot
            Plot.defaultBackend = backend
        except:
            _logger.warning("WARNING: Cannot set backend to %s", backend)
    widget = QStackWidget()
    w = StackSelector.StackSelector(widget)
    if filepattern is not None:
        #ignore the args even if present
        stack = w.getStackFromPattern(filepattern, begin, end, increment=increment,
                                      imagestack=imagestack)
    else:
        stack = w.getStack(args, imagestack=imagestack)
    if (type(stack) == type([])) or (isinstance(stack, list)):
        #aifira like, two stacks
        widget.setStack(stack[0])
        if len(stack) > 1:
            for i in range(1, len(stack)):
                if stack[i] is not None:
                    slave = QStackWidget(master=False,
                                         rgbwidget=widget.rgbWidget)
                    slave.setStack(stack[i])
                    widget.addSlave(slave)
        stack = None
    else:
        widget.setStack(stack)
    widget.show()
    app.exec()
    app = None

