import os
import numpy as np
import stgeotk as stg

from qgis.core import QgsMapLayer, QgsMessageLog
from qgis.PyQt import uic 
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QAction, QDialog, QDialogButtonBox, QButtonGroup


def has_field(layer, field_name):
    return layer.fields().indexFromName(field_name) != -1

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "settings_dialog.ui"))


class SettingsDialog(QDialog, FORM_CLASS):
    def __init__(self, options, iface, parent = None):
        """
        -----------
        Constructor
        -----------
        setup settings dialogue
        """
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)

        # LINES defaults
        index = self.marker_combobox.findText(options["marker"])
        self.marker_combobox.setCurrentIndex(index)
        self.marker_size_spinbox.setValue(options["marker_size"])
        self.marker_colorbutton.setColor(QColor(options["marker_color"]))

        self.marker_group = QButtonGroup(self)
        self.marker_group.addButton(self.color_by_single_color_radio)
        self.marker_group.addButton(self.color_by_data_field_radio)
        self.marker_group.setExclusive(True)
        self.marker_group.buttonClicked.connect(self.activate_marker_color)

        use_single_color = not bool(options["marker_color_field"])
        self.color_by_single_color_radio.setChecked(use_single_color)
        self.color_by_data_field_radio.setChecked(not use_single_color)
        self.activate_marker_color()

        self.marker_color_field.setLayer(iface.layerTreeView().currentLayer())
        self.marker_color_field.setAllowEmptyFieldName(False)
        self.marker_color_field.setField(options["marker_color_field"])

        index = self.marker_colormap_combobox.findText(options["marker_cmap"])
        self.marker_colormap_combobox.setCurrentIndex(index)
        if options["marker_cmap_limits"] is not None:
            self.marker_lowlimit_dspinbox.setValue(options["marker_cmap_limits"][0])
            self.marker_upplimit_dspinbox.setValue(options["marker_cmap_limits"][1])
        else:
            self.marker_lowlimit_dspinbox.setValue(0.0)
            self.marker_upplimit_dspinbox.setValue(0.0)

        self.marker_cmap_center_checkbox.setChecked(options["marker_cmap_center"] is not None)
        self.marker_cmap_center_checkbox.clicked.connect(self.activate_marker_cmap_center)
        if options["marker_cmap_center"] is not None:
            self.marker_cmap_center_dspinbox.setValue(options["marker_cmap_center"])
        self.activate_marker_cmap_center()

        # CONTOUR defaults
        self.contour_checkbox.setChecked(options["plot_contours"])
        self.activate_contour()
        self.contour_checkbox.stateChanged.connect(self.activate_contour)
        index = self.contour_cmap_combobox.findText(options["contour_cmap"])
        self.contour_cmap_combobox.setCurrentIndex(index)
        if options["contour_limits"] is not None:
            self.contour_lowlimit_dspinbox.setValue(options["contour_limits"][0])
            self.contour_upplimit_dspinbox.setValue(options["contour_limits"][1])
        else:
            self.contour_lowlimit_dspinbox.setValue(0.0)
            self.contour_upplimit_dspinbox.setValue(0.0)


    def activate_contour(self):
        state = self.contour_checkbox.isChecked()
        self.contour_colors_label.setEnabled(state)
        self.contour_limits_label.setEnabled(state)
        self.lower_label.setEnabled(state)
        self.upper_label.setEnabled(state)
        self.contour_cmap_combobox.setEnabled(state)
        self.contour_lowlimit_dspinbox.setEnabled(state)
        self.contour_upplimit_dspinbox.setEnabled(state)


    def activate_marker_color(self):
        single_color = self.color_by_single_color_radio.isChecked()
        self.marker_colorbutton.setEnabled(single_color)
        self.marker_color_field.setEnabled(not single_color)
        self.marker_cmap_center_checkbox.setEnabled(not single_color)
        self.marker_colormap_label.setEnabled(not single_color)
        self.marker_colormap_combobox.setEnabled(not single_color)
        self.marker_lower_label.setEnabled(not single_color)
        self.marker_upper_label.setEnabled(not single_color)
        self.marker_upplimit_dspinbox.setEnabled(not single_color)
        self.marker_lowlimit_dspinbox.setEnabled(not single_color)

    def activate_marker_cmap_center(self):
        self.marker_cmap_center_dspinbox.setEnabled(self.marker_cmap_center_checkbox.isChecked())


class StereonetPlugin:
    """
    Code for the main plugin
    Will init the user interface
    """

    def __init__(self, iface):
        self.iface = iface
        self.set_default_options()
        self.settings_dialog = None
        self.stereonet = None


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

        settings_icon = QIcon(os.path.join(str(dir_path), "settings.ico"))
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
        self.options["strike_field"] = "Strike"
        self.options["dip_field"] = "Dip"
        self.options["trend_field"] = "Trend"
        self.options["plunge_field"] = "Plunge"
        self.options["plot_contours"] = False
        self.options["plot_mean_plane"] = True
        self.options["contour_limits"] = None
        self.options["contour_cmap"] = "Oranges"
        self.options["marker"] = "+"
        self.options["marker_cmap"] = "RdYlGn"
        self.options["marker_cmap_limits"] = None
        self.options["marker_color"] = "#000000"
        self.options["marker_size"] = 6
        self.options["marker_cmap_center"] = None
        self.options["marker_color_field"] = ""


    def plot_lines(self):
        #  layers = self.iface.layerTreeView().selectedLayers()
        data = []
        color_data = []
        trd, plg = self.options["trend_field"], self.options["plunge_field"]
        stk, dip = self.options["strike_field"], self.options["dip_field"]
        clr = self.options["marker_color_field"]
        has_plane_data = False

        layer = self.iface.layerTreeView().currentLayer()
        if layer.type() != QgsMapLayer.VectorLayer:
            return

        # trend and plunge
        if has_field(layer, trd) and has_field(layer, plg):
            it = layer.selectedFeatures()
            for feature in it:
                data.append([feature[trd], feature[plg]])

        # strike and dip
        if has_field(layer, stk) and has_field(layer, dip):
            it =layer.selectedFeatures()
            for feature in it:
                data.append(stg.pole_to_plane([feature[stk], feature[dip]]))
            has_plane_data = True

        # nothing to do for empty dataset
        if not data:
            return

        # color data
        if clr and has_field(layer, clr):
            it = layer.selectedFeatures()
            for feature in it:
                color_data.append(feature[clr])

        # generate lineation plot
        self.stereonet = stg.Stereonet()
        dataset = stg.LineData()

        if color_data:
            dataset.load_data(np.array(data, dtype=np.double), layer.name(),
                    np.array(color_data, dtype=np.double), clr)
        else:
            dataset.load_data(np.array(data, dtype=np.double), layer.name())

        # marker color will be ignored if color axis data is provided
        line_plot = stg.LinePlot(self.stereonet, dataset,
                marker = self.options["marker"],
                s=self.options["marker_size"],
                color = self.options["marker_color"],
                cmap = self.options["marker_cmap"],
                cmap_center = self.options["marker_cmap_center"],
                linewidth = 0.8, edgecolors = "black",
                cmap_limits = self.options["marker_cmap_limits"])

        # generate average plane
        if has_plane_data and self.options["plot_mean_plane"]:
            avg_pole3, _ = dataset.eigen()
            avg_pole = stg.cartesian_to_line(avg_pole3[2])
            avg_plane_data = stg.PlaneData()

            # print the plane from pole
            avg_plane =  stg.plane_from_pole(avg_pole)
            print(avg_plane)

            avg_plane_data.load_data(stg.plane_from_pole(avg_pole), "Average plane")
            avg_plane_plot = stg.PlanePlot(self.stereonet, avg_plane_data)
            self.stereonet.append_plot(avg_plane_plot)

        # generate contour plot if requested
        if self.options["plot_contours"]:
            contour_data = stg.ContourData(dataset,
                    counting_method ="fisher",
                    auto_k_optimization=True)
            contour_plot = stg.ContourPlot(self.stereonet, 
                    contour_data, alpha = 0.9, cmap = self.options["contour_cmap"],
                    lim = self.options["contour_limits"])

            self.stereonet.append_plot(contour_plot)

        # generate plots
        self.stereonet.append_plot(line_plot)
        self.stereonet.generate_plots()


    def plot_planes(self):
        layers = self.iface.layerTreeView().selectedLayers()
        data = []
        stk, dip = self.options["strike_field"], self.options["dip_field"]

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
        self.stereonet = stg.Stereonet()
        dataset = stg.PlaneData()
        dataset.load_data(np.array(data, dtype=np.double))
        plane_plot = stg.PlanePlot(self.stereonet, dataset)
        self.stereonet.append_plot(plane_plot)
        self.stereonet.generate_plots()


    def set_options(self):
        """
        Generate a dialog to set the options
        """
        self.settings_dialog = SettingsDialog(self.options, self.iface)
        self.settings_dialog.button_box.clicked.connect(self.button_click)
        self.settings_dialog.show()
        result = self.settings_dialog.exec_()

    def button_click(self, button):
        dlg = self.settings_dialog
        sb = dlg.button_box.standardButton(button)

        if sb == QDialogButtonBox.Save:
            self.save_settings()
            dlg.accept()
        else:
            dlg.reject()


    def save_settings(self):
        dlg = self.settings_dialog
        self.options["plot_contours"] = dlg.contour_checkbox.isChecked()
        self.options["contour_cmap"] = dlg.contour_cmap_combobox.currentText()

        if dlg.contour_upplimit_dspinbox.value() > 0.0:
            self.options["contour_limits"] = \
                [dlg.contour_lowlimit_dspinbox.value(), dlg.contour_upplimit_dspinbox.value()]
        else:
            self.options["contour_limits"] = None

        if dlg.marker_upplimit_dspinbox.value() > 0.0:
            self.options["marker_cmap_limits"] = \
                [dlg.marker_lowlimit_dspinbox.value(), dlg.marker_upplimit_dspinbox.value()]
        else:
            self.options["marker_cmap_limits"] = None

        self.options["marker"] = dlg.marker_combobox.currentText()
        self.options["marker_size"] = dlg.marker_size_spinbox.value()
        self.options["marker_color"] = dlg.marker_colorbutton.color().name()

        if dlg.marker_color_by_data_field_radio.isChecked():
            self.options["marker_color_field"] = dlg.marker_color_field.currentField()
        else:
            self.options["marker_color_field"] = ""
        

        if dlg.marker_cmap_center_checkbox.isChecked():
            self.options["marker_cmap_center"] = dlg.marker_cmap_center_dspinbox.value()
        else:
            self.options["marker_cmap_center"] = None

        self.options["marker_cmap"] = dlg.marker_colormap_combobox.currentText()

        print(self.options)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

