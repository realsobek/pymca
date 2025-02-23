#/*##########################################################################
# Copyright (C) 2004-2015 V.A. Sole, European Synchrotron Radiation Facility
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
"""

A Stack plugin is a module that will be automatically added to the PyMca stack windows
in order to perform user defined operations on the data stack.

These plugins will be compatible with any stack window that provides the functions:
    #data related
    getStackDataObject
    getStackData
    getStackInfo
    setStack

    #images related
    addImage
    removeImage
    replaceImage

    #mask related
    setSelectionMask
    getSelectionMask

    #displayed curves
    getActiveCurve
    getGraphXLimits
    getGraphYLimits

    #information method
    stackUpdated
    selectionMaskUpdated
"""
import sys
import os
import numpy
import logging
import traceback
from PyMca5 import StackPluginBase
from PyMca5.PyMcaPhysics import FastXRFLinearFit
from PyMca5.PyMcaPhysics import XRFBatchFitOutput
from PyMca5.PyMcaGui import FastXRFLinearFitWindow
from PyMca5.PyMcaGui import CalculationThread
from PyMca5.PyMcaGui import StackPluginResultsWindow
from PyMca5.PyMcaGui import PyMca_Icons as PyMca_Icons
from PyMca5.PyMcaGui import PyMcaQt as qt

_logger = logging.getLogger(__name__)


class FastXRFLinearFitStackPlugin(StackPluginBase.StackPluginBase):
    def __init__(self, stackWindow, **kw):
        if _logger.getEffectiveLevel() == logging.DEBUG:
            StackPluginBase.pluginBaseLogger.setLevel(logging.DEBUG)
        StackPluginBase.StackPluginBase.__init__(self, stackWindow, **kw)
        self.methodDict = {}
        function = self.calculate
        info = "Fit stack with a fit configuration"
        icon = PyMca_Icons.fit
        self.methodDict["Fit Stack"] =[function,
                                       info,
                                       icon]
        function = self._showWidget
        info = "Show last results"
        icon = PyMca_Icons.brushselect
        self.methodDict["Show"] =[function,
                                  info,
                                  icon]
        self.__methodKeys = ["Fit Stack", "Show"]
        self.configurationWidget = None
        self.fitInstance = None
        self._widget = None
        self.thread = None

    def stackUpdated(self):
        _logger.debug("FastXRFLinearFitStackPlugin.stackUpdated() called")
        self._widget = None

    def selectionMaskUpdated(self):
        if self._widget is None:
            return
        if self._widget.isHidden():
            return
        mask = self.getStackSelectionMask()
        self._widget.setSelectionMask(mask)

    def mySlot(self, ddict):
        _logger.debug("mySlot ", ddict['event'], ddict.keys())
        if ddict['event'] == "selectionMaskChanged":
            self.setStackSelectionMask(ddict['current'])
        elif ddict['event'] == "addImageClicked":
            self.addImage(ddict['image'], ddict['title'])
        elif ddict['event'] == "addAllClicked":
            for i in range(len(ddict["images"])):
                self.addImage(ddict['images'][i], ddict['titles'][i])            
        elif ddict['event'] == "removeImageClicked":
            self.removeImage(ddict['title'])
        elif ddict['event'] == "replaceImageClicked":
            self.replaceImage(ddict['image'], ddict['title'])
        elif ddict['event'] == "resetSelection":
            self.setStackSelectionMask(None)

    #Methods implemented by the plugin
    def getMethods(self):
        if self._widget is None:
            return [self.__methodKeys[0]]
        else:
            return self.__methodKeys

    def getMethodToolTip(self, name):
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        return self.methodDict[name][2]

    def applyMethod(self, name):
        return self.methodDict[name][0]()

    # The specific part
    def calculate(self):
        if self.configurationWidget is None:
            self.configurationWidget = \
                            FastXRFLinearFitWindow.FastXRFLinearFitDialog()
        ret = self.configurationWidget.exec()
        if ret:
            self._executeFunctionAndParameters()

    def _executeFunctionAndParameters(self):
        self._parameters = self.configurationWidget.getParameters()
        self._widget = None
        if self.fitInstance is None:
            self.fitInstance = FastXRFLinearFit.FastXRFLinearFit()
        #self._fitConfigurationFile="E:\DATA\COTTE\CH1777\G4-4720eV-NOWEIGHT-Constant-batch.cfg"

        if _logger.getEffectiveLevel() == logging.DEBUG:
            self.thread = CalculationThread.CalculationThread(\
                            calculation_method=self.actualCalculation)
            self.thread.result = self.actualCalculation()
            self.threadFinished()
        else:
            self.thread = CalculationThread.CalculationThread(\
                            calculation_method=self.actualCalculation)
            self.thread.finished.connect(self.threadFinished)
            self.thread.start()
            message = "Please wait. Calculation going on."
            CalculationThread.waitingMessageDialog(self.thread,
                                parent=self.configurationWidget,
                                message=message)

    def actualCalculation(self):
        activeCurve = self.getActiveCurve()
        if activeCurve is not None:
            x, spectrum, legend, info = activeCurve
        else:
            x = None
            spectrum = None
        if not self.isStackFinite():
            # one has to check for NaNs in the used region(s)
            # for the time being only in the global image
            # spatial_mask = numpy.isfinite(image_data)
            spatial_mask = numpy.isfinite(self.getStackOriginalImage())
            # WDN: any effect?
        stack = self.getStackDataObject()

        fitparams = self._parameters['fit'].copy()
        fitConfigurationFile = fitparams.pop('configuration')
        self.fitInstance.setFitConfigurationFile(fitConfigurationFile)
        if fitparams['weight']:
            # force calculation of the unnormalized sum spectrum
            spectrum = None
        if stack.x in [None, []]:
            x = None
        else:
            x = stack.x[0]

        outparams = self._parameters['output']
        outbuffer = XRFBatchFitOutput.OutputBuffer(**outparams)
        outbuffer = self.fitInstance.fitMultipleSpectra(x=x,
                                                        y=stack,
                                                        ysum=spectrum,
                                                        outbuffer=outbuffer,
                                                        save=False,  # do it later
                                                        **fitparams)
        return outbuffer

    def threadFinished(self):
        try:
            self._threadFinished()
        except:
            msg = qt.QMessageBox()
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setInformativeText(str(sys.exc_info()[1]))
            msg.setDetailedText(traceback.format_exc())
            msg.exec()

    def _threadFinished(self):
        result = self.thread.result
        self.thread = None
        if type(result) == type((1,)):
            #if we receive a tuple there was an error
            if len(result):
                if result[0] == "Exception":
                    # somehow this exception is not caught
                    raise Exception(result[1], result[2])#, result[3])
                    return

        # Show results
        with result.bufferContext(update=True):
            if 'molarconcentrations' in result:
                imageNames = result.labels('parameters', labeltype='title') + \
                             result.labels('molarconcentrations', labeltype='title')
                images = numpy.concatenate((result['parameters'],
                                            result['molarconcentrations']), axis=0)
            elif 'massfractions' in result:
                imageNames = result.labels('parameters', labeltype='title') + \
                             result.labels('massfractions', labeltype='title')
                images = numpy.concatenate((result['parameters'],
                                            result['massfractions']), axis=0)
            else:
                imageNames = result.labels('parameters', labeltype='title')
                images = result['parameters']
            self._widget = StackPluginResultsWindow.StackPluginResultsWindow(\
                                            usetab=False)
            self._widget.buildAndConnectImageButtonBox(replace=True,
                                                       multiple=True)
            qt = StackPluginResultsWindow.qt
            self._widget.sigMaskImageWidgetSignal.connect(self.mySlot)
            self._widget.setStackPluginResults(images,
                                               image_names=imageNames)
            self._showWidget()

            # Save results
            result.save()

    def _showWidget(self):
        if self._widget is None:
            return
        #Show
        self._widget.show()
        self._widget.raise_()

        #update
        self.selectionMaskUpdated()

MENU_TEXT = "Fast XRF Stack Fitting"
def getStackPluginInstance(stackWindow, **kw):
    ob = FastXRFLinearFitStackPlugin(stackWindow)
    return ob
