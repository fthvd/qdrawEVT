# -*- coding: utf-8 -*-

# qdrawEVT: plugin that makes drawing easier
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

import os
import random
import unicodedata
from builtins import str

from qgis.PyQt.QtCore import Qt, QCoreApplication, pyqtSignal, QVariant
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import QWidget, QPushButton, QSlider, QDesktopWidget, \
    QLabel, QColorDialog, QVBoxLayout, QFontDialog, QMessageBox
from qgis.core import *
from qgis.core import QgsSettings, QgsProject, QgsVectorLayer, QgsVectorFileWriter, \
    QgsWkbTypes, QgsField, QgsFields, QgsLayerTree, QgsApplication, QgsLayerTreeLayer
from qgis.utils import iface

from . import resources


class QdrawSettings(QWidget):
    """Window used to change settings (transparency/color/event layers/layers path)"""
    settingsChanged = pyqtSignal()

    def __init__(self, form_wgt_libelle):
        QWidget.__init__(self)

        self.form_wgt_libelle = form_wgt_libelle
        self.setWindowTitle(self.tr('QdrawEVT - Settings'))
        self.setFixedSize(400, 180)
        self.center()
        self.keepselect = False

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

    def handler_selectedLayers(self):
        self.iface = iface
        if self.chkbox_selectedlayers.checkState():
            msg = self.tr("The display of the selections will be preserved.")
            self.keepselect = True
        else:
            msg = self.tr("The display of selections will be removed.")
            self.keepselect = False
            # Suppression d'une éventuelle sélection en cours
            root = QgsProject.instance().layerTreeRoot()
            for checked_layers in root.checkedLayers():
                try:
                    checked_layers.removeSelection()
                except:
                    pass
        QMessageBox.information(
            self.iface.mainWindow(),
            self.tr("Fenêtre carte : "), msg)
        self.close()
        # return keepselect

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
        # print('os.path : ' + str(os.path))
        # print('project.path : ' + str(project.homePath()))
        root = project.layerTreeRoot()
        nameproj = project.fileName()
        # os.chdir(project.homePath())
        evtpath = project.homePath()
        qmlpath = ':/plugins/qdrawEVT/resources/'
        evt = None
        groupevt = None

        for group in root.children():
            test = ''.join(
                x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test == 'EVENEMENTS':
                evt = True
                groupevt = group
                # print('os.path : ' + str(os.path))
                # print('project.path : ' + str(project.homePath()))
                if os.path.isfile(evtpath + "Evenements/POLYGONE_EVENEMENT.shp") or os.path.isfile(evtpath + "Evenements/LIGNE_EVENEMENT.shp") or os.path.isfile(evtpath + "Evenements/POINT_EVENEMENT.shp"):
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

        # Préparation de l'ouverture ou de la création des couches et affichage dans l'arborescence, groupe évènements
        crs = QgsProject.instance().crs()
        transform_context = QgsProject.instance().transformContext()
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = "ESRI Shapefile"
        save_options.fileEncoding = "UTF-8"
        lstlayerEVT = []

        if os.path.isfile(evtpath + "/Evenements/POLYGONE_EVENEMENT.shp"):
            vlayer = QgsVectorLayer(evtpath + "/Evenements/POLYGONE_EVENEMENT.shp", "POLYGONE_EVENEMENT", "ogr")
            # print('Chemin :' + evtpath + "Evenements/POLYGONE_EVENEMENT.shp")
            vlayer.loadNamedStyle(qmlpath + 'POLYGONE_EVENEMENT.qml')
            project.addMapLayer(vlayer)
            layer = root.findLayer(vlayer.id())
            clone = layer.clone()
            parent = layer.parent()
            groupevt.insertChildNode(0, clone)
            parent.removeChildNode(layer)
            self.QgisV3LayerRandomColor(vlayer, self.form_wgt_libelle)
            vlayer.setReadOnly(True)
            vlayer.triggerRepaint()
        else:
            polylayer_fields = QgsFields()
            polylayer_fields.append(QgsField('libelle', QVariant.String))
            polylayer_fields.append(QgsField('date', QVariant.String))
            polylayer_fields.append(QgsField('h_creation', QVariant.String))
            polylayer_fields.append(QgsField('source', QVariant.String))
            polylayer_fields.append(QgsField('h_constat', QVariant.String))
            polylayer_fields.append(QgsField('remarques', QVariant.String))
            polylayer_fields.append(QgsField('surface', QVariant.Double, 'double', 10, 0))
            polylayer_fields.append(QgsField('utilisatr', QVariant.String))
            os.makedirs(evtpath + "/Evenements", exist_ok=True)
            lstlayerEVT.append((evtpath + "/Evenements/POLYGONE_EVENEMENT.shp", polylayer_fields, QgsWkbTypes.MultiPolygon, qmlpath + 'POLYGONE_EVENEMENT.qml'))

        if os.path.isfile(evtpath + "/Evenements/LIGNE_EVENEMENT.shp"):
            vlayer = QgsVectorLayer(evtpath + "/Evenements/LIGNE_EVENEMENT.shp", "LIGNE_EVENEMENT", "ogr")
            vlayer.loadNamedStyle(qmlpath + 'LIGNE_EVENEMENT.qml')
            project.addMapLayer(vlayer)
            layer = root.findLayer(vlayer.id())
            clone = layer.clone()
            parent = layer.parent()
            groupevt.insertChildNode(0, clone)
            parent.removeChildNode(layer)
            vlayer.setReadOnly(True)
            vlayer.triggerRepaint()
        else:
            lnglayer_fields = QgsFields()
            lnglayer_fields.append(QgsField('libelle', QVariant.String))
            lnglayer_fields.append(QgsField('date', QVariant.String))
            lnglayer_fields.append(QgsField('h_creation', QVariant.String))
            lnglayer_fields.append(QgsField('source', QVariant.String))
            lnglayer_fields.append(QgsField('h_constat', QVariant.String))
            lnglayer_fields.append(QgsField('remarques', QVariant.String))
            lnglayer_fields.append(QgsField('longueur', QVariant.Double, 'double', 10, 0))
            lnglayer_fields.append(QgsField('utilisatr', QVariant.String))
            lstlayerEVT.append((evtpath + "/Evenements/LIGNE_EVENEMENT.shp", lnglayer_fields, QgsWkbTypes.MultiLineString, qmlpath + 'LIGNE_EVENEMENT.qml'))

        if os.path.isfile(evtpath + "/Evenements/POINT_EVENEMENT.shp"):
            vlayer = QgsVectorLayer(evtpath + "/Evenements/POINT_EVENEMENT.shp", "POINT_EVENEMENT", "ogr")
            vlayer.loadNamedStyle(qmlpath + 'POINT_EVENEMENT.qml')
            project.addMapLayer(vlayer)
            layer = root.findLayer(vlayer.id())
            clone = layer.clone()
            parent = layer.parent()
            groupevt.insertChildNode(0, clone)
            parent.removeChildNode(layer)
            vlayer.setReadOnly(True)
            vlayer.triggerRepaint()
        else:
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
            lstlayerEVT.append((evtpath + "/Evenements/POINT_EVENEMENT.shp", ptlayer_fields, QgsWkbTypes.MultiPoint,  qmlpath + 'POINT_EVENEMENT.qml'))

        if lstlayerEVT != []:
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
                lyr.loadNamedStyle(layer[3])
                myptlayer = root.findLayer(lyr.id())
                myptlayerclone = myptlayer.clone()
                parent = myptlayer.parent()
                groupevt.insertChildNode(0, myptlayerclone)
                parent.removeChildNode(myptlayer)
                lyr.updateFields()
                lyr.triggerRepaint()
                lyr.commitChanges()
                # layer.setReadOnly(True)

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

    # def center(self):
    #     screen = QDesktopWidget().screenGeometry()
    #     # self.update_idletasks()
    #     print(str(self.geometry()))
    #     l, h, x, y = self.geoliste(self.geometry())
    #     self.geometry("%dx%d%+d%+d" % (l, h, (self.winfo_screenwidth() - l) // 2, (self.fen.winfo_screenheight() - h) // 2))
    #
    # def geoliste(g):
    #     r=[i for i in range(0,len(g)) if not g[i].isdigit()]
    #     return [int(g[0:r[0]]),int(g[r[0]+1:r[1]]),int(g[r[1]+1:r[2]]),int(g[r[2]+1:])]

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
                os.chdir(project.homePath())
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
        # self.verifEVT()
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
        
    def QgisV3LayerRandomColor(self, layer, fieldName):
        """
        QGIS3 : Classification automatique du moteur de rendu pyqgis catégorisé sur le champ 'fieldname' de la table attributaire 'layer'
        copyright           : (C) 2019 by Sylvain T., CNRS FR 3020
        Licence             : Creative Commons CC-BY-SA V4+
        Sources             : https://gis.stackexchange.com/questions/226642/automatic-pyqgis-categorized-renderer-classification
        :param layer: QgsVectorLayer
        :param fieldName: str
        :return:
        """

        # provide file name index and field's unique values
        fni = layer.dataProvider().fields().indexFromName(fieldName)
        unique_values = layer.uniqueValues(fni)

        # fill categories
        categories = []
        # print('layer.geometryType() : ' + str(layer.geometryType()))
        # layer.geometryType() : point = 0, ligne = 1, polygone = 2
        geom_type = layer.geometryType()
        for unique_value in unique_values:
            # initialize the default symbol for this geometry type
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            if geom_type == 0:
                # Réglage de la taille des points
                symbol.setSize(4)
            elif geom_type == 1:
                # Réglage de l'épaisseur des lignes
                symbol.setWidth(1.5)
            symbol.setOpacity(0.4)

            # Couleurs aléatoires, le dernier paramètre règle le niveau de transparence (de 0 à 100%) Impose l'importation de random
            # layer_style = {}
            # layer_style['color'] = '%d, %d, %d, %d' % (random.randrange(0, 256), random.randrange(0, 256), random.randrange(0, 256), 40)
            # layer_style['outline'] = '#000000'
            # symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
            # # replace default symbol layer with the configured one
            # if symbol_layer is not None:
            #     symbol.changeSymbolLayer(0, symbol_layer)

            # Couleur rouge sur tous les objets
            symbol.setColor(QColor(255, 0, 0))

            # create renderer object
            category = QgsRendererCategory(unique_value, symbol, str(unique_value))
            # entry for the list of category items
            categories.append(category)

        # create renderer object
        renderer = QgsCategorizedSymbolRenderer(fieldName, categories)
        # assign the created renderer to the layer
        if renderer is not None:
            layer.setRenderer(renderer)

        layer.triggerRepaint()

