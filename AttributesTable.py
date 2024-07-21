# -*- coding: utf-8 -*-

# Qgeric: Graphical queries by drawing simple shapes.
# Author: Jérémy Kalsron
#         jeremy.kalsron@gmail.com
# Contributor : François Thévand
#         francois.thevand@gmail.com
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

import os, unicodedata, random, sys
import webbrowser
from qgis import utils
from qgis.PyQt import QtGui, QtCore
from qgis.PyQt.QtGui import QIcon, QColor, QPixmap
from qgis.PyQt.QtCore import Qt, QSize, QDate, QTime, QDateTime, QTranslator, QCoreApplication, QVariant, QSettings, QLocale, qVersion, QItemSelectionModel
from qgis.PyQt.QtWidgets import (QWidget, QDesktopWidget, QTabWidget, QVBoxLayout, QProgressDialog,
                                QStatusBar, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog,
                                QToolBar, QAction, QApplication, QHeaderView, QInputDialog, QComboBox,
                                QLineEdit, QMenu, QWidgetAction, QMessageBox, QDateEdit, QTimeEdit, QDateTimeEdit)
from qgis.core import QgsWkbTypes, QgsVectorLayer, QgsProject, QgsGeometry, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsApplication, QgsLayerTreeGroup
from qgis.gui import QgsMessageBar, QgsHighlight
from functools import partial
from . import odswriter as ods
from . import resources
from qgis.utils import *

# Display and export attributes from all active layers
class AttributesTable(QWidget):
    # Un attribut passé à une classe se récupère ici dans def __init__
    # def __init__(self, iface, name):
    def __init__(self, name):
        QWidget.__init__(self)

        # *** ATTENTION *** : dans le fichier de traduction la ligne <name>QdrawEVT</name> porte sur la classe principale (ici QdrawEVT dans le fichier qdrawEVT.py)
        overrideLocale = QSettings().value("locale/overrideFlag", False, type=bool)
        if not overrideLocale: locale = QLocale.system().name()
        else:
            locale = QSettings().value("locale/userLocale", "")
            if locale.__class__.__name__=='QVariant': locale= 'en'
        locale = locale[0:2]
        locale_path = os.path.join(
            os.path.dirname(__file__),
            'i18n',
            'qdrawEVT_{}.qm'.format(locale))
        self.translator = None
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.setWindowTitle(self.tr('Selection made in') + ' ' + name)
        self.resize(480,320)
        self.setMinimumSize(320,240)
        self.center()
        self.name = name
        # Results export button
        self.btn_saveTab = QAction(QIcon(':/plugins/qdrawEVT/resources/icon_save.png'), self.tr('Save this tab\'s results'), self)
        self.btn_saveTab.triggered.connect(lambda : self.saveAttributes(True))
        self.btn_saveAllTabs = QAction(QIcon(':/plugins/qdrawEVT/resources/icon_saveAll.png'), self.tr('Save all results'), self)
        self.btn_saveAllTabs.triggered.connect(lambda : self.saveAttributes(False))

        # Ajouter un bouton avec icone intégrées à qgis
        # self.btn_monBouton = QAction(QIcon(":images/themes/default/mActionSelectAll.svg"), self.tr('Select all items'), self)

        self.btn_export = QAction(QIcon(':/plugins/qdrawEVT/resources/icon_export.png'), self.tr('Export the selection as a memory layer'), self)
        self.btn_export.triggered.connect(self.exportLayer)
        self.btn_exportAll = QAction(QIcon(':/plugins/qdrawEVT/resources/icon_exportAll.png'), self.tr('Export all tabs as a memory layer'), self)
        self.btn_exportAll.triggered.connect(self.exportAllLayer)
        self.btn_zoom = QAction(QIcon(':/plugins/qdrawEVT/resources/icon_Zoom.png'), self.tr('Zoom to selected attributes'), self)
        self.btn_zoom.triggered.connect(self.zoomToFeature)
        self.btn_selectGeom = QAction(QIcon(':/plugins/qdrawEVT/resources/icon_HlG.png'), self.tr("Highlight feature's geometry"), self)
        self.btn_selectGeom.triggered.connect(self.selectGeomChanged)
        self.btn_rename = QAction(QIcon(':/plugins/qdrawEVT/resources/icon_Settings.png'), self.tr('Settings'), self)
        self.btn_rename.triggered.connect(self.renameWindow)
                
        self.tabWidget = QTabWidget() # Tab container
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.currentChanged.connect(self.highlight_features)
        self.tabWidget.tabCloseRequested.connect(self.closeTab)
        
        self.loadingWindow = QProgressDialog()
        self.loadingWindow.setWindowTitle(self.tr('Loading...'))
        self.loadingWindow.setRange(0,100)
        self.loadingWindow.setAutoClose(False)
        self.loadingWindow.setCancelButton(None)

        self.project = QgsProject.instance()
        self.root = self.project.layerTreeRoot()

        self.canvas = iface.mapCanvas()
        self.canvas.extentsChanged.connect(self.highlight_features)
        self.highlight = []
        self.highlight_rows = []
        
        toolbar = QToolBar()
        toolbar.addAction(self.btn_saveTab)
        toolbar.addAction(self.btn_saveAllTabs)
        toolbar.addSeparator()
        toolbar.addAction(self.btn_export)
        toolbar.addAction(self.btn_exportAll)
        toolbar.addSeparator()
        toolbar.addAction(self.btn_zoom)
        toolbar.addSeparator()
        toolbar.addAction(self.btn_selectGeom)
        toolbar.addAction(self.btn_rename)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(0,0,0,0)
        vbox.addWidget(toolbar)
        vbox.addWidget(self.tabWidget)
        self.setLayout(vbox)
        
        self.mb = iface.messageBar()
        
        self.selectGeom = False # False for point, True for geometry

    def renameWindow(self):
        title, ok = QInputDialog.getText(self, self.tr('Rename window'), self.tr('Enter a new title:'))  
        if ok:
            self.setWindowTitle(title)
            
    def closeTab(self, index):
        self.tabWidget.widget(index).deleteLater()
        self.tabWidget.removeTab(index)
        
    def selectGeomChanged(self):
        if self.selectGeom:
            self.selectGeom = False
            self.btn_selectGeom.setText(self.tr("Highlight feature's geometry"))
            self.btn_selectGeom.setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_HlG.png'))
        else:
            self.selectGeom = True
            self.btn_selectGeom.setText(self.tr("Highlight feature's centroid"))
            self.btn_selectGeom.setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_HlC.png'))
        self.highlight_features()

    def exportAllLayer(self):
        # Tests de la présence des groupes spécifiques gestion de crise
        for group in self.root.children():
            # Test couvrant les cas d'écriture avec accent et/ou majuscule en entête (Mettre le mot à rechercher en majuscules)
            test = ''.join(
                x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test == 'DESSINS':
                self.groupe_dessin = self.root.findGroup('Dessins')
                # Décochage, groupe inutile dans la sélection
                self.groupe_dessin.setItemVisibilityCheckedRecursive(False)
            else:
                self.groupe_dessin = None
            if test == 'EVENEMENTS':
                self.groupe_evt = self.root.findGroup('Evenements')
                # Décochage, groupe inutile dans la sélection
                self.groupe_evt.setItemVisibilityCheckedRecursive(False)
            else:
                self.groupe_evt = None
            if test == 'ENJEUX':
                self.groupe_enjeux = self.root.findGroup('Enjeux')
                # Cochage des groupes désirés dans la sélection
                self.groupe_enjeux.setItemVisibilityCheckedRecursive(True)
            else:
                self.groupe_enjeux = None
            if test == 'ADMINISTRATIF':
                self.groupe_administratif = self.root.findGroup('Administratif')
                # Décochage, groupe inutile dans la sélection
                self.groupe_administratif.setItemVisibilityCheckedRecursive(False)
            else:
                self.groupe_administratif = None

        tab_count = self.tabWidget.count()
        if tab_count != 0:
            for tab in range(0, tab_count):
                index = tab
                table = self.tabWidget.widget(index).findChildren(QTableWidget)[0]
                # ligne ajoutée pour sélection de tous les items et exportation
                table.selectAll()
                items = table.selectedItems()
                if len(items) > 0:
                    type = ''
                    if items[0].feature.geometry().type() == QgsWkbTypes.PointGeometry:
                        type = 'Point'
                    elif items[0].feature.geometry().type() == QgsWkbTypes.LineGeometry:
                        type = 'LineString'
                    else:
                        type = 'Polygon'
                    features = []
                    for item in items:
                        if item.feature not in features:
                            features.append(item.feature)
                    name = self.tr('Extract') + ' ' + table.title

                    # Pour affichage d'une boite de dialogue de denommage de l'extraction
                    # name = ''
                    # while not name.strip() and ok == True:
                    #     name, ok = QInputDialog.getText(self, self.tr('Layer name'), self.tr('Give a name to the layer:'))
                    # if ok:

                    layer = QgsVectorLayer(type + "?crs=" + table.crs.authid(), name, "memory")
                    layer.startEditing()
                    layer.dataProvider().addAttributes(features[0].fields().toList())
                    layer.dataProvider().addFeatures(features)
                    name_extracts = self.tr('Extracts in') + ' ' + self.name
                    if self.project.layerTreeRoot().findGroup(name_extracts) is None:
                        self.project.layerTreeRoot().insertChildNode(0, QgsLayerTreeGroup(name_extracts))
                    group_extr = self.project.layerTreeRoot().findGroup(name_extracts)
                    self.project.addMapLayer(layer, False)
                    # layerclone = layer.clone()
                    # parent = layer.parent()
                    group_extr.insertLayer(0, layer)
                    # Les deux commandes suivantes sont nécessaire pour que le groupe soit développé
                    group_extr.setExpanded(False)
                    group_extr.setExpanded(True)
                    # parent.removeChildNode(layer)
                    layer.commitChanges()

                    # Option 1 de copier-coller de tous les styles de la couche dans laquelle est faite l'extraction vers la couche extraite
                    # RECUPERE LES ACTIONS
                    src_lyrs = QgsProject.instance().mapLayersByName(table.title)
                    src = iface.setActiveLayer(src_lyrs[0])
                    if src:
                        iface.actionCopyLayerStyle().trigger()
                        dest_lyrs = iface.setActiveLayer(layer)
                        if dest_lyrs:
                            # print('copie du style dans ' + str(dest_lyrs))
                            iface.actionPasteLayerStyle().trigger()

                    # Option 2 de copier-coller de tous les styles de la couche dans laquelle est faite l'extraction vers la couche extraite
                    # NE RECUPERE PAS LES ACTIONS
                    # layer_from = QgsProject.instance().mapLayersByName(table.title)[0]
                    # layer_to = QgsProject.instance().mapLayersByName(layer.name())[0]
                    # layer_to.styleManager().copyStylesFrom(layer_from.styleManager())

                    # Option 3 de récupération du style de la couche dans laquelle est faite l'extraction
                    # NE RECUPERE PAS LES ACTIONS
                    # style = QgsProject.instance().mapLayersByName(table.title)[0].renderer()
                    # # Application du style à l'extrait de couche
                    # if style != None:
                    #     layer.setRenderer(style)
                    #     layer.triggerRepaint()
                else:
                    # self.mb.pushWarning(self.tr('Warning'), self.tr('There is no selected feature!'))
                    pass
                table.clearSelection()

            nodes = self.root.children()
            for n in nodes:
                if isinstance(n, QgsLayerTreeGroup):
                    if n.isExpanded() == True:
                        n.setExpanded(False)
                        # print(f"Layer group '{n.name()}' now collapsed.")
            # Tests de la présence des groupes spécifiques gestion de crise
            for group in self.root.children():
                # Test couvrant les cas d'écriture avec accent et/ou majuscule en entête (Mettre le mot à rechercher en majuscules)
                test = ''.join(
                    x for x in unicodedata.normalize('NFKD', group.name()) if
                    unicodedata.category(x)[0] == 'L').upper()
                # Cochage et expansion du groupe dessins si présent
                if test == 'DESSINS':
                    self.groupe_dessin = self.root.findGroup('Dessins')
                    self.groupe_dessin.setItemVisibilityCheckedRecursive(True)
                    self.groupe_dessin.setExpanded(False)
                    self.groupe_dessin.setExpanded(True)
                # Cochage et expansion du groupe evenements si présent
                if test == 'EVENEMENTS':
                    self.groupe_evt = self.root.findGroup('Evenements')
                    self.groupe_evt.setItemVisibilityCheckedRecursive(True)
                    self.groupe_evt.setExpanded(False)
                    self.groupe_evt.setExpanded(True)
                # Décochage du groupe enjeux si présent
                if test == 'ENJEUX':
                    self.groupe_enjeux = self.root.findGroup('Enjeux')
                    self.groupe_enjeux.setItemVisibilityChecked(False)
                    # self.groupe_enjeux.setExpanded(True)
                    # self.groupe_enjeux.setExpanded(False)
            # On déplie le groupe extraction et on rafraichit l'affichage
            group_extr.setExpanded(False)
            group_extr.setExpanded(True)
            self.select(group_extr)
            layerNode = self.root.findLayer(layer.id())
            layerNode.setExpanded(False)
            layerNode.setExpanded(True)
            iface.layerTreeView().refreshLayerSymbology(layer.id())
            iface.mapCanvas().refresh()
            table.clearSelection()

    def exportLayer(self):
        if self.tabWidget.count() != 0:
            index = self.tabWidget.currentIndex()
            table = self.tabWidget.widget(index).findChildren(QTableWidget)[0]
            # ligne ajoutée pour sélection de tous les items et exportation
            table.selectAll()
            items = table.selectedItems()
            name = self.tr('Extract') + ' ' + table.title
            name_extracts = self.tr('Extracts in') + ' ' + self.name
            if self.project.layerTreeRoot().findGroup(name_extracts) is None:
                self.project.layerTreeRoot().insertChildNode(0, QgsLayerTreeGroup(name_extracts))
            group_extr = self.project.layerTreeRoot().findGroup(name_extracts)
            if len(items) > 0:
                type = ''
                if items[0].feature.geometry().type() == QgsWkbTypes.PointGeometry:
                    type = 'Point'
                elif items[0].feature.geometry().type() == QgsWkbTypes.LineGeometry:
                    type = 'LineString'
                else:
                    type = 'Polygon'
                features = []
                for item in items:
                    if item.feature not in features:
                        features.append(item.feature)

                # Pour affichage d'une boite de dialogue  denommage de l'extraction
                # name = ''
                # while not name.strip() and ok == True:
                #     name, ok = QInputDialog.getText(self, self.tr('Layer name'), self.tr('Give a name to the layer:'))
                # if ok:

                layer = QgsVectorLayer(type+"?crs="+table.crs.authid(), name, "memory")
                layer.startEditing()
                layer.dataProvider().addAttributes(features[0].fields().toList())
                layer.dataProvider().addFeatures(features)
                self.project.addMapLayer(layer, False)
                group_extr.insertLayer(0, layer)
                layer.commitChanges()

                # Option 1 de copier-coller de tous les styles de la couche dans laquelle est faite l'extraction vers la couche extraite
                # RECUPERE LES ACTIONS
                src_lyrs = QgsProject.instance().mapLayersByName(table.title)
                src = iface.setActiveLayer(src_lyrs[0])
                if src:
                    iface.actionCopyLayerStyle().trigger()
                    dest_lyrs = iface.setActiveLayer(layer)
                    if dest_lyrs:
                        # print('copie du style dans ' + str(dest_lyrs))
                        iface.actionPasteLayerStyle().trigger()

                # Option 2 de copier-coller de tous les styles de la couche dans laquelle est faite l'extraction vers la couche extraite
                # NE RECUPERE PAS LES ACTIONS
                # layer_from = QgsProject.instance().mapLayersByName(table.title)[0]
                # layer_to = QgsProject.instance().mapLayersByName(layer.name())[0]
                # layer_to.styleManager().copyStylesFrom(layer_from.styleManager())

                # Option 3 de récupération du style de la couche dans laquelle est faite l'extraction
                # NE RECUPERE PAS LES ACTIONS
                # style = QgsProject.instance().mapLayersByName(table.title)[0].renderer()
                # # Application du style à l'extrait de couche
                # if style != None:
                #     layer.setRenderer(style)
                #     layer.triggerRepaint()

                nodes = self.root.children()
                for n in nodes:
                    if isinstance(n, QgsLayerTreeGroup):
                        if n.isExpanded() == True:
                            n.setExpanded(False)
                            # print(f"Layer group '{n.name()}' now collapsed.")
                # Tests de la présence des groupes spécifiques gestion de crise
                for group in self.root.children():
                    # Test couvrant les cas d'écriture avec accent et/ou majuscule en entête (Mettre le mot à rechercher en majuscules)
                    test = ''.join(
                        x for x in unicodedata.normalize('NFKD', group.name()) if
                        unicodedata.category(x)[0] == 'L').upper()
                    # Cochage et expansion du groupe dessins si présent
                    if test == 'DESSINS':
                        self.groupe_dessin = self.root.findGroup('Dessins')
                        self.groupe_dessin.setItemVisibilityCheckedRecursive(True)
                        self.groupe_dessin.setExpanded(False)
                        self.groupe_dessin.setExpanded(True)
                    # Cochage et expansion du groupe evenements si présent
                    if test == 'EVENEMENTS':
                        self.groupe_evt = self.root.findGroup('Evenements')
                        self.groupe_evt.setItemVisibilityCheckedRecursive(True)
                        self.groupe_evt.setExpanded(False)
                        self.groupe_evt.setExpanded(True)
                    # Décochage du groupe enjeux si présent
                    if test == 'ENJEUX':
                        self.groupe_enjeux = self.root.findGroup('Enjeux')
                        self.groupe_enjeux.setItemVisibilityChecked(False)
                        # self.groupe_enjeux.setExpanded(True)
                        # self.groupe_enjeux.setExpanded(False)
                # On déplie le groupe extraction et on rafraichit l'affichage
            else:
                # self.mb.pushWarning(self.tr('Warning'), self.tr('There is no selected feature!'))
                pass
            group_extr.setExpanded(False)
            group_extr.setExpanded(True)
            self.select(group_extr)
            layerNode = self.root.findLayer(layer.id())
            layerNode.setExpanded(False)  # added TRUE
            layerNode.setExpanded(True)
            iface.layerTreeView().refreshLayerSymbology(layer.id())
            iface.mapCanvas().refresh()
            table.clearSelection()

    def highlight_features(self):
        for item in self.highlight:
            self.canvas.scene().removeItem(item)
        del self.highlight[:]
        del self.highlight_rows[:]
        index = self.tabWidget.currentIndex()
        tab = self.tabWidget.widget(index)
        if self.tabWidget.count() != 0:
            table = self.tabWidget.widget(index).findChildren(QTableWidget)[0]
            nb = 0
            area = 0
            length = 0
            items = table.selectedItems()
            for item in items:
                if item.row() not in self.highlight_rows:
                    if self.selectGeom:
                        highlight = QgsHighlight(self.canvas, item.feature.geometry(), self.tabWidget.widget(index).layer)
                    else:
                        highlight = QgsHighlight(self.canvas, item.feature.geometry().centroid(), self.tabWidget.widget(index).layer)
                    highlight.setColor(QColor(255,0,0))
                    self.highlight.append(highlight)
                    self.highlight_rows.append(item.row())
                    g = QgsGeometry(item.feature.geometry())
                    # geometry reprojection to get meters
                    g.transform(QgsCoordinateTransform(tab.layer.crs(), QgsProject.instance().crs(), QgsProject.instance()))
                    nb += 1
                    area += g.area()
                    length += g.length()
            if tab.layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                tab.sb.showMessage(self.tr('Selected features') + ': ' + str(nb) + '  ' + self.tr('Area') + ': '+"%.2f"%area+' m'+u'²')
            elif tab.layer.geometryType() == QgsWkbTypes.LineGeometry:
                tab.sb.showMessage(self.tr('Selected features')+': '+str(nb)+'  '+self.tr('Length')+': '+"%.2f"%length+' m')
            else:
                tab.sb.showMessage(self.tr('Selected features')+': '+str(nb))
    
    def tr(self, message):
        return QCoreApplication.translate('QdrawEVT', message)
        
    def zoomToFeature(self):
        index = self.tabWidget.currentIndex()
        table = self.tabWidget.widget(index).findChildren(QTableWidget)[0]
        items = table.selectedItems()
        feat_id = []
        for item in items:
            feat_id.append(item.feature.id())
        if len(feat_id) >= 1:
            if len(feat_id) == 1:
                self.canvas.setExtent(items[0].feature.geometry().buffer(5, 0).boundingBox()) # in case of a single point, it will still zoom to it
            else:
                self.canvas.zoomToFeatureIds(self.tabWidget.widget(self.tabWidget.currentIndex()).layer, feat_id)         
        self.canvas.refresh() 
    
    # Add a new tab

    # Modification F. Thévand ajout paramètre visible :
    # (layer, fields_name, fields_type, cells, idx_visible)

    def addLayer(self, layer, headers, types, features, visible):
        self.layer = layer
        # print('layer entrée addLayer : ' + str(self.layer))
        tab = QWidget()
        tab.layer = self.layer
        p1_vertical = QVBoxLayout(tab)
        p1_vertical.setContentsMargins(0,0,0,0)
        
        table = QTableWidget()
        table.itemSelectionChanged.connect(self.highlight_features)
        table.title = self.layer.name()
        table.crs = self.layer.crs()
        table.setColumnCount(len(headers))
        if len(features) > 0:
            table.setRowCount(len(features))
            nbrow = len(features)
            self.loadingWindow.show()
            self.loadingWindow.setLabelText(table.title)
            self.loadingWindow.activateWindow()
            self.loadingWindow.showNormal()
            
            # Table population
            m = 0
            for feature in features:
                n = 0

                # Ancienne syntaxe :
                #                for cell in feature.attributes():
                #                    item = QTableWidgetItem()
                #                    item.setData(Qt.DisplayRole, cell)
                #                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                #                    item.feature = feature
                #                    table.setItem(m, n, item)
                #                    n += 1

                # Modification F. Thévand :
                for idx in visible:
                    try:
                        item = QTableWidgetItem()
                        item.setData(Qt.DisplayRole, feature[idx])
                        # Fin modification
                        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                        item.feature = feature
                        table.setItem(m, n, item)
                        n += 1
                    except KeyError:
                        pass
                m += 1
                self.loadingWindow.setValue(int((float(m) / nbrow) * 100))
                QApplication.processEvents()

        else:
            table.setRowCount(0)  
                            
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionsMovable(True)
        
        table.types = types
        table.filter_op = []
        table.filters = []
        for i in range(0, len(headers)):
            table.filters.append('')
            table.filter_op.append(0)
        
        header = table.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(partial(self.filterMenu, table))
            
        table.setSortingEnabled(True)
        
        p1_vertical.addWidget(table)
        
        # Status bar to display informations (ie: area)
        tab.sb = QStatusBar()
        p1_vertical.addWidget(tab.sb)
        
        title = table.title
        # We reduce the title's length to 20 characters
        if len(title)>20:
            title = title[:20]+'...'
        
        # We add the number of elements to the tab's title.
        title += ' ('+str(len(features))+')'
            
        self.tabWidget.addTab(tab, title) # Add the tab to the conatiner
        self.tabWidget.setTabToolTip(self.tabWidget.indexOf(tab), table.title) # Display a tooltip with the layer's full name
     
    def filterMenu(self, table, pos):
        index = table.columnAt(pos.x())
        menu = QMenu()
        filter_operation = QComboBox()
        if table.types[index] in [10]:
            filter_operation.addItems(['Contains', 'Equals'])
        else:
            filter_operation.addItems(['=','>','<'])
        filter_operation.setCurrentIndex(table.filter_op[index])
        action_filter_operation = QWidgetAction(self)
        action_filter_operation.setDefaultWidget(filter_operation)
        if table.types[index] in [14]:
            if not isinstance(table.filters[index], QDate):
                filter_value = QDateEdit()
            else:
                filter_value = QDateEdit(table.filters[index])
        elif table.types[index] in [15]:
            if not isinstance(table.filters[index], QTime):
                filter_value = QTimeEdit()
            else:
                filter_value = QTimeEdit(table.filters[index])
        elif table.types[index] in [16]:
            if not isinstance(table.filters[index], QDateTime):
                filter_value = QDateTimeEdit()
            else:
                filter_value = QDateTimeEdit(table.filters[index])
        else:
            filter_value = QLineEdit(table.filters[index])
        action_filter_value = QWidgetAction(self)
        action_filter_value.setDefaultWidget(filter_value)
        menu.addAction(action_filter_operation)
        menu.addAction(action_filter_value)
        action_filter_apply = QAction('Apply', self)
        action_filter_apply.triggered.connect(partial(self.applyFilter, table, index, filter_value, filter_operation))
        action_filter_cancel = QAction('Cancel', self)
        action_filter_cancel.triggered.connect(partial(self.applyFilter, table, index, None, filter_operation))
        menu.addAction(action_filter_apply)
        menu.addAction(action_filter_cancel)
        menu.exec_(QtGui.QCursor.pos())
     
    def applyFilter(self, table, index, filter_value, filter_operation):
        if filter_value == None:
            table.filters[index] = None
        else:
            if isinstance(filter_value, QDateEdit):
                table.filters[index] = filter_value.date()
            elif isinstance(filter_value, QTimeEdit):
                table.filters[index] = filter_value.time()
            elif isinstance(filter_value, QDateTimeEdit):
                table.filters[index] = filter_value.dateTime()
            else:
                table.filters[index] = filter_value.text()
        table.filter_op[index] = filter_operation.currentIndex()
        nb_elts = 0
        for i in range(0, table.rowCount()):
            table.setRowHidden(i, False)
            nb_elts += 1
        hidden_rows = []
        for nb_col in range(0, table.columnCount()):
            filtered = False
            header = table.horizontalHeaderItem(nb_col).text()
            valid = False
            if table.filters[nb_col] is not None:
                if  type(table.filters[nb_col]) in [QDate, QTime, QDateTime]:
                    valid = True
                else:
                    if table.filters[nb_col].strip():
                        valid = True
            if valid:
                filtered = True
                items = None
                if table.types[nb_col] in [10]:# If it's a string
                    filter_type = None
                    if table.filter_op[nb_col] == 0: # Contain
                        filter_type = Qt.MatchContains
                    if table.filter_op[nb_col] == 1: # Equal
                        filter_type = Qt.MatchFixedString 
                    items = table.findItems(table.filters[nb_col], filter_type)
                elif table.types[nb_col] in [14, 15, 16]: # If it's a date/time
                    items = []
                    for nb_row in range(0, table.rowCount()):
                        item = table.item(nb_row, nb_col)
                        if table.filter_op[nb_col] == 0: # =
                            if  item.data(QTableWidgetItem.Type) == table.filters[nb_col]:
                                items.append(item)
                        if table.filter_op[nb_col] == 1: # >
                            if  item.data(QTableWidgetItem.Type) > table.filters[nb_col]:
                                items.append(item)
                        if table.filter_op[nb_col] == 2: # <
                            if  item.data(QTableWidgetItem.Type) < table.filters[nb_col]:
                                items.append(item)
                else: # If it's a number
                    items = []
                    for nb_row in range(0, table.rowCount()):
                        item = table.item(nb_row, nb_col)
                        if item.text().strip():
                            if table.filter_op[nb_col] == 0: # =
                                if  float(item.text()) == float(table.filters[nb_col]):
                                    items.append(item)
                            if table.filter_op[nb_col] == 1: # >
                                if  float(item.text()) > float(table.filters[nb_col]):
                                    items.append(item)
                            if table.filter_op[nb_col] == 2: # <
                                if  float(item.text()) < float(table.filters[nb_col]):
                                    items.append(item)
                rows = []
                for item in items:
                    if item.column() == nb_col:
                        rows.append(item.row())
                for i in range(0, table.rowCount()):
                    if i not in rows:
                        if i not in hidden_rows:
                            nb_elts -= 1
                        table.setRowHidden(i, True)
                        hidden_rows.append(i)
            if filtered:
                if header[len(header)-1] != '*':
                    table.setHorizontalHeaderItem(nb_col, QTableWidgetItem(header+'*'))
            else:
                if header[len(header)-1] == '*':
                    header = header[:-1]
                    table.setHorizontalHeaderItem(nb_col, QTableWidgetItem(header))
        
        title = self.tabWidget.tabText(self.tabWidget.currentIndex())
        for i in reversed(range(len(title))):
            if title[i] == ' ':
                break
            title = title[:-1]
        title += '('+str(nb_elts)+')'
        self.tabWidget.setTabText(self.tabWidget.currentIndex(), title)
       
    # Save tables in OpenDocument format
    # Use odswriter library
    def saveAttributes(self, active):
        # Création d'un sous-dossier "Extractions" dans le dossier contenant le projet
        os.makedirs(self.project.homePath() + '/Extractions', exist_ok=True)
        file = QFileDialog.getSaveFileName(self, self.tr('Save in...'),self.project.homePath() + '/Extractions', self.tr('OpenDocument Spreadsheet (*.ods)'))
        if file[0]:
            try:
                with ods.writer(open(file[0], "wb")) as odsfile:
                    tabs = None
                    if active:
                        tabs = self.tabWidget.currentWidget().findChildren(QTableWidget)
                    else:
                        tabs = self.tabWidget.findChildren(QTableWidget)
                    for table in reversed(tabs):
                        sheet = odsfile.new_sheet(
                            table.title[:20] + '...')  # For each tab in the container, a new sheet is created
                        sheet.writerow([
                                           table.title])  # Comme la longueur du titre de l'onglet est limitée, le nom complet de la couche est écrit dans la première ligne
                        nb_row = table.rowCount()
                        nb_col = table.columnCount()

                        # Fetching and writing of the table's header
                        header = []
                        for i in range(0, nb_col):
                            header.append(table.horizontalHeaderItem(i).text())
                        sheet.writerow(header)

                        # Fetching and writing of the table's items
                        for i in range(0, nb_row):
                            row = []
                            # Modification F. THEVAND pour conversion des chiffres du texte en float:
                            for j in range(0, nb_col):
                                try:
                                    attr = table.item(i, j).text()
                                except:
                                    continue
                                # Test pour colonne CP ou code insee commençant par zéro
                                # avec prise en compte des flottants de type 0,n
                                if attr[:1] != '0':
                                    try:
                                        attr = float(attr)
                                    except:
                                        pass
                                elif attr[:2] == '0,' or attr[:2] == '0.':
                                    try:
                                        attr = float(attr)
                                    except:
                                        pass
                                row.append(attr)
                            # Fin modification F. THEVAND
                            if not table.isRowHidden(i):
                                sheet.writerow(row)
                    valsortie = True
                # Définition du choix de l'ouverture du fichier sauvegardé
                box = QMessageBox()
                box.setIcon(QMessageBox.Information)
                box.setText(
                    self.tr("Creation of ods workbook completed:") + "\n\n" + file[0] + '\n\n' + self.tr('Open file?'))
                box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                box.setDefaultButton(QMessageBox.Yes)
                buttonYes = box.button(QMessageBox.Yes)
                buttonYes.setText(self.tr('Continue'))
                buttonNo = box.button(QMessageBox.No)
                buttonNo.setText(self.tr('Cancel'))
                # Pour que la fenêtre reste au premier plan de toutes les applications en cours
                box.setWindowFlags(Qt.WindowStaysOnTopHint)
                # print("Fichier " + str(file) + " créé")
                # print("Fichier " + str(file[0]) + " créé")
                box.exec_()
                if box.clickedButton() == buttonYes:
                    os.startfile(r'file://' + file[0])
                return valsortie
            except IOError:
                QMessageBox.critical(self, self.tr('Error'),
                                     self.tr("The file can't be written.") + '\n' + self.tr(
                                         "Maybe you don't have the rights or are trying to overwrite an opened file."))
                return False

    def center(self):
            # size_ecran = QtGui.QDesktopWidget().screenGeometry()
            screen = QDesktopWidget().screenGeometry()
            size = self.geometry()
            self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
        
    def clear(self):
        self.tabWidget.clear()
        for table in self.tabWidget.findChildren(QTableWidget):
            table.setParent(None)
        
    def closeEvent(self, e):
        result = QMessageBox.question(self, self.tr("Saving?"), self.tr("Would you like to save results before exit?"), buttons = QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if result == QMessageBox.Yes:
            if self.saveAttributes(False):
                self.clear()
                e.accept()
            else:
                e.ignore()
        elif result == QMessageBox.No:
            self.clear()
            e.accept()
        else:
            e.ignore()

    def select(self, name):
        view = iface.layerTreeView()
        m = view.model()
        listIndexes = m.match(m.index(0, 0), Qt.DisplayRole, name, Qt.MatchFixedString)
        if listIndexes:
            i = listIndexes[0]
            view.selectionModel().setCurrentIndex(i, QItemSelectionModel.ClearAndSelect)
        else:
            raise Exception(f"'{name}' not found")