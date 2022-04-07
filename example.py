import sys
import asyncio
import logging
sys.path.append('./PC-60FW')
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtWidgets


from oximeter import Oximeter

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)



   

### START QtApp #####
app = QtWidgets.QApplication(sys.argv)            # you MUST do this once (initialize things)
####################

win = pg.GraphicsLayoutWidget(title="PC-60FW") # creates a window
p1 = win.addPlot(row=0, col=0, title="Wave plot")  # creates empty space for the plot in the window
p1.setYRange(-100,100,padding=0)
p1.setXRange(0,500,padding=0)
p2 = win.addPlot(row=1, col=0, title="HR plot")
p2.setYRange(0,300,padding=0)
curve1 = p1.plot()   # create an empty "plot" (a curve to plot)
curve2 = p2.plot()                     
Xm = np.zeros(500)          # create array that will contain the relevant time series   
Xo = np.array([0])



def printdata(data):
    print(data)

def wavegraph(data):
    global curve1, curve2, Xm, Xo
    
    for d in data:
        wavegraph.n +=1
        wavegraph.t=(wavegraph.t+1)%500
        Xm[wavegraph.t] = (d & 127)-64  #remove maximum peak detection bit 
        if(d & 128): #maximum peak
            Xo=np.append(Xo,60/(wavegraph.n *0.02)) #calculate HR 
            wavegraph.n = 0

    curve1.setData(Xm)                     
    curve2.setData(Xo)                                         
    QtWidgets.QApplication.processEvents()
wavegraph.n=0 
wavegraph.t=0


async def main():
    o1 = Oximeter()
    print("Scanning...")
    devices = await o1.find()   
    if devices:
        print(devices)
        o1.setaddres(devices[0].address)
        o1.setWave_callback(wavegraph) #0.1s
        o1.setData_callback(printdata) #1s
        o1.setMode_callback(printdata) #1s
        await o1.run()
        win.show()
        
        while o1._client.is_connected:
            await asyncio.sleep(1.0)

    

if __name__ == "__main__":
    asyncio.run(main())
