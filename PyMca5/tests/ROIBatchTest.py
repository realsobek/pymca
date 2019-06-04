#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019 European Synchrotron Radiation Facility
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
__author__ = "V. Armando Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import unittest
import os
import sys
import numpy
import gc
import shutil

DEBUG = 0

class testROIBatch(unittest.TestCase):
    def setUp(self):
        """
        Get the data directory
        """
        try:
            from PyMca5.PyMcaCore import StackROIBatch
            self._importSuccess = True
        except:
            self._importSuccess = False

    def testImport(self):
        self.assertTrue(self._importSuccess,
                        'Unsuccessful PyMca5.PyMcaCore.StackROIBatch import')

    def testCalculation(self):
        from PyMca5.PyMcaCore.StackROIBatch import StackROIBatch
        x = numpy.arange(1000.)
        y = x + numpy.exp(-0.5*(x-500)**2)
        y.shape = 1, 1, -1

        config = {}
        config["ROI"] = {}
        config["ROI"]["roilist"] = ["roi1", "roi2", "roi3"]
        config["ROI"]["roidict"] = {}
        config["ROI"]["roidict"]["roi1"] = {}
        config["ROI"]["roidict"]["roi1"]["from"] = 10
        config["ROI"]["roidict"]["roi1"]["to"] = 20
        config["ROI"]["roidict"]["roi1"]["type"] = "Channel"
        config["ROI"]["roidict"]["roi2"] = {}
        config["ROI"]["roidict"]["roi2"]["from"] = 200
        config["ROI"]["roidict"]["roi2"]["to"] = 500
        config["ROI"]["roidict"]["roi2"]["type"] = "Channel"
        config["ROI"]["roidict"]["roi3"] = {}
        config["ROI"]["roidict"]["roi3"]["from"] = 200
        config["ROI"]["roidict"]["roi3"]["to"] = 500
        config["ROI"]["roidict"]["roi3"]["type"] = "Channel"
        
        instance = StackROIBatch()
        outputDict = instance.batchROIMultipleSpectra(x=x,
                                                      y=y,
                                                      configuration=config,
                                                      net=True)
        images = outputDict["images"]
        names = outputDict["names"]

        # target values
        xproc = x
        yproc = y[0, 0, :]
        for roi in config["ROI"]["roidict"]:        
            toData = config["ROI"]["roidict"][roi]["to"]
            fromData = config["ROI"]["roidict"][roi]["from"]
            idx = numpy.nonzero((fromData <= xproc) & (xproc <= toData))[0]
            if len(idx):
                    xw = xproc[idx]
                    yw = yproc[idx]
                    rawCounts = yw.sum(dtype=numpy.float)
                    deltaX = xw[-1] - xw[0]
                    deltaY = yw[-1] - yw[0]
                    if deltaX > 0.0:
                        slope = (deltaY/deltaX)
                        background = yw[0] + slope * (xw - xw[0])
                        netCounts = rawCounts -\
                                    background.sum(dtype=numpy.float)
                    else:
                        netCounts = 0.0
            else:
                rawCounts = 0.0
                netCounts = 0.0
            config["ROI"]["roidict"][roi]["rawcounts"] = rawCounts
            config["ROI"]["roidict"][roi]["netcounts"] = netCounts
            print("names= ", names)
            rawName = "ROI " + roi + ""
            netName = "ROI " + roi + " Net"
            imageRaw = images[names.index(rawName)]
            imageNet = images[names.index(netName)]
            print("ROI = ", roi)
            print("rawCounts = ", rawCounts)
            print("imageRawCounts = ", imageRaw[0, 0])
            print("netCounts = ", netCounts)
            print("imageNetCounts = ", imageNet[0, 0])
            self.assertTrue(imageRaw[0, 0] == rawCounts,
                            "Incorrect calculation for raw roi %s" % roi)
            self.assertTrue(imageNet[0, 0] == netCounts,
                            "Incorrect calculation for net roi %s delta = %f" % \
                            (roi, imageNet[0, 0] - netCounts))

def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(unittest.TestLoader().loadTestsFromTestCase( \
                                    testROIBatch))
    else:
        # use a predefined order
        testSuite.addTest(testROIBatch("testImport"))
        testSuite.addTest(testROIBatch("testCalculation"))
    return testSuite

def test(auto=False):
    return unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        auto = False
    else:
        auto = True
    result = test(auto)
    sys.exit(not result.wasSuccessful())
