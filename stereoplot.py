from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

import numpy as np

from qgis.core import QgsMapLayer, QgsMessageLog
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt import QtWidgets 

import os
import stgeotk as stg


def has_field(layer, field_name):
    return layer.fields().indexFromName(field_name) != -1


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "settings_dialog.ui"))

class SettingsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent = None):
        """
        -----------
        Constructor
        -----------
        setup settings dialogue
        """
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)


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

        settings_icon = QIcon(os.path.join(str(dir_path),"settings.ico"))
        self.settings_action = QAction(settings_icon, u"Stereonet settings", self.iface.mainWindow())
        self.settings_action.triggered.connect(self.set_options)
        self.iface.addToolBarIcon(self.settings_action)


    def unload(self):
        self.iface.removeToolBarIcon(self.line_action)
        del self.line_action

        self.iface.removeToolBarIcon(self.plane_action)
        del self.plane_action

        self.iface.removeToolBarIcon(self.settings_action)
        del self.settings_action
        


    def plot_mean_plane(self, poles_to_plane, stereonet):
        poles_to_plane = stg.mean_vector(poles_to_plane)
        stereonet.append_plot()


    def set_default_options(self):
        self.options = {}
        self.options["strike_field_name"] = "Strike"
        self.options["dip_field_name"] = "Dip"
        self.options["trend_field_name"] = "Trend"
        self.options["plunge_field_name"] = "Plunge"
        self.options["plot_contours"] = True
        self.options["plot_mean_plane"] = True


    def plot_lines(self):
        layers = self.iface.layerTreeView().selectedLayers()
        data = []
        trd, plg = self.options["trend_field_name"], self.options["plunge_field_name"]
        stk, dip = self.options["strike_field_name"], self.options["dip_field_name"]

        has_plane_data = False

        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:

                # trend and plunge
                if has_field(layer, trd) and has_field(layer, plg):
                    it = layer.selectedFeatures()
                    for feature in it:
                        data.append([feature[trd], feature[plg]])

                # strike and dip
                if has_field (layer, stk) and has_field(layer, dip):
                    it =layer.selectedFeatures()
                    for feature in it:
                        data.append(stg.pole_to_plane([feature[stk], feature[dip]]))
                    has_plane_data = True

            else: # continue to the next layer
                continue

        # nothing to do for empty dataset
        if not data:
            return 

        # generate lineation plot
        stereonet = stg.Stereonet()
        dataset = stg.LineData()
        dataset.load_data(np.array(data, dtype=np.double))
        line_plot = stg.LinePlot(stereonet, dataset, marker = '.', s=6)


        # generate average plane
        if has_plane_data and self.options["plot_mean_plane"]:
            avg_pole3, _ = dataset.eigen()
            avg_pole = stg.cartesian_to_line(avg_pole3[2])
            avg_plane_data = stg.PlaneData()
            avg_plane_data.load_data(stg.plane_from_pole(avg_pole), "Average plane")
            avg_plane_plot = stg.PlanePlot(stereonet, avg_plane_data)
            stereonet.append_plot(avg_plane_plot)

        # generate contour plot if requested
        if self.options["plot_contours"]:
            contour_data = stg.ContourData(dataset,
                    counting_method ="fisher",
                    auto_k_optimization=True)
            contour_plot = stg.ContourPlot(stereonet, contour_data, 
                    alpha = 0.9, lim = [0.0, 20.0])
            
            stereonet.append_plot(contour_plot)
            #  stereonet.color_axes[contour_plot][1].clim(0.0, 30.0)

        # generate plots
        stereonet.append_plot(line_plot)
        stereonet.generate_plots()


    def plot_planes(self):
        layers = self.iface.layerTreeView().selectedLayers()
        data = []
        stk, dip = self.options["strike_field_name"], self.options["dip_field_name"]

        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                # trend and plunge
                if has_field(layer, stk) and has_field(layer, dip):
                    it = layer.selectedFeatures()
                    for feature in it:
                        data.append([feature[stk], feature[dip]])
            else:
                continue

        # nothing to do for empty dataset
        if not data:
            return 

        # generate foliation plot
        stereonet = stg.Stereonet()
        dataset = stg.PlaneData()
        dataset.load_data(np.array(data, dtype=np.double))
        plane_plot = stg.PlanePlot(stereonet, dataset)
        stereonet.append_plot(plane_plot)
        stereonet.generate_plots()


    def set_options(self):
        """
        Generate a dialog to set the options
        """
        self.settings_dialog = SettingsDialog()
        self.settings_dialog.show()
        result = self.settings_dialog.exec_()


    #  def add_action(
        #  self,
        #  icon_path,
        #  text,
        #  callback,
        #  enabled_flag=True,
        #  add_to_menu=True,
        #  add_to_toolbar=True,
        #  status_tip=None,
        #  whats_this=None,
        #  parent=None):
        #  """Add a toolbar icon to the toolbar.
#
        #  :param icon_path: Path to the icon for this action. Can be a resource
            #  path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        #  :type icon_path: str
#
        #  :param text: Text that should be shown in menu items for this action.
        #  :type text: str
#
        #  :param callback: Function to be called when the action is triggered.
        #  :type callback: function
#
        #  :param enabled_flag: A flag indicating if the action should be enabled
            #  by default. Defaults to True.
        #  :type enabled_flag: bool
#
        #  :param add_to_menu: Flag indicating whether the action should also
            #  be added to the menu. Defaults to True.
        #  :type add_to_menu: bool
#
        #  :param add_to_toolbar: Flag indicating whether the action should also
            #  be added to the toolbar. Defaults to True.
        #  :type add_to_toolbar: bool
#
        #  :param status_tip: Optional text to show in a popup when mouse pointer
            #  hovers over the action.
        #  :type status_tip: str
#
        #  :param parent: Parent widget for the new action. Defaults None.
        #  :type parent: QWidget
#
        #  :param whats_this: Optional text to show in the status bar when the
            #  mouse pointer hovers over the action.
#
        #  :returns: The action that was created. Note that the action is also
            #  added to self.actions list.
        #  :rtype: QAction
        #  """
#
        #  icon = QIcon(icon_path)
        #  action = QAction(icon, text, parent)
        #  action.triggered.connect(callback)
        #  action.setEnabled(enabled_flag)
#
        #  if status_tip is not None:
            #  action.setStatusTip(status_tip)
#
        #  if whats_this is not None:
            #  action.setWhatsThis(whats_this)
#
        #  if add_to_toolbar:
            #  self.toolbar.addAction(action)
#
        #  if add_to_menu:
            #  self.iface.addPluginToMenu(self.menu, action)
#
        #  self.actions.append(action)
        #  return action
#
            #
#
