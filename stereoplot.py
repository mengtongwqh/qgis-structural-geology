import os
import numpy as np
import stgeotk as stg

from qgis.core import NULL, QgsMapLayer, QgsMessageLog, Qgis, QgsVectorLayer
from qgis.PyQt import uic

# from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.gui import QgsFieldComboBox, QgsMessageBar
from qgis.PyQt.QtWidgets import QAction, QDialog, QDialogButtonBox, QButtonGroup


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "settings_dialog.ui")
)


def has_field(layer, field_name):
    return layer.fields().indexFromName(field_name) != -1


def info(msg):
    QgsMessageLog.logMessage(msg, "qgis-structural-geology", level=Qgis.Info)


class SettingsDialog(QDialog, FORM_CLASS):

    def __init__(self, options: dict, iface, parent=None):
        """
        Setup the SettingsDialog according to the options provided
        """
        self.iface = iface  # alias the iface
        self.options = options

        # setup parent class
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)

        # GENERAL tab
        self.init_field_combobox(self.trend_field, options["trend_field"])
        self.init_field_combobox(self.plunge_field, options["plunge_field"])
        self.init_field_combobox(self.dip_dir_field, options["dip_dir_field"])
        self.init_field_combobox(self.dip_angle_field,
                                 options["dip_angle_field"])
        self.init_field_combobox(self.strike_field, options["strike_field"])

        self.planar_data_group = QButtonGroup(self)
        self.planar_data_group.addButton(self.use_dip_dir_radio)
        self.planar_data_group.addButton(self.use_strike_radio)
        self.planar_data_group.setExclusive(True)
        self.planar_data_group.buttonClicked.connect(
            self.toggle_planar_data_format)
        self.use_dip_dir_radio.setChecked(options["use_dip_dir"])
        self.use_strike_radio.setChecked(not options["use_dip_dir"])
        self.toggle_planar_data_format()

        self.plot_mean_plane_checkbox.setChecked(options["plot_mean_plane"])
        self.plot_intersection_point_checkbox.setChecked(
            options["plot_intersection_point"])

        # MARKER tab
        index = self.marker_combobox.findText(options["marker"])
        self.marker_combobox.setCurrentIndex(index)
        self.marker_size_spinbox.setValue(options["marker_size"])
        self.marker_colorbutton.setColor(QColor(options["marker_color"]))

        self.marker_group = QButtonGroup(self)
        self.marker_group.addButton(self.color_by_single_color_radio)
        self.marker_group.addButton(self.color_by_data_field_radio)
        self.marker_group.setExclusive(True)
        self.marker_group.buttonClicked.connect(self.toggle_marker_color)

        use_single_color = not bool(options["marker_color_field"])
        self.color_by_single_color_radio.setChecked(use_single_color)
        self.color_by_data_field_radio.setChecked(not use_single_color)
        self.toggle_marker_color()

        self.init_field_combobox(
            self.marker_color_field, options["marker_color_field"])

        index = self.marker_colormap_combobox.findText(options["marker_cmap"])
        self.marker_colormap_combobox.setCurrentIndex(index)
        if options["marker_cmap_limits"] is not None:
            self.marker_lowlimit_dspinbox.setValue(
                options["marker_cmap_limits"][0])
            self.marker_upplimit_dspinbox.setValue(
                options["marker_cmap_limits"][1])
        else:
            self.marker_lowlimit_dspinbox.setValue(0.0)
            self.marker_upplimit_dspinbox.setValue(0.0)

        self.marker_cmap_center_checkbox.setChecked(
            options["marker_cmap_center"] is not None
        )
        self.marker_cmap_center_checkbox.clicked.connect(
            self.toggle_marker_cmap_center)
        if options["marker_cmap_center"] is not None:
            self.marker_cmap_center_dspinbox.setValue(
                options["marker_cmap_center"])
        self.toggle_marker_cmap_center()

        # CONTOUR tab
        self.contour_checkbox.setChecked(options["plot_contours"])
        self.toggle_contour()
        self.contour_checkbox.stateChanged.connect(self.toggle_contour)
        index = self.contour_cmap_combobox.findText(options["contour_cmap"])
        self.contour_cmap_combobox.setCurrentIndex(index)
        if options["contour_limits"] is not None:
            self.contour_lowlimit_dspinbox.setValue(
                options["contour_limits"][0])
            self.contour_upplimit_dspinbox.setValue(
                options["contour_limits"][1])
        else:
            self.contour_lowlimit_dspinbox.setValue(0.0)
            self.contour_upplimit_dspinbox.setValue(0.0)

        # ------------------------
        # SAVE or REJECT settings
        # ------------------------
        self.button_box.clicked.connect(self.save_or_reject_settings)

    def init_field_combobox(
        self,
        combobox: QgsFieldComboBox,
        default_fieldname: str = "",
        allow_empty_field: bool = False,
        layer=None,
    ):
        if layer is None:
            layer = self.iface.layerTreeView().currentLayer()
        combobox.setLayer(layer)
        combobox.setAllowEmptyFieldName(allow_empty_field)
        combobox.setField(default_fieldname)

    def toggle_planar_data_format(self):
        use_dip_dir = self.use_dip_dir_radio.isChecked()
        self.dip_dir_field.setEnabled(use_dip_dir)
        self.strike_field.setEnabled(not use_dip_dir)

    def toggle_marker_color(self):
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

    def toggle_marker_cmap_center(self):
        self.marker_cmap_center_dspinbox.setEnabled(
            self.marker_cmap_center_checkbox.isChecked()
        )

    def toggle_contour(self):
        state = self.contour_checkbox.isChecked()
        self.contour_colors_label.setEnabled(state)
        self.contour_limits_label.setEnabled(state)
        self.lower_label.setEnabled(state)
        self.upper_label.setEnabled(state)
        self.contour_cmap_combobox.setEnabled(state)
        self.contour_lowlimit_dspinbox.setEnabled(state)
        self.contour_upplimit_dspinbox.setEnabled(state)

    def save_or_reject_settings(self, button):
        sb = self.button_box.standardButton(button)
        if sb == QDialogButtonBox.Save:
            self.accept()
        else:
            self.reject()

    def accept(self):
        """
        Collect all settings in the SettingsDialog 
        into the options dictionary
        """
        # GENERAL
        self.options["trend_field"] = self.trend_field.currentField()
        self.options["plunge_field"] = self.plunge_field.currentField()
        self.options["dip_dir_field"] = self.dip_dir_field.currentField()
        self.options["strike_field"] = self.strike_field.currentField()
        self.options["dip_angle_field"] = self.dip_angle_field.currentField()
        self.options["use_dip_dir"] = self.use_dip_dir_radio.isChecked()

        self.options["plot_mean_plane"] = self.plot_mean_plane_checkbox.isChecked()
        self.options["plot_intersection_point"] = self.plot_intersection_point_checkbox.isChecked()

        # MARKER
        if self.marker_upplimit_dspinbox.value() > 0.0:
            self.options["marker_cmap_limits"] = [
                self.marker_lowlimit_dspinbox.value(),
                self.marker_upplimit_dspinbox.value(),
            ]
        else:
            self.options["marker_cmap_limits"] = None

        self.options["marker"] = self.marker_combobox.currentText()
        self.options["marker_size"] = self.marker_size_spinbox.value()
        self.options["marker_color"] = self.marker_colorbutton.color().name()

        if self.color_by_data_field_radio.isChecked():
            self.options["marker_color_field"] = self.marker_color_field.currentField()
        else:
            self.options["marker_color_field"] = ""

        if self.marker_cmap_center_checkbox.isChecked():
            self.options[
                "marker_cmap_center"
            ] = self.marker_cmap_center_dspinbox.value()
        else:
            self.options["marker_cmap_center"] = None

        self.options["marker_cmap"] = self.marker_colormap_combobox.currentText()

        # COUTOURS
        self.options["plot_contours"] = self.contour_checkbox.isChecked()
        self.options["contour_cmap"] = self.contour_cmap_combobox.currentText()

        if self.contour_upplimit_dspinbox.value() > 0.0:
            self.options["contour_limits"] = [
                self.contour_lowlimit_dspinbox.value(),
                self.contour_upplimit_dspinbox.value(),
            ]
        else:
            self.options["contour_limits"] = None

        # print current options to message log
        info("Saved settings: \n" + str(self.options))


class StereonetPlugin:
    """
    Code for the main plugin
    Will init the user interface
    """

    def __init__(self, iface):
        self.iface = iface
        self.settings_dialog = None
        self.stereonet = None
        self.actions = []
        self.options = {}
        self.set_default_options()
        self.iface.layerTreeView().currentLayerChanged.connect(self.sniff_layer_fields)

    def initGui(self):
        self.add_action_to_toolbar(
            "line_icon.ico", "plotLines", self.plot_lines, "Plot linear structural features")
        self.add_action_to_toolbar(
            "plane_icon.ico", "plotPlanes", self.plot_planes)
        self.add_action_to_toolbar(
            "pole_to_plane.ico", "plotPolesToPlane", self.plot_poles_to_plane
        )
        self.add_action_to_toolbar(
            "settings.ico", "settings", self.open_settings_dialog)

    def add_action_to_toolbar(
        self, icon_name, object_name, callback, status_tip=None, whats_this=None
    ):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        icon = QIcon(os.path.join(str(dir_path), icon_name))
        action = QAction(icon, object_name, self.iface.mainWindow())
        action.triggered.connect(callback)
        self.iface.addToolBarIcon(action)

        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)

        # append this action to the collection
        self.actions.append(action)
        return action

    def unload(self):
        for action in self.actions:
            self.iface.removeToolBarIcon(action)
        self.actions.clear()

    def set_default_options(self):
        # general group settings
        self.options["strike_field"] = "strike"
        self.options["dip_angle_field"] = "dip_angle"
        self.options["dip_dir_field"] = "dip_dir"
        self.sniff_layer_fields(self.iface.layerTreeView().currentLayer())

        self.options["trend_field"] = "trend"
        self.options["plunge_field"] = "plunge"
        self.options["plot_contours"] = False
        self.options["plot_mean_plane"] = True
        self.options["plot_intersection_point"] = True

        # marker group settings
        self.options["marker"] = "+"
        self.options["marker_cmap"] = "RdYlGn"
        self.options["marker_cmap_limits"] = None
        self.options["marker_color"] = "#000000"
        self.options["marker_size"] = 6
        self.options["marker_cmap_center"] = None
        self.options["marker_color_field"] = ""

        # contour group settings
        self.options["contour_limits"] = None
        self.options["contour_cmap"] = "Oranges"

    def plot_lines(self):
        self.stereonet = stg.Stereonet()

        data = []
        color_data = []
        graph_name = []

        trd_field, plg_field = self.options["trend_field"], self.options["plunge_field"]
        clr = self.options["marker_color_field"]

        layers = self.iface.layerTreeView().selectedLayersRecursive()

        for layer in layers:
            if not isinstance(layer, QgsVectorLayer):
                info(layer.name() + " is not a vector layer. Skipped.")
                continue
            else:
                info(layer.name() + " is included for line plot")
                graph_name.append(layer.name())

            # trend and plunge
            if has_field(layer, trd_field) and has_field(layer, plg_field):
                selected_features = layer.selectedFeatures()
                for feature in selected_features:
                    trd, plg = feature[trd_field], feature[plg_field]
                    if trd != NULL and plg != NULL:
                        data.append([trd, plg])
                        if clr and has_field(layer, clr):
                            if feature[clr] == NULL:
                                raise ValueError("Color data is NULL.")
                            color_data.append(feature[clr])

        # nothing to do for empty dataset
        if not data:
            self.warn(
                "No line data are detected in the dataset. Nothing is plotted.")
            return

        # generate lineation plot
        dataset = stg.LineData()

        if color_data:
            dataset.load_data(
                np.array(data, dtype=np.double),
                str(graph_name),
                np.array(color_data, dtype=np.double),
                clr,
            )
        else:
            dataset.load_data(np.array(data, dtype=np.double), str(graph_name))

        # marker color will be ignored if color axis data is provided
        line_plot = stg.LinePlot(
            self.stereonet,
            dataset,
            marker=self.options["marker"],
            s=self.options["marker_size"],
            color=self.options["marker_color"],
            cmap=self.options["marker_cmap"],
            cmap_center=self.options["marker_cmap_center"],
            linewidth=0.8,
            edgecolors="black",
            cmap_limits=self.options["marker_cmap_limits"],
        )

        # generate contour plot if requested
        if self.options["plot_contours"]:
            contour_data = stg.ContourData(
                dataset, counting_method="fisher", auto_k_optimization=True
            )
            contour_plot = stg.ContourPlot(
                self.stereonet,
                contour_data,
                alpha=0.9,
                cmap=self.options["contour_cmap"],
                lim=self.options["contour_limits"],
            )
            self.stereonet.append_plot(contour_plot)


        # generate bestfit plane
        if self.options["plot_mean_plane"]:
            bestfit_pole = stg.cartesian_to_line(dataset.eigen()[0][0])
            bestfit_plane_data = stg.PlaneData()

            # print the plane from pole
            bestfit_plane = stg.plane_from_pole(bestfit_pole)
            info(
                f"Best-fit plane strike/dip = {bestfit_plane[0]} / {bestfit_plane[1]}")
            bestfit_plane_data.load_data(
                bestfit_plane, dataset.data_legend + " best-fit plane")
            bestfit_plane_plot = stg.PlanePlot(
                self.stereonet, bestfit_plane_data)
            self.stereonet.append_plot(bestfit_plane_plot)


        # generate plots
        self.stereonet.append_plot(line_plot)
        self.stereonet.generate_plots()

    def plot_planes(self):
        """
        Plot big circles of planar structural features.
        If requested, also plot the best intersection point.
        """
        layers = self.iface.layerTreeView().selectedLayersRecursive()
        data = []
        data_normal = []
        graph_name = []

        dip_field = self.options["dip_angle_field"]
        if self.options["use_dip_dir"]:
            direc_field = self.options["dip_dir_field"]
            info("Dataset will be treated in dip-dir/dip-angle format ")
        else:
            direc_field = self.options["strike_field"]
            info("Dataset will be treated in strike/dip format ")

        for layer in layers:
            # skip non-vector layers
            if isinstance(layer, QgsVectorLayer):
                info(layer.name() + " is included for plane plotting.")
                graph_name.append(layer.name())
            else:
                info(layer.name() + " is not a vector layer. Skipped.")
                continue

            # strike and dip
            if has_field(layer, direc_field) and has_field(layer, dip_field):
                selected_features = layer.selectedFeatures()
                for feature in selected_features:
                    stk = feature[direc_field] - 90 * \
                        self.options["use_dip_dir"]
                    dip = feature[dip_field]

                    if stk != NULL and dip != NULL:
                        data.append([stk, dip])
                        data_normal.append(
                            stg.pole_to_plane([stk, dip])
                        )

        # nothing to do for empty dataset
        if not data:
            self.warn(
                "No plane data are detected in the dataset. Nothing is plotted.")
            return

        # generate foliation plot
        self.stereonet = stg.Stereonet()
        dataset = stg.PlaneData()
        dataset.load_data(np.array(data, dtype=np.double), str(graph_name))
        plane_plot = stg.PlanePlot(self.stereonet, dataset)
        dataset_normal = stg.LineData()
        dataset_normal.load_data(data_normal, str(graph_name))

        # generate average intersection
        if self.options["plot_intersection_point"]:
            avg_intersect = stg.LineData()
            avg_intersect.load_data(dataset_normal.eigen()[
                                    0][0], str(graph_name) + " average intersect")
            avg_intersect_plot = stg.LinePlot(
                self.stereonet, avg_intersect, marker="*")
            self.stereonet.append_plot(avg_intersect_plot)

            # report trend/plunge
            avg_trd, avg_plg = stg.cartesian_to_line(avg_intersect.data[0])
            info(
                f"Trend/plunge of the best-fit intersection point: {avg_trd} / {avg_plg}")

        self.stereonet.append_plot(plane_plot)
        self.stereonet.generate_plots()

    def plot_poles_to_plane(self):
        """
        Plot poles to planes of planar structural features 
        If requested, also plot the best-fit big circle to the poles to planes
        """
        layers = self.iface.layerTreeView().selectedLayersRecursive()
        data = []
        color_data = []
        graph_name = []

        dip_field = self.options["dip_angle_field"]
        if self.options["use_dip_dir"]:
            direc_field = self.options["dip_dir_field"]
            info("Dataset will be treated in dip-dir/dip-angle format ")
        else:
            direc_field = self.options["strike_field"]
            info("Dataset will be treated in strike/dip format ")
        clr = self.options["marker_color_field"]

        for layer in layers:
            if isinstance(layer, QgsVectorLayer):
                info(layer.name() + " is included for poles-to-plane plotting.")
                graph_name.append(layer.name())
            else:
                info(layer.name() + " is not a vector layer. Skipped.")
                continue

            # strike and dip
            if has_field(layer, direc_field) and has_field(layer, dip_field):
                selected_features = layer.selectedFeatures()
                for feature in selected_features:
                    stk = feature[direc_field] - 90 * \
                        self.options["use_dip_dir"]
                    dip = feature[dip_field]
                    if stk != NULL and dip != NULL:
                        data.append(stg.pole_to_plane([stk, dip]))
                        if clr and has_field(layer, clr):
                            color_data.append(feature[clr])

        if not data:
            self.warn(
                "No plane data are detected in the dataset. Nothing is plotted")
            return

        # generate poles to plane plot
        self.stereonet = stg.Stereonet()

        dataset = stg.LineData()
        if color_data:
            dataset.load_data(np.array(data, dtype=np.double), str(
                graph_name) + " poles", np.array(color_data, dtype=np.double), clr)
            line_plot = stg.LinePlot(self.stereonet, dataset, marker=self.options["marker"],
                                     s=self.options["marker_size"],
                                     cmap=self.options["marker_cmap"],
                                     cmap_center=self.options["marker_cmap_center"],
                                     linewidth=0.8,
                                     cmap_limits=self.options["marker_cmap_limits"])
        else:
            dataset.load_data(np.array(data, dtype=np.double),
                              str(graph_name) + " poles")
            line_plot = stg.LinePlot(self.stereonet, dataset, marker=self.options["marker"],
                                     s=self.options["marker_size"],
                                     color=self.options["marker_color"],
                                     linewidth=0.8)

        # generate contour plot if requested
        if self.options["plot_contours"]:
            contour_data = stg.ContourData(
                dataset, counting_method="fisher", auto_k_optimization=True
            )
            contour_plot = stg.ContourPlot(
                self.stereonet,
                contour_data,
                alpha=0.9,
                cmap=self.options["contour_cmap"],
                lim=self.options["contour_limits"],
            )
            self.stereonet.append_plot(contour_plot)

        # generate average plane
        if self.options["plot_mean_plane"]:
            avg_plane_pole = stg.cartesian_to_line(dataset.eigen()[0][2])
            avg_plane_data = stg.PlaneData()

            # print the plane from pole
            avg_plane = stg.plane_from_pole(avg_plane_pole)
            info(f"Average plane strike/dip = {avg_plane[0]} / {avg_plane[1]}")
            avg_plane_data.load_data(
                avg_plane, str(graph_name) + " average plane")
            avg_plane_plot = stg.PlanePlot(self.stereonet, avg_plane_data)
            self.stereonet.append_plot(avg_plane_plot)

        self.stereonet.append_plot(line_plot)
        self.stereonet.generate_plots()

    def open_settings_dialog(self):
        """
        Generate a dialog to set the plotting options
        """
        self.settings_dialog = SettingsDialog(self.options, self.iface)
        self.settings_dialog.show()
        self.settings_dialog.exec_()

    def warn(self, msg):
        """
        Print a warning message to the messageBar
        """
        self.iface.messageBar().pushMessage("Warning", msg, level=Qgis.Warning)

    def sniff_layer_fields(self, layer):
        """
        When a new layer is selected,
        try to determine if it is in strike-dip format or
        dip-dir/dip-angle format
        """
        if isinstance(layer, QgsVectorLayer) and has_field(layer, "Strike"):
            self.options["use_dip_dir"] = False
            self.options["strike_field"] = "strike"
            self.options["dip_angle_field"] = "dip"
        else:
            self.options["use_dip_dir"] = True
            self.options["dip_angle_field"] = "dip_angle"
            self.options["dip_dir_field"] = "dip_dir"
