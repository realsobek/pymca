#/*##########################################################################
# Copyright (C) 2004-2006 European Synchrotron Radiation Facility
#
# This file is part of the PyMCA X-ray Fluorescence Toolkit developed at
# the ESRF by the Beamline Instrumentation Software Support (BLISS) group.
#
# This toolkit is free software; you can redistribute it and/or modify it 
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option) 
# any later version.
#
# PyMCA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# PyMCA; if not, write to the Free Software Foundation, Inc., 59 Temple Place,
# Suite 330, Boston, MA 02111-1307, USA.
#
# PyMCA follows the dual licensing model of Trolltech's Qt and Riverbank's PyQt
# and cannot be used as a free plugin for a non-free program. 
#
# Please contact the ESRF industrial unit (industry@esrf.fr) if this license 
# is a problem to you.
#############################################################################*/
#!/usr/bin/env python
"""
This module implements several mathematical functions:
    - peak search
    - center of mass search
    - fwhm search
WARNING : array are Numeric.array objects.
"""

import Numeric

def search_peak(xdata,ydata):
     """
     Search a peak and its position in arrays xdata ad ydata. 
     Return three integer:
       - peak position
       - peak value
       - index of peak position in array xdata
         This result may accelerate the fwhm search.
     """
     ymax   = max(ydata)
     idx    = __give_index(ymax,ydata)
     return xdata[idx],ymax,idx


def search_com(xdata,ydata):
    """
    Return the center of mass in arrays xdata and ydata
    """
    num    = Numeric.sum(xdata*ydata)
    denom  = Numeric.sum(ydata)
    try:
       result = num/denom
    except ZeroDivisionError:
       result = 0
    return result


def search_fwhm(xdata,ydata,peak=None,index=None):
    """
    Search a fwhm and its center in arrays xdata and ydatas.
    If no fwhm is found, (0,0) is returned.
    peak and index which are coming from search_peak result, may
    accelerate calculation
    """
    if peak is None or index is None:
        x,mypeak,index_peak = search_peak(xdata,ydata)
    else:
        mypeak     = peak
        index_peak = index
    
    hm = mypeak/2
    idx = index_peak

    try:
        while ydata[idx] >= hm:
           idx = idx-1
        x0 = xdata[idx]
        x1 = xdata[idx+1]
        y0 = ydata[idx]
        y1 = ydata[idx+1]
    
        lhmx = (hm*(x1-x0) - (y0*x1)+(y1*x0)) / (y1-y0)
    except ZeroDivisionError:
        lhmx = 0 
    except IndexError:
        lhmx = xdata[0]

    idx = index_peak
    try:
        while ydata[idx] >= hm:
            idx = idx+1
    
        x0 = xdata[idx]
        x1 = xdata[idx+1]
        y0 = ydata[idx]
        y1 = ydata[idx+1]
    
        uhmx = (hm*(x1-x0) - (y0*x1)+(y1*x0)) / (y1-y0)
    except ZeroDivisionError:
        uhmx = 0
    except IndexError:
        uhmx = xdata[-1]

    FWHM  = uhmx - lhmx
    CFWHM = (uhmx+lhmx)/2
    return FWHM,CFWHM


def __give_index(elem,array):
     """
     Return the index of elem in array
     """
     mylist = array.tolist()
     return mylist.index(elem)


def test():
    pass

if __name__ == '__main__':
       test()
