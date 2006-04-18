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
# Form implementation generated from reading ui file 'FitStatusGUI.ui'
#
# Created: Wed Oct 16 17:44:27 2002
#      by: The PyQt User Interface Compiler (pyuic)
#
# WARNING! All changes made in this file will be lost!


from qt import *

def uic_load_pixmap_FitStatusGUI(name):
    pix = QPixmap()
    m = QMimeSourceFactory.defaultFactory().data(name)

    if m:
        QImageDrag.decode(m,pix)

    return pix


class FitStatusGUI(QWidget):
    def __init__(self,parent = None,name = None,fl = 0):
        QWidget.__init__(self,parent,name,fl)

        if name == None:
            self.setName("FitStatusGUI")

        self.resize(535,47)
        self.setCaption(str("FitStatusGUI"))

        FitStatusGUILayout = QHBoxLayout(self,11,6,"FitStatusGUILayout")

        self.StatusLabel = QLabel(self,"StatusLabel")
        self.StatusLabel.setText(str("Status:"))
        FitStatusGUILayout.addWidget(self.StatusLabel)

        self.StatusLine = QLineEdit(self,"StatusLine")
        self.StatusLine.setText(str("Ready"))
        self.StatusLine.setReadOnly(1)
        FitStatusGUILayout.addWidget(self.StatusLine)

        self.ChisqLabel = QLabel(self,"ChisqLabel")
        self.ChisqLabel.setText(str("Chisq:"))
        FitStatusGUILayout.addWidget(self.ChisqLabel)

        self.ChisqLine = QLineEdit(self,"ChisqLine")
        #self.ChisqLine.setSizePolicy(QSizePolicy(1,0,0,0,self.ChisqLine.sizePolicy().hasHeightForWidth()))
        self.ChisqLine.setMaximumSize(QSize(16000,32767))
        self.ChisqLine.setText(str(""))
        self.ChisqLine.setReadOnly(1)
        FitStatusGUILayout.addWidget(self.ChisqLine)
