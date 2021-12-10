from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

import numpy as np
import matplotlib.pyplot as plt

from qgis.core import *
from qgis.gui import *
import os
import stgeotk as stg


def has_field(layer, field_name):
    return layer.fields().indexFromName(field_name) != -1


class StereonetPlugin:
    '''
    Code for the main plugin
    Will init the user interface

    '''

    def __init__(self, iface):
        self.iface = iface
        self.set_default_options()


    def initGui(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        line_icon = QIcon(os.path.join(str(dir_path), "line_icon.ico"))
        self.line_action = QAction(line_icon, u"Plot linear features", self.iface.mainWindow())
        self.line_action.triggered.connect(self.plot_lines)
        self.iface.addToolBarIcon(self.line_action)

        plane_icon = QIcon(os.path.join(str(dir_path), "plane_icon.ico"))
        self.plane_action = QAction(plane_icon, u"Plot planar features", self.iface.mainWindow())
        self.plane_action.triggered.connect(self.plot_planes)
        self.iface.addToolBarIcon(self.plane_action)



    def unload(self):
        self.iface.removeToolBarIcon(self.line_action)
        del self.line_action

        self.iface.removeToolBarIcon(self.plane_action)
        del self.plane_action


    def set_default_options(self):
        self.options = {}
        self.options["strike_field_name"] = "Strike"
        self.options["dip_field_name"] = "Dip"
        self.options["trend_field_name"] = "Trend"


    def plot_lines(self):
        layers = self.iface.layerTreeView().selectedLayers()
        trend = []
        plunge = []
        trd, plg = "Trend", "Plunge"

        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                # trend and plunge
                if has_field(layer, trd) and has_field(layer, plg):
                    it = layer.selectedFeatures()
                    for feature in it:
                        trend.append(feature[trd])
                        plunge.append(feature[plg])
            else:
                continue

        # generate lineation plot
        stereonet = stg.Stereonet()
        dataset = stg.LineData()
        dataset.load_data(np.array([trend, plunge], dtype=np.double).T)
        line_plot = stg.LinePlot(stereonet, dataset, marker = '+')
        stereonet.append_plot(line_plot)
        stereonet.generate_plots()


    def plot_planes(self):
        layers = self.iface.layerTreeView().selectedLayers()
        strikes= []
        dips  = []
        stk, dip = "Strike", "Dip"

        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                # trend and plunge
                if has_field(layer, stk) and has_field(layer, dip):
                    it = layer.selectedFeatures()
                    for feature in it:
                        strikes.append(feature[stk])
                        dips.append(feature[dip])
            else:
                continue

        # generate foliation plot
        stereonet = stg.Stereonet()
        dataset = stg.PlaneData()
        dataset.load_data(np.array([strikes, dips], dtype=np.double).T)
        plane_plot = stg.PlanePlot(stereonet, dataset)
        stereonet.append_plot(plane_plot)
        stereonet.generate_plots()
