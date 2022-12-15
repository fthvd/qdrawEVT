# -*- coding: utf-8 -*-

# QDraw: plugin that makes drawing easier
# Author: Jérémy Kalsron
#         jeremy.kalsron@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from builtins import str

from qgis.PyQt.QtWidgets import QWidget, QPushButton, QSlider, QDesktopWidget,\
    QLabel, QColorDialog, QVBoxLayout, QFontDialog, QMessageBox

from qgis.PyQt.QtGui import QColor, QFont

from qgis.PyQt.QtCore import Qt, QCoreApplication, pyqtSignal, QVariant

from qgis.core import QgsSettings, QgsProject, QgsVectorLayer, QgsVectorFileWriter,\
    QgsWkbTypes, QgsField, QgsFields, QgsLayerTree, QgsApplication

from qgis.utils import iface

import os, unicodedata

from . import resources


class QdrawSettings(QWidget):
    """Window used to change settings (transparency/color/event layers/layers path)"""
    settingsChanged = pyqtSignal()

    def __init__(self):
        QWidget.__init__(self)

        self.setWindowTitle(self.tr('QdrawEVT - Settings'))
        self.setFixedSize(400, 180)
        self.center()

        # default color
        #self.color = QColor(60, 151, 255, 255)
        #self.font = QFont('arial', 12)
        #self.colorFont = QColor('black')
        self.restore_settings()

        self.sld_opacity = QSlider(Qt.Horizontal, self)
        self.sld_opacity.setRange(0, 255)
        self.sld_opacity.setValue(255)
        self.sld_opacity.tracking = True
        self.sld_opacity.valueChanged.connect(self.handler_opacitySliderValue)
        self.lbl_opacity = QLabel(self.tr('Opacity') + ': 100%', self)

        self.dlg_color = QColorDialog(self)
        self.btn_chColor = QPushButton(self.tr('Change the drawing color'), self)
        self.btn_chColor.clicked.connect(self.handler_chColor)
        
        self.dlg_font = QFontDialog(self)
        self.btn_chFont = QPushButton(self.tr('Change text font'), self)
        self.btn_chFont.clicked.connect(self.handler_chFont)
        
        self.dlg_colorFont = QColorDialog(self)
        self.btn_chColorFont = QPushButton(self.tr('Change text color'), self)
        self.btn_chColorFont.clicked.connect(self.handler_chColorFont)

        self.btn_createLayers = QPushButton(self.tr('Create the group and the event layers'), self)
        self.btn_createLayers.clicked.connect(self.handler_createLayers)

        vbox = QVBoxLayout()
        vbox.addWidget(self.lbl_opacity)
        vbox.addWidget(self.sld_opacity)
        vbox.addWidget(self.btn_chColor)
        vbox.addWidget(self.btn_chFont)
        vbox.addWidget(self.btn_chColorFont)
        vbox.addWidget(self.btn_createLayers)
        self.setLayout(vbox)

        # Désactivation du bouton si couche déjà présente
        # if os.path.isfile("Evenements/POLYGONE_EVENEMENT.shp") or os.path.isfile(
        #         "Evenements/LIGNE_EVENEMENT.shp") or os.path.isfile("Evenements/POINT_EVENEMENT.shp"):
        #     print('Couches déjà créées')
        #     # QMessageBox.warning(
        #     #     self.iface.mainWindow(),
        #     #     self.tr("Commande inutile : "), self.tr("Les couches sont déja présentes."))
        #     btn_createLayers.setEnabled(False)
        #     self.close()

    def tr(self, message):
        return QCoreApplication.translate('QdrawEVT', message)

    def handler_opacitySliderValue(self, val):
        self.color.setAlpha(val)
        self.lbl_opacity.setText(
            self.tr('Opacity')+': '+str(int((float(val) / 255) * 100))+'%')
        self.save_settings()
        self.settingsChanged.emit()

    def handler_chColor(self):
        color = self.dlg_color.getColor(self.color)
        if color.isValid():
            color.setAlpha(self.color.alpha())
            self.color = color
            self.save_settings()
            self.settingsChanged.emit()
            self.close()

    def getColor(self):
        return self.color
        
    def getFont(self):
        return self.font
        
    def handler_chFont(self):
        font = self.dlg_font.getFont(self.font)[0]
        self.font = font
        self.save_settings()
        self.settingsChanged.emit()
        self.close()

    def handler_chColorFont(self):
        color = self.dlg_color.getColor(self.colorFont)
        if color.isValid():
            color.setAlpha(self.color.alpha())
            self.colorFont = color
            self.save_settings()
            self.settingsChanged.emit()
            self.close()
            
    def handler_createLayers(self):
        self.iface = iface
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        nameproj = project.fileName()
        evt = None
        groupevt = None
        for group in root.children():
            test = ''.join(
                x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test == 'EVENEMENTS':
                evt = True
                groupevt = group
                if os.path.isfile("Evenements/POLYGONE_EVENEMENT.shp") or os.path.isfile("Evenements/LIGNE_EVENEMENT.shp") or os.path.isfile("Evenements/POINT_EVENEMENT.shp"):
                    print('Couches déjà créées')
                    QMessageBox.warning(
                        self.iface.mainWindow(),
                        self.tr("Commande inutile : "), self.tr("Les couches sont déja présentes."))
                    self.btn_createLayers.setEnabled(False)
                    # self.close()
                    return
        if not evt:
            if nameproj != '':
                groupevt = root.insertGroup(0, 'Evenements')
            else:
                print('Projet non enregistré')
                self.btn_createLayers.setEnabled(False)
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    self.tr("Creation of event shapefile: "), self.tr("Possible only in a saved project. The layers will thus be created in an events sub-folder of the folder containing the project."))
                self.close()
                return

        # Création des couches et affichage dans l'arborescence, groupe évènements
        crs = QgsProject.instance().crs()
        transform_context = QgsProject.instance().transformContext()
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = "ESRI Shapefile"
        save_options.fileEncoding = "UTF-8"

        polylayer_fields = QgsFields()
        polylayer_fields.append(QgsField('libelle', QVariant.String))
        polylayer_fields.append(QgsField('date', QVariant.String))
        polylayer_fields.append(QgsField('h_creation', QVariant.String))
        polylayer_fields.append(QgsField('source', QVariant.String))
        polylayer_fields.append(QgsField('h_constat', QVariant.String))
        polylayer_fields.append(QgsField('remarques', QVariant.String))
        polylayer_fields.append(QgsField('surface', QVariant.Int))
        polylayer_fields.append(QgsField('utilisatr', QVariant.String))

        lnglayer_fields = QgsFields()
        lnglayer_fields.append(QgsField('libelle', QVariant.String))
        lnglayer_fields.append(QgsField('date', QVariant.String))
        lnglayer_fields.append(QgsField('h_creation', QVariant.String))
        lnglayer_fields.append(QgsField('source', QVariant.String))
        lnglayer_fields.append(QgsField('h_constat', QVariant.String))
        lnglayer_fields.append(QgsField('remarques', QVariant.String))
        lnglayer_fields.append(QgsField('longueur', QVariant.Int))
        lnglayer_fields.append(QgsField('utilisatr', QVariant.String))

        ptlayer_fields = QgsFields()
        ptlayer_fields.append(QgsField('libelle', QVariant.String)),
        ptlayer_fields.append(QgsField('date', QVariant.String)),
        ptlayer_fields.append(QgsField('h_creation', QVariant.String)),
        ptlayer_fields.append(QgsField('source', QVariant.String)),
        ptlayer_fields.append(QgsField('h_constat', QVariant.String)),
        ptlayer_fields.append(QgsField('remarques', QVariant.String)),
        ptlayer_fields.append(QgsField('x_gps', QVariant.Double, 'double', 10, 6)),
        ptlayer_fields.append(QgsField('y_gps', QVariant.Double, 'double', 10, 6)),
        ptlayer_fields.append(QgsField('utilisatr', QVariant.String))

        # qmlpath = QgsApplication.qgisSettingsDirPath() + 'qdrawEVT/qml/'
        qmlpath = ':/plugins/qdrawEVT/resources/'
        EVTpath = project.homePath()
        os.makedirs(EVTpath + "/Evenements", exist_ok=True)
        lstlayerEVT = [(EVTpath + "/Evenements/POLYGONE_EVENEMENT.shp", polylayer_fields, QgsWkbTypes.MultiPolygon, qmlpath + 'POLYGONE_EVENEMENT.qml'), (EVTpath + "/Evenements/LIGNE_EVENEMENT.shp", lnglayer_fields, QgsWkbTypes.MultiLineString,  qmlpath + 'LIGNE_EVENEMENT.qml'), (EVTpath + "/Evenements/POINT_EVENEMENT.shp", ptlayer_fields, QgsWkbTypes.MultiPoint,  qmlpath + 'POINT_EVENEMENT.qml')]
        print(project.homePath())
        for layer in lstlayerEVT:
            writer = QgsVectorFileWriter.create(
                layer[0],
                layer[1],
                layer[2],
                crs,
                transform_context,
                save_options
            )
            lyr = self.iface.addVectorLayer(layer[0], '', 'ogr')
            pr = lyr.dataProvider()
            lyr.updateFields()
            lyr.loadNamedStyle(layer[3])
            myptlayer = root.findLayer(lyr.id())
            myptlayerclone = myptlayer.clone()
            parent = myptlayer.parent()
            groupevt.insertChildNode(0, myptlayerclone)
            parent.removeChildNode(myptlayer)
            lyr.triggerRepaint()
            lyr.commitChanges()

            if writer.hasError() != QgsVectorFileWriter.NoError:
                print(self.tr("Error when creating shapefile: "), writer.errorMessage())
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    self.tr("Error when creating shapefile ") + lyr.name() + " : ", writer.errorMessage())
                return
            del writer
        root = project.layerTreeRoot()
        group = root.children()
        for n in group:
            test = ''.join(
                x for x in unicodedata.normalize('NFKD', n.name()) if
                unicodedata.category(x)[0] == 'L').upper()
            if test == 'EVENEMENTS':
                n.setExpanded(True)
            else:
                n.setExpanded(False)
        self.close()

    def handler_convertEventLayers(self):
        self.close()

    def getColorFont(self):
        return self.colorFont

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) / 2,
                  (screen.height() - size.height()) / 2)

    def verifEVT(self):
        self.iface = iface
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        nameproj = project.fileName()
        evt = None
        groupevt = None
        for group in root.children():
            test = ''.join(
                x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test == 'EVENEMENTS':
                evt = True
                groupevt = group
                if os.path.isfile("Evenements/POLYGONE_EVENEMENT.shp") or os.path.isfile("Evenements/LIGNE_EVENEMENT.shp") or os.path.isfile("Evenements/POINT_EVENEMENT.shp"):
                    print('Couches déjà créées')
                    # QMessageBox.warning(
                    #     self.iface.mainWindow(),
                    #     self.tr("Commande inutile : "), self.tr("Les couches sont déja présentes."))
                    self.btn_createLayers.setEnabled(False)
                    return
        if not evt:
            if nameproj != '':
                print('Couches EVT absentes du projet')
                self.btn_createLayers.setEnabled(True)
            else:
                print('Projet non enregistré')
                self.btn_createLayers.setEnabled(True)
                # QMessageBox.warning(
                #     self.iface.mainWindow(),
                #     self.tr("Creation of event shapefile: "), self.tr("Possible only in a saved project. The layers will thus be created in an events sub-folder of the folder containing the project."))

    def showEvent(self, o):
        print('show passé')
        self.verifEVT()
        o.accept()

    def closeEvent(self, e):
        self.clear()
        e.accept()

    def clear(self):
        return
        
    def save_settings(self):
        settings = QgsSettings()
        settings.beginGroup("/Qdraw")
        settings.setValue("font", self.font.family())
        settings.setValue("fontSize", self.font.pointSize())
        settings.setValue("colorFontRed", self.colorFont.red())
        settings.setValue("colorFontgreen", self.colorFont.green())
        settings.setValue("colorFontblue", self.colorFont.blue())
        settings.setValue("colorFontAlpha", self.colorFont.alpha())
        settings.setValue("colorRed", self.color.red())
        settings.setValue("colorGreen", self.color.green())
        settings.setValue("colorBlue", self.color.blue())
        settings.setValue("colorAlpha", self.color.alpha())
        settings.endGroup()
        
    def restore_settings(self):
        settings = QgsSettings()
        settings.beginGroup("/Qdraw")
        self.font=QFont(settings.value("font", 'arial'), int(settings.value("fontSize",12)))
        self.colorFont=QColor(int(settings.value("colorFontRed", 0)), int(settings.value("colorFontGreen", 0)), int(settings.value("colorFontBlue", 0)), int(settings.value("colorFontAlpha", 255)))
        self.color = QColor(int(settings.value("colorRed", 60)), int(settings.value("colorGreen", 151)), int(settings.value("colorBlue", 255)), int(settings.value("colorAlpha", 255)))
        
        
