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

from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QDialog, QComboBox, QLineEdit, QVBoxLayout, \
    QCheckBox, QDialogButtonBox, QLabel
from qgis.core import QgsProject

import os, unicodedata, random

class QDrawLayerDialog(QDialog):
    def __init__(self, iface, gtype, layerevt, evt):
        QDialog.__init__(self)

        self.setWindowTitle(self.tr('Drawing'))

        self.name = QLineEdit()
        # if gtype == 'point' or gtype == 'XYpoint' or gtype == 'text':
        if gtype == 'text':
            self.gtype = 'text'
        elif gtype == 'point' or gtype == 'XYpoint':
            self.gtype = 'Point'
        elif gtype == 'line':
            self.gtype = 'LineString'
        else:
            self.gtype = 'Polygon'

        # change here by QgsMapLayerComboBox()
        self.layerBox = QComboBox()
        self.layers = []
        for layer in QgsProject.instance().mapLayers().values():
            # test d'existance d'une couche en mémoire et inscription du nom de la couche dans la liste
            if layer.providerType() == "memory":
                # ligne suivante à remplacer par if layer.geometryType() == :
                if self.gtype in layer.dataProvider().dataSourceUri()[:26]: #  must be of the same type of the draw
                    if 'field='+self.tr('Drawings')+':string(255,0)' in layer.dataProvider().dataSourceUri()[-28:]: # must have its first field named Drawings, string type
                        self.layers.append(layer)
                        self.layerBox.addItem(layer.name())
            # test de correspondance du nom de la couche evenement et inscription du nom de la couche dans la liste
            if layer.name() == layerevt:
                self.layers.append(layer)
                self.layerBox.addItem(layer.name())

        if not evt:
            self.addLayer = QCheckBox(self.tr('Add to an existing layer'))
            self.addLayer.toggled.connect(self.addLayerChecked)
            self.addLayer.setEnabled(True)
            self.addLayer.setChecked(False)
        elif evt:
            self.addLayer = QCheckBox(self.tr('Add to an existing layer'))
            self.addLayer.toggled.connect(self.addLayerChecked)
            if self.gtype != 'text':
                self.addLayer.setEnabled(False)
                self.addLayer.setChecked(True)
            else:
                self.addLayer.setEnabled(False)
                self.addLayer.setChecked(False)
        # print('self.gtype : ' + str(self.gtype))
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel(self.tr("Give a name to the feature:")))
        vbox.addWidget(self.name)
        #if not evt:
        vbox.addWidget(self.addLayer)
        vbox.addWidget(self.layerBox)
        if len(self.layers) == 0:
            self.addLayer.setEnabled(False)
            self.layerBox.setEnabled(False)
        self.layerBox.setEnabled(False)
        vbox.addWidget(buttons)
        self.setLayout(vbox)
        self.name.setFocus()

    def tr(self, message):
        return QCoreApplication.translate('QdrawEVT', message)

    def addLayerChecked(self):
        if self.addLayer.checkState() == Qt.Checked:
            self.layerBox.setEnabled(True)
        else:
            self.layerBox.setEnabled(False)

    def getName(self, iface, gtype, layerevt, evt):
        dialog = QDrawLayerDialog(iface, gtype, layerevt, evt)
        result = dialog.exec_()
        return (
        dialog.name.text(),
        dialog.addLayer.checkState() == Qt.Checked,
        dialog.layerBox.currentIndex(),
        dialog.layers,
        result == QDialog.Accepted)

class QDrawLayerDialogSelection(QDialog):
    def __init__(self, root):
        QDialog.__init__(self)

        self.setWindowTitle(self.tr('Select'))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel(self.tr("Drawing completed. Make a selection in its grip? WARNING: remember to check the desired groups and layers in the selection")))
        vbox.addWidget(buttons)
        self.setLayout(vbox)
        # Obtenir l'instance du projet en cours
        self.project = QgsProject.instance()
        # Root du projet en cours
        self.root = self.project.layerTreeRoot()

    def tr(self, message):
        return QCoreApplication.translate('QdrawEVT', message)

    def getcoche(self, warning):
        list_coche = []
        for group in self.root.children():
            # print('group.name() : ' + group.name())
            # Test couvrant les cas d'écriture avec accent et/ou majuscule en entête (Mettre le mot à rechercher en majuscules)
            test = ''.join(
                x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test not in groupes_a_gerer:
                coche = self.root.findGroup(str(group.name()))
                if coche.isVisible():
                    list_coche.append(True)
            else:
                continue
        if list_coche == []:
            return False
        else:
            return True
