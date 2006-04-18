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
# Form implementation generated from reading ui file 'Notebook.ui'
#
# Created: Tue Jul 16 12:28:10 2002
#      by: The PyQt User Interface Compiler (pyuic)
#
# WARNING! All changes made in this file will be lost!


import sys
from qt import *
#from qttable import QTable
import Parameters
import McaTable
import string

class ParametersTab(QTabWidget):
    def __init__(self,parent = None,name = None,fl = 0):
#    def __init__(self,*args):
        QTabWidget.__init__(self, parent, name, fl)
        #apply(QTabWidget.__init__,(self,) + args)

        #if name == None:
        #    self.setName("FitParameters")
        
        #geometry
        #self.resize(570,300)
        #self.setCaption(self.trUtf8(name))
            
        #initialize the numer of tabs to 1
        #self.TabWidget=QTabWidget(self,"ParametersTab")
        #self.TabWidget.setGeometry(QRect(25,25,450,350))
        #the widgets in the notebook
        self.views={}
        #the names of the widgets (to have them in order)
        self.tabs=[]
        #the widgets/tables themselves
        self.tables={}
        self.mcatable=None
        self.setMargin(10)
        #create the first tab
        self.setview(name="Region 1")

    def setview(self,name=None,fitparameterslist=None):
        if name is None:
            name = self.current
        if name in self.tables.keys():
            table=self.tables[name]
        else:
            #create the parameters instance
            self.tables[name]=Parameters.Parameters(self)
            table=self.tables[name]
            self.tabs.append(name)
            self.views[name]=table
            #if qVersion() >= '3.0.0':
            #    self.addTab(table,self.trUtf8(name))
            #else:
            #    self.addTab(table,self.tr(name))
            self.addTab(table,str(name))
        if fitparameterslist is not None:
            table.fillfromfit(fitparameterslist)
        #print "SHowing page ",name
        self.showPage(self.views[name])
        self.current=name        

    def renameview(self,oldname=None,newname=None):
        error = 1
        if newname is not None:
            if newname not in self.views.keys():            
                if oldname in self.views.keys():
                    parameterlist=self.tables[oldname].fillfitfromtable()
                    self.setview(name=newname,fitparameterslist=parameterlist)
                    self.removeview(oldname)
                    error = 0
        return error

    def fillfromfit(self,fitparameterslist,current=None):
        if current is None:
            current=self.current
        #for view in self.tables.keys():
        #    self.removeview(view)
        self.setview(fitparameterslist=fitparameterslist,name=current)
        
    def fillfitfromtable(self,*vars,**kw):
        if len(vars) > 0:
            name=vars[0]
        elif kw.has_key('view'):
            name=kw['view']
        elif kw.has_key('name'):
            name=kw['name']
        else:
            name=self.current
        if hasattr(self.tables[name],'fillfitfromtable'):
            return self.tables[name].fillfitfromtable()
        else:
            return None       
    
    def removeview(self,*vars,**kw):
        error = 1
        if len(vars) > 0:
            view=vars[0]
        elif kw.has_key('view'):
            view=kw['view']
        elif kw.has_key('name'):
            view=kw['name']
        else:
            return error
        if view == self.current:
            return error
        if view in self.views.keys():
                self.tabs.remove(view)
                self.removePage(self.tables[view])
                self.removePage(self.views[view])
                del self.tables[view]
                del self.views[view]
                error =0
        return error

    def removeallviews(self,keep='Fit'):
        for view in self.tables.keys():
            if view != keep:
                self.removeview(view)

    def fillfrommca(self,mcaresult):
        #for view in self.tables.keys():
        #    self.removeview(view)
        self.removeallviews()
        region = 0
        for result in mcaresult:
             #if result['chisq'] is not None:
                region=region+1
                self.fillfromfit(result['paramlist'],current='Region '+`region`)
        name='MCA'
        if self.tables.has_key(name):
           table=self.tables[name]
        else:
           self.tables[name]=McaTable.McaTable(self)
           table=self.tables[name]       
           self.tabs.append(name)
           self.views[name]=table
           #self.addTab(table,self.trUtf8(name))
           self.addTab(table,str(name))
           self.connect(table,PYSIGNAL('McaTableSignal'),self.__forward)
        table.fillfrommca(mcaresult)
        self.setview(name=name)        
        return
        
    def __forward(self,dict):
        self.emit(PYSIGNAL('MultiParametersSignal'),(dict,))


    def gettext(self,**kw):
        if kw.has_key("name"):
            name = kw["name"]
        else:
            name = self.current
        table = self.tables[name]
        lemon=string.upper("#%x%x%x" % (255,250,205))
        if qVersion() < '3.0.0':
            hcolor = string.upper("#%x%x%x" % (230,240,249))
        else:
            hb = table.horizontalHeader().paletteBackgroundColor()
            hcolor = string.upper("#%x%x%x" % (hb.red(),hb.green(),hb.blue()))
        text=""
        text+=("<nobr>")
        text+=( "<table>")
        text+=( "<tr>")
        for l in range(table.numCols()):
            text+=('<td align="left" bgcolor="%s"><b>' % hcolor)
            text+=(str(table.horizontalHeader().label(l)))
            text+=("</b></td>")
        text+=("</tr>")
        #text+=( str(qt.QString("</br>"))
        for r in range(table.numRows()):
            text+=("<tr>")
            if len(str(table.text(r,0))):
                color = "white"
                b="<b>"                
            else:
                b=""
                color = lemon
            try:
                #MyQTable item has color defined
                cc = table.item(r,0).color
                cc = string.upper("#%x%x%x" % (cc.red(),cc.green(),cc.blue()))
                color = cc
            except:
                pass
            for c in range(table.numCols()):
                if len(table.text(r,c)):
                    finalcolor = color
                else:
                    finalcolor = "white"
                if c<2:
                    text+=('<td align="left" bgcolor="%s">%s' % (finalcolor,b))
                else:
                    text+=('<td align="right" bgcolor="%s">%s' % (finalcolor,b))
                text+=( str(table.text(r,c)))
                if len(b):
                    text+=("</td>")
                else:
                    text+=("</b></td>") 
            if len(str(table.text(r,0))):
                text+=("</b>")
            text+=("</tr>")
            #text+=( str(qt.QString("<br>"))
            text+=("\n")
        text+=("</table>")
        text+=("</nobr>")
        return text

def test():
    a = QApplication(sys.argv)
    QObject.connect(a,SIGNAL("lastWindowClosed()"),a,SLOT("quit()"))
    w = ParametersTab()
    a.setMainWidget(w)
    w.show()
    if 1:
        import specfile
        import Specfit
        import string
        from Numeric import sqrt,equal,array,Float,concatenate,arange,take,nonzero
        sf=specfile.Specfile('02021201.dat')
        scan=sf.select('14')
        #sf=specfile.Specfile('02022101.dat')
        #scan=sf.select('11')
        nbmca=scan.nbmca()
        mcadata=scan.mca(1)
        y=array(mcadata)
        #x=arange(len(y))
        x=arange(len(y))*0.0200511-0.003186
        fit=Specfit.Specfit()
        fit.setdata(x=x,y=y)
        fit.importfun("SpecfitFunctions.py")
        fit.settheory('Hypermet')
        fit.configure(Yscaling=1.,
                      WeightFlag=1,
                      PosFwhmFlag=1,
                      HeightAreaFlag=1,
                      FwhmPoints=50,
                      PositionFlag=1,
                      HypermetTails=1)        
        fit.setbackground('Linear')
        if 0:
            # build a spectrum array
            f=open("spec.arsp",'r')
            #read the spectrum datas
            x=array([],Float)
            y=array([],Float)
            tmp=f.readline()[:-1]
            while (tmp != ""):
                tmpSeq=tmp.split()
                x=concatenate((x,[float(tmpSeq[0])]))
                y=concatenate((y,[float(tmpSeq[1])]))
                tmp=f.readline()[:-1]
            fit.setdata(x=x,y=y)
        if 1:
            mcaresult=fit.mcafit(x=x,xmin=x[70],xmax=x[500])
            w.fillfrommca(mcaresult)
        else:
            fit.estimate()
            fit.startfit()
            w.fillfromfit(fit.paramlist,current='Fit')
            w.removeview(view='Region 1')

    a.exec_loop()
        
if __name__ == "__main__":
    bench=0
    if bench:
        import pstats
        import profile
        profile.run('test()',"test")
        p=pstats.Stats("test")
        p.strip_dirs().sort_stats(-1).print_stats()
    else:
        test()
