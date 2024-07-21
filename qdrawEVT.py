# -*- coding: utf-8 -*-

# qdrawEVT: plugin qui facilite le dessin
# Author: françois Thévand
#         francois.thevand@gmail.com
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le modifier
# selon les termes de la licence publique générale GNU telle que publiée par
# la Free Software Foundation, soit la version 3 de la Licence, soit
# (à votre choix) toute version ultérieure.
#
# Ce programme est distribué dans l'espoir qu'il sera utile,
# mais SANS AUCUNE GARANTIE ; sans même la garantie implicite de
# QUALITÉ MARCHANDE ou ADAPTATION À UN USAGE PARTICULIER. Voir le
# Licence publique générale GNU pour plus de détails.
#
# Vous devriez avoir reçu une copie de la licence publique générale GNU
# avec ce programme. Si ce n'est pas le cas, consultez <http://www.gnu.org/licenses/>.

from __future__ import print_function
from __future__ import absolute_import
from builtins import str
from builtins import object

from qgis.PyQt.QtCore import QTranslator, QSettings, QCoreApplication, QLocale, qVersion
from qgis.PyQt.QtWidgets import QAction, QApplication, QMessageBox, QMenu, QInputDialog, QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit,\
    QDateTimeEdit, QTimeEdit, QPushButton, QComboBox, QLabel, QCheckBox, QProgressDialog

from qgis.PyQt.QtGui import QIcon, QColor, QFont

from qgis.core import *

from qgis.gui import QgsRubberBand, QgsAttributeEditorContext, QgsLayerTreeMapCanvasBridge

from .AttributesTable import *

from .drawtools import DrawPoint, DrawRect, DrawLine, DrawCircle, DrawPolygon, SelectPoint, XYDialog, DMSDialog

from .qdrawsettings import QdrawSettings

from .qdrawlayerdialogEVT import QDrawLayerDialog, QDrawLayerDialogSelection

from datetime import datetime, date, time

import os, unicodedata, random

from . import resources

# Test existance du groupe Evènements avec suppression des espaces et des accents dans le nom du groupe testé
# evt = False
# groupevt = False
# for group in root.children():
#     test = ''.join(
#         x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
#     if test == 'EVENEMENTS':
#         evt = True
#         groupevt = group

# Inscrire ici le nom des couches evenement et les noms de colonnes attributaires utilisées dans ces couches
evtpnt = 'POINT_EVENEMENT'
evtlgn = 'LIGNE_EVENEMENT'
evtpol = 'POLYGONE_EVENEMENT'
lst_form_wgt = ['libelle','date','h_creation','source','h_constat','remarques','surface','longueur','x_gps','y_gps','utilisatr']
form_wgt_libelle = 'libelle'
form_wgt_date = 'date'
form_wgt_h_creation = 'h_creation'
form_wgt_source = 'source'
form_wgt_h_constat = 'h_constat'
form_wgt_remarques = 'remarques'
form_wgt_surface = 'surface'
form_wgt_longueur = 'longueur'
form_wgt_x_gps = 'x_gps'
form_wgt_y_gps = 'y_gps'
form_wgt_utilisatr = 'utilisatr'
# Inscrire ici le nom des groupes devant être oté de la sélection
# En majuscules et sans espaces pour test avec boucle sur fonction :
# for group in self.root.children():
#   test = ''.join(x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
lst_group_no_select = ['FONDSDEPLAN']
lst_group_evt = ['EVENEMENTS']
lst_group_drawing = ['DESSINS']

#Fonction de reconstruction du chemin absolu vers la ressource image ou autre fichier
def resolve(name, basepath=None):
  if not basepath:
    basepath = os.path.dirname(os.path.realpath(__file__))
  return os.path.join(basepath, name)

class QdrawEVT(object):
    def __init__(self, iface):

        self.feature = None
        self.features = None
        self.layer = None
        self.index = None
        self.layers = None
        self.featureid = None
        self.groupes_coches = None
        self.request = None
        self.XYcrs = None
        self.layerevtname = None
        self.drawShape = None

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

        # *** ATTENTION *** : dans le fichier de traduction la ligne <name>QdrawEVT</name> porte sur la classe principale (ici QdrawEVT dans le fichier qdrawEVT.py)

        self.translator = None
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Obtenir l'instance du projet en cours
        self.project = QgsProject.instance()
        # Root du projet en cours
        self.root = self.project.layerTreeRoot()

        # # mise en variable des groupes a gérer pour la sélection
        # self.group_no_select = []
        # for group in self.root.children():
        #     test = ''.join(x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
        #     if test in lst_group_no_select:
        #         self.group_no_select.append(group)
        #
        # self.group_evt = []
        # for group in self.root.children():
        #     test = ''.join(
        #         x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
        #     if test in lst_group_evt:
        #         self.group_evt.append(group)
        #
        # self.group_drawing = []
        # for group in self.root.children():
        #     test = ''.join(
        #         x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
        #     if test in lst_group_drawing:
        #         self.group_evt.append(group)
        # if self.group_evt != []:
        #     self.evt = True
        # else:
        #     self.evt = False

        self.evt = None
        self.group_no_select = []
        self.group_evt = []
        self.group_drawing = []

        self.iface = iface
        self.sb = self.iface.statusBarIface()
        self.tool = None
        self.toolname = None

        self.results = []

        self.bGeom = None

        self.actions = []
        self.menu = '&QdrawEVT'
        self.toolbar = self.iface.addToolBar('QdrawEVT')
        self.toolbar.setObjectName('QdrawEVT')

        self.settings = QdrawSettings(form_wgt_libelle)
        # self.bridge = QgsLayerTreeMapCanvasBridge(QgsProject.instance().layerTreeRoot(), self.iface.mapCanvas())

        # Ajout de la fenêtre de sélection
        self.loadingWindow = QProgressDialog(self.tr('Selecting...'),self.tr('Pass'),0,100)
        self.loadingWindow.setAutoClose(False)
        self.loadingWindow.close()

    def unload(self):
        for action in self.actions:
            self.iface.removePluginVectorMenu('&QdrawEVT', action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def tr(self, message):
        return QCoreApplication.translate('QdrawEVT', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            checkable=False,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            menu=None,
            parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        action.setCheckable(checkable)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if menu is not None:
            action.setMenu(menu)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):

        pointMenu = QMenu()
        pointMenu.addAction(
            QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtXY_EVT.png'),
            self.tr('XY Point drawing tool'), self.drawXYPoint)
        pointMenu.addAction(
            QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtDMS_EVT.png'),
            self.tr('DMS Point drawing tool'), self.drawDMSPoint)
        icon_path = ':/plugins/qdrawEVT/resources/icon_DrawText_EVT.png'
        self.add_action(
            icon_path,
            text=self.tr('Outil de dessin de texte'),
            checkable=True,
            callback=self.drawText,
            parent=self.iface.mainWindow()
        )
        icon_path = ':/plugins/qdrawEVT/resources/icon_DrawPt_EVT.png'
        self.add_action(
            icon_path,
            text=self.tr('Point drawing tool'),
            checkable=True,
            menu=pointMenu,
            callback=self.drawPoint,
            parent=self.iface.mainWindow()
        )
        icon_path = ':/plugins/qdrawEVT/resources/icon_DrawL_EVT.png'
        self.add_action(
            icon_path,
            text=self.tr('Line drawing tool'),
            checkable=True,
            callback=self.drawLine,
            parent=self.iface.mainWindow()
        )
        icon_path = ':/plugins/qdrawEVT/resources/icon_DrawR_EVT.png'
        self.add_action(
            icon_path,
            text=self.tr('Rectangle drawing tool'),
            checkable=True,
            callback=self.drawRect,
            parent=self.iface.mainWindow()
        )
        icon_path = ':/plugins/qdrawEVT/resources/icon_DrawC_EVT.png'
        self.add_action(
            icon_path,
            text=self.tr('Circle drawing tool'),
            checkable=True,
            callback=self.drawCircle,
            parent=self.iface.mainWindow()
        )
        icon_path = ':/plugins/qdrawEVT/resources/icon_DrawP_EVT.png'
        self.add_action(
            icon_path,
            text=self.tr('Polygon drawing tool'),
            checkable=True,
            callback=self.drawPolygon,
            parent=self.iface.mainWindow()
        )
        bufferMenu = QMenu()
        polygonBufferAction = QAction(
            QIcon(':/plugins/qdrawEVT/resources/icon_DrawTP_EVT.png'),
            self.tr('Buffer drawing with polygonal selection of objects in the selected layer'),
            bufferMenu)
        polygonBufferAction.triggered.connect(self.drawPolygonBuffer)
        bufferMenu.addAction(polygonBufferAction)
        icon_path = ':/plugins/qdrawEVT/resources/icon_DrawT_EVT.png'
        self.add_action(
            icon_path,
            text=self.tr('Buffer drawing on objects in selected layer'),
            checkable=True,
            menu=bufferMenu,
            callback=self.drawBuffer,
            parent=self.iface.mainWindow()
        )
        icon_path = ':/plugins/qdrawEVT/resources/icon_Settings_EVT.png'
        self.add_action(
            icon_path,
            text=self.tr('Settings'),
            callback=self.showSettingsWindow,
            parent=self.iface.mainWindow()
        )

    def showAttributesTable(self, name):

        tab = AttributesTable(name)

        # Pour que la fenêtre reste au premier plan de toutes les applications en cours
        tab.setWindowFlags(Qt.WindowStaysOnTopHint)

        layers = self.project.mapLayers().values()
        for layer in layers:
            try:
                if layer.type() == QgsMapLayer.VectorLayer and QgsProject.instance().layerTreeRoot().findLayer(
                        layer.id()).isVisible():

                    # Modification F Thévand
                    # pour prise en compte de la configuration du masquage des colonnes attributaires des couches
                    # et prise en compte des alias de colonnes.
                    # Travail sur la selection dans les couches concernées seulement

                    cells = layer.selectedFeatures()
                    if len(cells) != 0:
                        columns = layer.attributeTableConfig().columns()
                        fields_aliases = []
                        fields_name = []
                        for column in columns:
                            if not column.hidden:
                                if layer.attributeAlias(layer.fields().indexOf(column.name)):
                                    fields_aliases.append(layer.attributeAlias(layer.fields().indexOf(column.name)))
                                    fields_name.append(layer.attributeAlias(layer.fields().indexOf(column.name)))
                                else:
                                    fields_name.append(column.name)
                            fields_type = [column.type for column in columns if not column.hidden]
                            idx_visible = [layer.fields().indexOf(column.name) for column in columns if not column.hidden]
                            # idx_masked = [layer.fields().indexOf(column.name) for column in columns if column.hidden]

                        # Fin modification
                        # print('layer entrée addLayer : ' + str(layer))

                        tab.addLayer(layer, fields_name, fields_type, cells, idx_visible)

                        # Pour contrôle
                        # print("Couche " + layer.name())
                        # print("alias : " + str(fields_aliases))
                        # print("Longueur chaine alias : " + str(len(fields_aliases)))
            except:
                pass
        tab.loadingWindow.close()
        tab.show()
        tab.activateWindow();
        tab.showNormal();

        self.results.append(tab)

    def closeAttributesTable(self, tab):
        self.results.remove(tab)

    def testGroups(self):
        # mise en variable des groupes a gérer pour la sélection
        self.group_no_select = []
        for group in self.root.children():
            test = ''.join(x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test in lst_group_no_select:
                self.group_no_select.append(group)
        self.group_evt = []
        for group in self.root.children():
            test = ''.join(x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test in lst_group_evt:
                self.group_evt.append(group)
                self.group_no_select.append(group)
        self.group_drawing = []
        for group in self.root.children():
            test = ''.join(x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test in lst_group_drawing:
                self.group_drawing.append(group)
                self.group_no_select.append(group)
        if self.group_evt:
            self.evt = True
        else:
            self.evt = False

    def isEVT(self):
        layers_evt = []
        layers_group_drawing = []
        sortieEVT = False
        for group in self.root.children():
            test = ''.join(x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test in lst_group_evt:
                # Réinitialisation de l'analyse thématique des couches évènement
                if group:
                    for lyr in group.children():
                        layers_evt.append(self.project.mapLayersByName(lyr.name())[0])
                        # self.QgisV3LayerRandomColor(layer, form_wgt_libelle)
                        # iface.layerTreeView().refreshLayerSymbology(layer.name())
                # return True, layers_evt
                sortieEVT = True
                break

            # Code en prévision utilisation couche dessin
            # elif test in lst_group_drawing:
            #     if group:
            #         for lyr in group.children():
            #             layers_group_drawing.append(self.project.mapLayersByName(lyr.name())[0])
            #             # self.QgisV3LayerRandomColor(layer, form_wgt_libelle)
            #             # iface.layerTreeView().refreshLayerSymbology(layer.name())
            #     sortie_group_drawing = True

        if sortieEVT:
            return True, layers_evt
        else:
            return False, layers_evt

    def drawPoint(self):
        # Modification qdrawEVT
        print('self.isEVT() : ' + str(self.isEVT()))
        if self.isEVT() == None:
            self.msgisEVTNone()
            return
        elif self.isEVT()[0]:
            self.actions[1].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawPt_EVT'))
            self.actions[1].menu().actions()[0].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtXY_EVT'))
            self.actions[1].menu().actions()[1].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtDMS_EVT'))
        else:
            self.actions[1].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawPt'))
            self.actions[1].menu().actions()[0].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtXY'))
            self.actions[1].menu().actions()[1].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtDMS'))
        self.layerevtname = evtpnt
        self.actions[1].triggered.disconnect()
        self.actions[1].triggered.connect(self.drawPoint)
        self.actions[1].menu().actions()[0].triggered.disconnect()
        self.actions[1].menu().actions()[0].triggered.connect(self.drawXYPoint)
        self.actions[1].menu().actions()[1].triggered.disconnect()
        self.actions[1].menu().actions()[1].triggered.connect(self.drawDMSPoint)
        if self.tool:
            self.tool.reset()
        self.tool = DrawPoint(self.iface, self.settings.getColor())
        self.tool.setAction(self.actions[1])
        self.tool.selectionDone.connect(self.draw)
        self.iface.mapCanvas().setMapTool(self.tool)
        self.drawShape = 'point'
        self.toolname = 'drawPoint'
        self.resetSB()

    def drawText(self):
        if self.tool:
            self.tool.reset()
        self.tool = DrawPoint(self.iface, self.settings.getColor())
        self.tool.setAction(self.actions[0])
        self.tool.selectionDone.connect(self.draw)
        self.iface.mapCanvas().setMapTool(self.tool)
        self.drawShape = 'text'
        self.toolname = 'drawText'
        # Modification qdrawEVT
        self.layerevtname = None
        self.resetSB()

    def drawXYPoint(self):
        # Modification qdrawEVT
        self.layerevtname = evtpnt
        mc = self.iface.mapCanvas()
        ms = mc.mapSettings()
        # default for drawXYPoint data : WGS84 EPSG:4326
        crs = QgsCoordinateReferenceSystem(4326)
        ms.setDestinationCrs(crs)
        if self.isEVT() == None:
            self.msgisEVTNone()
            return
        elif self.isEVT()[0]:
            self.actions[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPt_EVT.png'))
            self.actions[1].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtXY_EVT.png'))
            self.actions[1].menu().actions()[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtDMS_EVT.png'))
        elif not self.isEVT()[0]:
            self.actions[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPt.png'))
            self.actions[1].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtXY.png'))
            self.actions[1].menu().actions()[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtDMS.png'))
        self.actions[1].menu().actions()[0].setText(
            self.tr('XY point drawing tool'))
        self.actions[1].menu().actions()[1].setText(
            self.tr('DMS point drawing tool'))
        self.actions[1].menu().actions()[0].triggered.disconnect()
        self.actions[1].menu().actions()[0].triggered.connect(self.drawXYPoint)
        self.actions[1].menu().actions()[1].triggered.disconnect()
        self.actions[1].menu().actions()[1].triggered.connect(self.drawDMSPoint)
        try:
            xytuple, ok = XYDialog().getPoint(ms.destinationCrs())
        except:
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr('Error'), self.tr('Saisie incorrecte ou clic sur Annuler'))
            return
        # print('xytuple : ' + str(xytuple))
        # print('crs : ' + str(crs))
        point = xytuple[0]
        ptOrigin = point
        if xytuple[1] != crs:
            crsSrc = xytuple[1] # projection choisie par l'utilisateur
        else:
            crsSrc = crs # projection définie par défaut dans drawXYPoint() qdrawEVT.py (4326)
        crsDest = QgsProject.instance().crs()
        crsTransform = QgsCoordinateTransform(crsSrc,crsDest, QgsProject.instance())
        # Transformation crsSrc -> crsDest
        point = crsTransform.transform(ptOrigin)
        # Remplacé pour utilisation de la projection du projet en cours
        # crs = QgsCoordinateReferenceSystem(2154)
        # Ligne de remplacement
        crs = QgsProject.instance().crs()
        ms.setDestinationCrs(crs)
        self.XYcrs = crs
        if ok:
            if point.x() == 0 and point.y() == 0:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    self.tr('Error'), self.tr('Invalid input !'))
                if self.tool:
                    self.tool.reset()
                self.tool = DrawPoint(self.iface, self.settings.getColor())
                self.tool.setAction(self.actions[1])
                self.tool.selectionDone.connect(self.drawPoint)
                self.iface.mapCanvas().setMapTool(self.tool)
                self.drawShape = 'point'
                self.toolname = 'drawPoint'
                self.resetSB()
                return
            else:
                self.drawPoint()
                self.tool.rb = QgsRubberBand(
                    self.iface.mapCanvas(), QgsWkbTypes.PointGeometry)
                self.tool.rb.addPoint(point)
                self.tool.rb.setColor(self.settings.getColor())
                self.tool.rb.setWidth(4)
                self.drawShape = 'XYpoint'
                print('self.tool.rb : ' + str(self.tool.rb))
                self.draw()
                mc.setCenter(point)
                mc.refresh()
#                # wait .5 seconds to simulate a flashing effect
#                QTimer.singleShot(500,self.resetSB)

    def drawDMSPoint(self):
        # Modification qdrawEVT
        mc = self.iface.mapCanvas()
        ms = mc.mapSettings()
        # Gestion du changement d'aspact de l'icone d'outil
        self.layerevtname = evtpnt
        if self.isEVT() == None:
            self.msgisEVTNone()
            return
        elif self.isEVT()[0]:
            self.actions[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPt_EVT.png'))
            self.actions[1].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtXY_EVT.png'))
            self.actions[1].menu().actions()[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtDMS_EVT.png'))
        elif not self.isEVT()[0]:
            self.actions[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPt.png'))
            self.actions[1].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtXY.png'))
            self.actions[1].menu().actions()[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtDMS.png'))
        self.actions[1].menu().actions()[0].setText(
            self.tr('XY point drawing tool'))
        self.actions[1].menu().actions()[1].setText(
            self.tr('DMS point drawing tool'))
        self.actions[1].menu().actions()[0].triggered.disconnect()
        self.actions[1].menu().actions()[0].triggered.connect(self.drawXYPoint)
        self.actions[1].menu().actions()[1].triggered.disconnect()
        self.actions[1].menu().actions()[1].triggered.connect(self.drawDMSPoint)

        point, ok = DMSDialog().getPoint()
        # default for drawDMSPoint data : WGS84 EPSG:4326
        crsSrc = QgsCoordinateReferenceSystem(4326)
        crsDest = QgsProject.instance().crs()
        ptOrigin = point
        crsTransform = QgsCoordinateTransform(crsSrc,crsDest, QgsProject.instance())
        # Transformation crsSrc -> crsDest
        point = crsTransform.transform(ptOrigin)
        crs = QgsProject.instance().crs()
        ms.setDestinationCrs(crs)
        self.XYcrs = crs

        if ok:
            if point.x() == 0 and point.y() == 0:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    self.tr('Error'), self.tr('Invalid input !'))
            else:
                self.drawPoint()
                self.tool.rb = QgsRubberBand(
                    self.iface.mapCanvas(), QgsWkbTypes.PointGeometry)
                self.tool.rb.setColor(self.settings.getColor())
                self.tool.rb.setWidth(3)
                self.tool.rb.addPoint(point)
                self.drawShape = 'XYpoint'
                self.draw()
                # centrer la carte sur le point
                mc.setCenter(point)
                mc.refresh()

    def drawLine(self):
        # Modification qdrawEVT
        if self.isEVT() == None:
            self.msgisEVTNone()
            return
        elif self.isEVT()[0]:
            self.actions[2].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawL_EVT'))
        else:
            self.actions[2].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawL'))
        self.layerevtname = evtlgn
        if self.tool:
            self.tool.reset()
        self.request = 'intersects'
        self.tool = DrawLine(self.iface, self.settings.getColor())
        self.tool.setAction(self.actions[2])
        self.tool.selectionDone.connect(self.draw)
        self.tool.move.connect(self.updateSB)
        self.iface.mapCanvas().setMapTool(self.tool)
        self.drawShape = 'line'
        self.toolname = 'drawLine'
        self.resetSB()

    def drawRect(self):
        # Modification qdrawEVT
        if self.isEVT() == None:
            self.msgisEVTNone()
            return
        elif self.isEVT()[0]:
            self.actions[3].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawR_EVT'))
        else:
            self.actions[3].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawR'))
        self.layerevtname = evtpol
        if self.tool:
            self.tool.reset()
        self.request = 'intersects'
        self.tool = DrawRect(self.iface, self.settings.getColor())
        self.tool.setAction(self.actions[3])
        self.tool.selectionDone.connect(self.draw)
        self.tool.move.connect(self.updateSB)
        self.iface.mapCanvas().setMapTool(self.tool)
        self.drawShape = 'polygon'
        self.toolname = 'drawRect'
        self.resetSB()

    def drawCircle(self):
        # Modification qdrawEVT
        if self.isEVT() == None:
            self.msgisEVTNone()
            return
        elif self.isEVT()[0]:
            self.actions[4].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawC_EVT'))
        else:
            self.actions[4].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawC'))
        self.layerevtname = evtpol

        if self.tool:
            self.tool.reset()
        self.request = 'intersects'
        self.tool = DrawCircle(self.iface, self.settings.getColor(), 40)
        self.tool.setAction(self.actions[4])
        self.tool.selectionDone.connect(self.draw)
        self.tool.move.connect(self.updateSB)
        self.iface.mapCanvas().setMapTool(self.tool)
        self.drawShape = 'polygon'
        self.toolname = 'drawCircle'
        self.resetSB()

    def drawPolygon(self):
        # Modification qdrawEVT
        if self.isEVT() == None:
            self.msgisEVTNone()
            return
        elif self.isEVT()[0]:
            self.actions[5].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawP_EVT'))
        else:
            self.actions[5].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_DrawP'))
        self.layerevtname = evtpol
        if self.tool:
            self.tool.reset()
        self.request = 'intersects'
        self.tool = DrawPolygon(self.iface, self.settings.getColor())
        self.tool.setAction(self.actions[5])
        self.tool.selectionDone.connect(self.draw)
        self.tool.move.connect(self.updateSB)
        self.iface.mapCanvas().setMapTool(self.tool)
        self.drawShape = 'polygon'
        self.toolname = 'drawPolygon'
        self.resetSB()

    def drawBuffer(self):
        self.layerevtname = evtpol
        self.bGeom = None
        if self.tool:
            self.tool.reset()
        self.request = 'intersects'
        self.tool = SelectPoint(self.iface, self.settings.getColor())
        if self.isEVT() == None:
            self.msgisEVTNone()
            return
        elif self.isEVT()[0]:
            self.actions[6].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawT_EVT.png'))
            self.actions[6].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawTP_EVT.png'))
            self.actions[6].setText(
                self.tr('Buffer drawing tool on the selected layer'))
            self.actions[6].menu().actions()[0].setText(
                self.tr('Polygon buffer drawing tool on the selected layer'))
        elif not self.isEVT()[0]:
            self.actions[6].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawT.png'))
            self.actions[6].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawTP.png'))
            self.actions[6].setText(
                self.tr('Buffer drawing tool on the selected layer'))
            self.actions[6].menu().actions()[0].setText(
                self.tr('Polygon buffer drawing tool on the selected layer'))
        self.actions[6].triggered.disconnect()
        self.actions[6].triggered.connect(self.drawBuffer)
        self.actions[6].menu().actions()[0].triggered.disconnect()
        self.actions[6].menu().actions()[0].triggered.connect(self.drawPolygonBuffer)
        self.tool.setAction(self.actions[6])
        self.tool.select.connect(self.selectBuffer)
        self.tool.selectionDone.connect(self.draw)
        self.iface.mapCanvas().setMapTool(self.tool)
        self.drawShape = 'polygon'
        self.toolname = 'drawBuffer'
        self.resetSB()

    def drawPolygonBuffer(self):
        self.layerevtname = evtpol
        self.bGeom = None
        if self.tool:
            self.tool.reset()
        self.request = 'intersects'
        self.tool = DrawPolygon(self.iface, self.settings.getColor())
        if self.isEVT() == None:
            self.msgisEVTNone()
            return
        elif self.isEVT()[0]:
            self.actions[6].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawTP_EVT.png'))
            self.actions[6].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawT_EVT.png'))
            self.actions[6].setText(
                self.tr('Polygon buffer drawing tool on the selected layer'))
            self.actions[6].menu().actions()[0].setText(
                self.tr('Buffer drawing tool on the selected layer'))
        elif not self.isEVT()[0]:
            self.actions[6].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawTP.png'))
            self.actions[6].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawT.png'))
            self.actions[6].setText(
                self.tr('Polygon buffer drawing tool on the selected layer'))
            self.actions[6].menu().actions()[0].setText(
                self.tr('Buffer drawing tool on the selected layer'))
        self.actions[6].triggered.disconnect()
        self.actions[6].triggered.connect(self.drawPolygonBuffer)
        self.actions[6].menu().actions()[0].triggered.disconnect()
        self.actions[6].menu().actions()[0].triggered.connect(self.drawBuffer)
        self.tool.setAction(self.actions[6])
        self.tool.selectionDone.connect(self.selectBuffer)
        self.iface.mapCanvas().setMapTool(self.tool)
        self.drawShape = 'polygon'
        self.toolname = 'drawBuffer'
        self.resetSB()

    def showSettingsWindow(self):
        self.settings.settingsChanged.connect(self.settingsChangedSlot)
        self.settings.show()

    # triggered when a setting is changed
    def settingsChangedSlot(self):
        if self.tool:
            self.tool.rb.setColor(self.settings.getColor())

    def resetSB(self):
        message = {
            'drawText': 'Left click to place a text.',
            'drawPoint': 'Left click to place a point.',
            'drawLine': 'Left click to place points. Right click to confirm.',
            'drawRect': 'Maintain the left click to draw a rectangle.',
            'drawCircle': 'Maintain the left click to draw a circle. \
Simple Left click to give a perimeter.',
            'drawPolygon': 'Left click to place points. Right click to \
confirm.',
            'drawBuffer': 'Select a vector layer in the Layer Tree, \
then select an entity on the map.'
        }
        self.sb.showMessage(self.tr(message[self.toolname]))

    def updateSB(self):
        g = self.geomTransform(
            self.tool.rb.asGeometry(),
            self.iface.mapCanvas().mapSettings().destinationCrs(), QgsProject.instance().crs())
        if self.toolname == 'drawLine':
            if g.length() >= 0:
                self.sb.showMessage(
                    self.tr('Length') + ': ' + str("%.2f" % g.length()) + " m")
            else:
                self.sb.showMessage(self.tr('Length')+': '+"0 m")
        else:
            if g.area() >= 0:
                self.sb.showMessage(
                    self.tr('Area')+': '+str("%.2f" % g.area())+" m"+u'²')
            else:
                self.sb.showMessage(self.tr('Area')+': '+"0 m"+u'²')
        self.iface.mapCanvas().mapSettings().destinationCrs().authid()

    def geomTransform(self, geom, crs_orig, crs_dest):
        g = QgsGeometry(geom)
        crsTransform = QgsCoordinateTransform(
            crs_orig, crs_dest, QgsCoordinateTransformContext())  # which context ?
        g.transform(crsTransform)
        return g

    def selectBuffer(self):
        rb = self.tool.rb
        if isinstance(self.tool, DrawPolygon):
            rbSelect = self.tool.rb
        else:
            rbSelect = self.tool.rbSelect
        layer = self.iface.layerTreeView().currentLayer()
        if layer is not None and layer.type() == QgsMapLayer.VectorLayer \
                and self.iface.layerTreeView().currentNode().isVisible():
            # rubberband reprojection
            g = self.geomTransform(
                rbSelect.asGeometry(),
                self.iface.mapCanvas().mapSettings().destinationCrs(),
                layer.crs())
            features = layer.getFeatures(QgsFeatureRequest(g.boundingBox()))
            rbGeom = []
            for feature in features:
                geom = feature.geometry()
                try:
                    if g.intersects(geom):
                        rbGeom.append(feature.geometry())
                except:
                    # there's an error but it intersects
                    # fix_print_with_import
                    # print('error with '+layer.name()+' on '+str(feature.id()))
                    rbGeom.append(feature.geometry())
            if len(rbGeom) > 0:
                for geometry in rbGeom:
                    if rbGeom[0].combine(geometry) is not None:
                        if self.bGeom is None:
                            self.bGeom = geometry
                        else:
                            self.bGeom = self.bGeom.combine(geometry)
                rb.setToGeometry(self.bGeom, layer)
        if isinstance(self.tool, DrawPolygon):
            self.draw()

    def draw(self):
        test_draw = None
        rb = self.tool.rb
        g = rb.asGeometry()
        # Modification qdrawEVT
        mc = iface.mapCanvas()
        mc.setCenter(g.centroid().asPoint())
        if self.drawShape in ['point', 'XYpoint', 'Text']:
            mc.zoomScale(5000)
        else:
            mc.zoomToFeatureExtent(g.boundingBox())

        ok = True
        warning = False
        errBuffer_noAtt = False
        errBuffer_Vertices = False

        self.layer = self.iface.layerTreeView().currentLayer()
        if self.toolname == 'drawBuffer':
            if self.bGeom is None:
                warning = True
                errBuffer_noAtt = True
            else:
                perim, ok = QInputDialog.getDouble(
                    self.iface.mainWindow(), self.tr('Perimeter'),
                    self.tr('Give a perimeter in m:')
                    + '\n' + self.tr('(works only with metric crs)'),
                    min=0)
                g = self.bGeom.buffer(perim, 40)
                rb.setToGeometry(g, QgsVectorLayer(
                    "Polygon?crs=" + self.layer.crs().authid(), "", "memory"))
                if g.length() == 0 and ok:
                    warning = True
                    errBuffer_Vertices = True

        if self.toolname == 'drawCopies':
            if g.length() < 0:
                warning = True
                errBuffer_noAtt = True

        name_draw = ''
        add = False
        self.testGroups()
        if ok and not warning:
            ok = True
            self.index = 0
            self.layers = []
            # print('self.toolname : ' + str(self.toolname))
            while not name_draw.strip() and not add and ok:
                # Lancement de la boite de dialogue avec passage de la définition de self.drawShape (gtype en sortie)
                dlg = QDrawLayerDialog(self.iface, self.drawShape, self.layerevtname, self.evt)
                name_draw, add, self.index, self.layers, ok = dlg.getName(self.iface, self.drawShape, self.layerevtname, self.evt)
        # print('self.evt : ' + str(self.evt))
        # print('layers : ' + str(self.layers))
        # print('ok : ' + str(ok))
        # print('name_draw : ' + str(name_draw))
        # print('add : ' + str(add))
        # print('self.index : ' + str(self.index))
        # print('self.layerevtname : ' + str(self.layerevtname))
        # print('self.drawShape : ' + str(self.drawShape))

        # print('warning : ' + str(warning))

        if ok and not warning and self.evt:
            if self.drawShape == 'text':
                if self.root.findGroup(self.tr('Drawings')) is None:
                    self.root.insertChildNode(0, QgsLayerTreeGroup(self.tr('Drawings')))
                group = self.root.findGroup(self.tr('Drawings'))
                test_draw = 1
                self.layer = QgsVectorLayer(
                    "Point?crs=" + self.iface.mapCanvas().mapSettings().destinationCrs().authid() + "&field=" + self.tr(
                        'Drawings') + ":string(255)", name_draw, "memory")
                g = g.centroid()  # force geometry as point
                # self.layer.beginEditCommand("Memory layer")
                self.layer.startEditing()
                symbols = self.layer.renderer().symbols(QgsRenderContext())  # todo which context ?
                symbols[0].setColor(self.settings.getColor())
                self.feature = QgsFeature(self.layer.fields())
                self.feature.setGeometry(g)
                self.feature.setAttributes([name_draw])
                self.layer.dataProvider().addFeatures([self.feature])
                self.featureid = self.feature.id()
                # ajout dessin de texte
                symbols[0].setSize(0)
                layer_settings = QgsPalLayerSettings()
                text_format = QgsTextFormat()
                text_format.setFont(self.settings.getFont())
                text_format.setSize(self.settings.getFont().pointSize())
                text_format.setColor(self.settings.getColorFont())
                layer_settings.setFormat(text_format)
                layer_settings.fieldName = "Dessins"
                layer_settings.placement = QgsPalLayerSettings.OverPoint
                layer_settings = QgsVectorLayerSimpleLabeling(layer_settings)
                self.layer.setLabelsEnabled(True)
                self.layer.setLabeling(layer_settings)
                # self.layer.commitChanges()
                if not add:
                    self.project.addMapLayer(self.layer, False)
                    group.insertLayer(0, self.layer)
                self.iface.layerTreeView().refreshLayerSymbology(self.layer.id())
                self.iface.mapCanvas().refresh()
            else:
                # ajout point, ligne ou polygone
                self.layer = self.project.mapLayersByName(self.layerevtname)[0]
                self.iface.setActiveLayer(self.layer)
                self.layer.setReadOnly(False)
                self.layer.startEditing()
                self.features = QgsFeature()
                # Ajout de la géométrie dans la couche
                self.features.setGeometry(g)
                # Récupération de la structure de la couche
                self.features.setFields(self.layer.fields())  # retrieve the fields from layer and set them to the feature
                # print('layer.fields().count() = ' + str(layer.fields().count()))
                # Récupération du nom de l'utilisateur
                self.features.setAttribute(form_wgt_utilisatr, os.environ.get("USERNAME"))
                # Test du type pour inscription des données dimentionnelles adaptées
                if self.drawShape in ['point', 'XYpoint']:
                    # Transformation de la coordonnée en EPSG 4326
                    crsSrc = QgsProject.instance().crs()  # L93
                    crsDest = QgsCoordinateReferenceSystem(4326)  # WGS 84
                    xform1 = QgsCoordinateTransform(crsSrc, crsDest, self.project)
                    geom = g.centroid().asPoint()
                    # Transformation crsSrc -> crsDest
                    pt1 = xform1.transform(geom)
                    x1, y1 = pt1.x(), pt1.y()
                    # Inscription en donnée attributaire
                    self.features.setAttribute(form_wgt_x_gps, round(x1, 6))
                    self.features.setAttribute(form_wgt_y_gps, round(y1, 6))
                elif self.drawShape == 'line':
                    self.features.setAttribute(form_wgt_longueur, int(round(g.length(),0)))
                elif self.drawShape == 'polygon':
                    self.features.setAttribute(form_wgt_surface, int(round(g.area(), -2)))
                # Ouverture du formulaire (enregistrement de l'objet si click sur ok)
                # avec possibilité d'attribution de focus (voir source)
                form = self.iface.getFeatureForm(self.layer, self.features)
                # Mise du formulaire en mode création
                form.setMode(QgsAttributeEditorContext.AddFeatureMode)
                # Inscription du nom de l'évènement dans le formulaire (A réactiver en cas de besoin)
                if form_wgt_libelle in lst_form_wgt:
                    libelle = form.findChild(QLineEdit, form_wgt_libelle)
                    libelle.setText(name_draw)
                # if form_wgt_date in lst_form_wgt:
                #     date = form.findChild(QDateTimeEdit, form_wgt_date)
                # if form_wgt_h_creation in lst_form_wgt:
                #     h_creation = form.findChild(QDateTimeEdit, form_wgt_h_creation)
                # if form_wgt_utilisatr in lst_form_wgt:
                #     utilisateur = form.findChild(QLineEdit, form_wgt_utilisatr)
                # if self.drawShape in ['point', 'XYpoint']:
                #     if form_wgt_x_gps in lst_form_wgt:
                #         x_gps = form.findChild(QLineEdit, form_wgt_x_gps)
                #     if form_wgt_y_gps in lst_form_wgt:
                #         y_gps = form.findChild(QLineEdit, form_wgt_y_gps)
                # elif self.drawShape == 'line':
                #     if form_wgt_longueur in lst_form_wgt:
                #         longueur = form.findChild(QLineEdit, form_wgt_longueur)
                # elif self.drawShape == 'polygon':
                #     if form_wgt_surface in lst_form_wgt:
                #         surface = form.findChild(QLineEdit, form_wgt_surface)
                # Attribution du focus à l'item "Source"
                if form_wgt_source in lst_form_wgt:
                    source = form.findChild(QLineEdit, form_wgt_source)
                    source.setFocus(True)
                # if form_wgt_h_constat in lst_form_wgt:
                #     constat = form.findChild(QDateTimeEdit, form_wgt_h_constat)
                # if form_wgt_remarques in lst_form_wgt:
                #     remarques = form.findChild(QPlainTextEdit, form_wgt_remarques)
                test_draw = form.exec_()
                if test_draw == 1:
                    # print("test_draw = OK")
                    self.QgisV3LayerRandomColor(self.layer, form_wgt_libelle)
                    self.layer.commitChanges()
                    self.layer.setReadOnly(True)
                else:
                    self.layer.rollBack()
                    # self.layer.commitChanges()
                    self.layer.setReadOnly(True)

        if ok and not warning and not self.evt:
            print('Pas de groupe évènement')
            if self.root.findGroup(self.tr('Drawings')) is None:
                self.root.insertChildNode(0, QgsLayerTreeGroup(self.tr('Drawings')))
            group = self.root.findGroup(self.tr('Drawings'))
            test_draw = 1
            if add:
                self.layer = self.layers[self.index]
                if self.drawShape in ['point', 'XYpoint', 'text']:
                    g = g.centroid()
            else:
                if self.drawShape in ['point', 'text']:
                    self.layer = QgsVectorLayer("Point?crs="+self.iface.mapCanvas().mapSettings().destinationCrs().authid()+"&field="+self.tr('Drawings')+":string(255)", name_draw, "memory")
                    g = g.centroid()  # force geometry as point
                elif self.drawShape == 'XYpoint':
                    self.layer = QgsVectorLayer("Point?crs="+self.XYcrs.authid()+"&field="+self.tr('Drawings')+":string(255)", name_draw, "memory")
                    g = g.centroid()
                elif self.drawShape == 'line':
                    self.layer = QgsVectorLayer("LineString?crs="+self.iface.mapCanvas().mapSettings().destinationCrs().authid()+"&field="+self.tr('Drawings')+":string(255)", name_draw, "memory")
                    # fix_print_with_import
                else:
                    self.layer = QgsVectorLayer("Polygon?crs="+self.iface.mapCanvas().mapSettings().destinationCrs().authid()+"&field="+self.tr('Drawings')+":string(255)", name_draw, "memory")
            # self.layer.beginEditCommand("Memory layer")
            self.layer.startEditing()
            symbols = self.layer.renderer().symbols(QgsRenderContext())  # todo which context ?
            symbols[0].setColor(self.settings.getColor())
            self.feature = QgsFeature(self.layer.fields())
            self.feature.setGeometry(g)
            self.feature.setAttributes([name_draw])
            self.layer.dataProvider().addFeatures([self.feature])
            self.featureid = self.feature.id()
            # ajout dessin de texte
            if self.drawShape == 'text':
                print('Pas de groupe EVT, écriture texte')
                symbols[0].setSize(0)
                layer_settings  = QgsPalLayerSettings()
                text_format = QgsTextFormat()
                text_format.setFont(self.settings.getFont())
                text_format.setSize(self.settings.getFont().pointSize())
                text_format.setColor(self.settings.getColorFont())
                layer_settings.setFormat(text_format)
                layer_settings.fieldName = "Dessins"
                layer_settings.placement = QgsPalLayerSettings.OverPoint
                layer_settings = QgsVectorLayerSimpleLabeling(layer_settings)
                self.layer.setLabelsEnabled(True)
                self.layer.setLabeling(layer_settings)
                self.layer.renderer().symbol().symbolLayer(0).setShape(QgsSimpleMarkerSymbolLayerBase.Star)
                self.layer.triggerRepaint()
                self.iface.layerTreeView().refreshLayerSymbology(self.layer.id())
                self.iface.mapCanvas().refresh()

            # self.layer.commitChanges()
            if not add:
                self.project.addMapLayer(self.layer, False)
                group.insertLayer(0, self.layer)
            self.iface.layerTreeView().refreshLayerSymbology(self.layer.id())
            self.iface.mapCanvas().refresh()
            # self.layer.commitChanges()

            # self.testGroups()

            #     pjt = QgsProject.instance()
            #     pjt.addMapLayer(layer, False)
            #     if pjt.layerTreeRoot().findGroup(self.tr('Drawings')) is None:
            #         pjt.layerTreeRoot().insertChildNode(
            #             0, QgsLayerTreeGroup(self.tr('Drawings')))
            #     group = pjt.layerTreeRoot().findGroup(
            #         self.tr('Drawings'))
            #     group.insertLayer(0, layer)
            # self.iface.layerTreeView().refreshLayerSymbology(layer.id())
            # self.iface.mapCanvas().refresh()

        # Modification pour ajout de la sélection des couches intersectant
        # une ligne ou un polygone, avec cochage automatique du groupe enjeux
        if self.drawShape not in ['point', 'XYpoint', 'text'] and test_draw == 1:
            # Définition du choix d'une sélection en intersection
            print('Texte du nom : ' + str(name_draw))
            box = QMessageBox()
            box.setWindowTitle(self.tr('Choosing a selection'))
            box.setIcon(QMessageBox.Information)
            box.setText(name_draw + self.tr(" drawn. Make a selection in its grip?") + '\n\n' + self.tr('WARNING! In the layers panel,') + '\n' + self.tr('check WITHOUT OPENING the group to place in the selection.') + '\n')
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.Yes)
            buttonYes = box.button(QMessageBox.Yes)
            # buttonYes.setText(self.tr('Continue'))
            buttonNo = box.button(QMessageBox.No)
            # buttonNo.setText(self.tr('Cancel'))
            # Pour que la fenêtre reste au premier plan de toutes les applications en cours
            box.setWindowModality(Qt.WindowModal)
            box.setWindowFlags(Qt.WindowStaysOnTopHint)
            box.exec_()

            self.groupes_coches = []
            test_coche = self.verifCocheGroupes()
            # print('self.groupes_coches : ' + str(self.groupes_coches))
            # print('self.group_no_select : ' + str(self.group_no_select))
            # print('test_coche : ' + str(test_coche))
            if box.clickedButton() == buttonYes:
                if test_coche:
                    warning = False
                    ok = True
                    active = False
                    errBuffer_noAtt = False
                    errBuffer_Vertices = False
                    buffer_geom = None
                    buffer_geom_crs = None

                    for group in self.root.children():
                        # Test couvrant les cas d'écriture avec accent et/ou majuscule en entête (Mettre le mot à
                        # rechercher en majuscules)
                        if group in self.group_no_select:
                            group.setItemVisibilityChecked(False)
                        if group in self.group_drawing:
                            group.setItemVisibilityCheckedRecursive(False)


                    # Nous vérifions s'il y a au moins une couche visible
                    for layer in QgsProject().instance().mapLayers().values():
                        # print('layer : ' + str(layer))
                        # print('layer.type() : ' + str(layer.type()))
                        try:
                            if self.root.findLayer(layer.id()).isVisible():
                                warning = False
                                active = True
                                break
                        except:
                            pass

                    # Création de buffer sur la couche courante
                    if self.request == 'buffer':
                        layer = self.iface.layerTreeView().currentLayer()
                        if layer is not None and layer.type() == QgsMapLayer.VectorLayer and QgsProject.instance().layerTreeRoot().findLayer(layer.id()).isVisible():
                            # rubberband reprojection
                            g = self.geomTransform(rb.asGeometry(), self.iface.mapCanvas().mapSettings().destinationCrs(),layer.crs())
                            features = layer.getFeatures(QgsFeatureRequest(g.boundingBox()))
                            style = layer.renderer()
                            rbGeom = []
                            for feature in features:
                                geom = feature.geometry()
                                if g.intersects(geom):
                                    rbGeom.append(QgsGeometry(feature.geometry()))
                            if len(rbGeom) > 0:
                                union_geoms = rbGeom[0]
                                for geometry in rbGeom:
                                    if union_geoms.combine(geometry) is not None:
                                        union_geoms = union_geoms.combine(geometry)

                                rb.setToGeometry(union_geoms, layer)

                                perim, ok = QInputDialog.getDouble(self.iface.mainWindow(), self.tr('Perimeter'),
                                                                   self.tr('Give a perimeter in m:') + '\n' + self.tr(
                                                                       '(works only with metric crs)'), min=0)
                                buffer_geom_crs = layer.crs()
                                buffer_geom = union_geoms.buffer(perim, 40)
                                rb.setToGeometry(buffer_geom, QgsVectorLayer("Polygon?crs=" + layer.crs().authid(), "", "memory"))
                                rb.setRenderer(style)
                                if buffer_geom.length == 0:
                                    warning = True
                                    errBuffer_Vertices = True
                            else:
                                warning = True
                                errBuffer_noAtt = True
                        else:
                            warning = True
                    if len(QgsProject().instance().mapLayers().values()) > 0 and warning == False and ok:
                        self.loadingWindow.show()
                        self.loadingWindow.activateWindow()
                        self.loadingWindow.showNormal()
                        for layer in QgsProject().instance().mapLayers().values():
                            try:
                                if layer.type() == QgsMapLayer.VectorLayer and QgsProject.instance().layerTreeRoot().findLayer(layer.id()).isVisible():
                                    if self.request == 'buffer' and self.iface.layerTreeView().currentLayer() == layer:
                                        layer.selectByIds([])
                                        continue
                                    self.loadingWindow.reset()
                                    self.loadingWindow.setWindowTitle(self.tr('Selecting...'))
                                    self.loadingWindow.setLabelText(layer.name())

                                    # rubberband reprojection
                                    if self.request == 'buffer':
                                        if buffer_geom_crs.authid() != layer.crs().authid():
                                            g = self.geomTransform(buffer_geom, buffer_geom_crs, layer.crs())
                                        else:
                                            g = self.geomTransform(buffer_geom, buffer_geom_crs, layer.crs())
                                    else:
                                        g = self.geomTransform(rb.asGeometry(), self.iface.mapCanvas().mapSettings().destinationCrs(),
                                                               layer.crs())

                                    feat_id = []
                                    features = layer.getFeatures(QgsFeatureRequest(g.boundingBox()))
                                    count = layer.getFeatures(QgsFeatureRequest(g.boundingBox()))

                                    nbfeatures = 0
                                    for feature in count:
                                        nbfeatures += 1

                                    # Select attributes intersecting with the rubberband
                                    index = 0
                                    for feature in features:
                                        geom = feature.geometry()
                                        try:
                                            if g.intersects(geom):
                                                feat_id.append(feature.id())
                                        except:
                                            # There's an error but it intersects
                                            # print('error with ' + layer.name() + ' on ' + str(feature.id()))
                                            feat_id.append(feature.id())
                                        index += 1
                                        self.loadingWindow.setValue(int((float(index) / nbfeatures) * 100))
                                        if self.loadingWindow.wasCanceled():
                                            self.loadingWindow.reset()
                                            break
                                        QApplication.processEvents()
                                    layer.selectByIds(feat_id)
                            except:
                                pass

                        self.loadingWindow.close()
                        self.showAttributesTable(name_draw)
                    else:
                        # Display a warning in the message bar depending of the error
                        if errBuffer_noAtt:
                            self.iface.messageBar().pushWarning(self.tr('Warning'),
                                                                self.tr("You didn't click on a layer's attribute !"))
                        elif errBuffer_Vertices:
                            self.iface.messageBar().pushWarning(self.tr('Warning'), self.tr(
                                "You must give a non-null value for a point's or line's perimeter!"))
                        else:
                            self.iface.messageBar().pushWarning(self.tr('Warning'), self.tr(
                                'There is no selected layer, or it is not vector nor visible!'))
                        for layer in self.isEVT()[1]:
                            layer.rollback()
                    if not ok:
                        pass
                elif not test_coche:
                    if self.isEVT() == None:
                        self.msgisEVTNone()
                        return
                    elif self.isEVT()[0]:
                        self.layer.rollBack()
                        # self.layer.commitChanges()
                    else:
                        self.project.removeMapLayer(self.layer.id())
                    self.msgForgottenTick()
            elif box.clickedButton() == buttonNo:
                pass
        else:
            pass
        if self.isEVT() == None:
            self.msgisEVTNone()
            return
        elif self.isEVT()[0] and ok:
            # for layer in self.isEVT()[1]:
            if self.layer is None:
                self.msgNoSelect()
                return
            self.QgisV3LayerRandomColor(self.layer, form_wgt_libelle)
            self.layer.setReadOnly(True)
            try:
                for couche in self.groupes_coches:
                    couche.setItemVisibilityChecked(False)
                for group in self.group_no_select:
                    group.setItemVisibilityChecked(True)
                for group in self.group_drawing:
                    group.setItemVisibilityCheckedRecursive(True)
            except:
                pass
        elif not self.isEVT()[0]:
            for layer in self.isEVT()[1]:
                self.QgisV3LayerRandomColor(layer, self.tr('Drawings'))
            for group in self.group_drawing:
                group.setItemVisibilityCheckedRecursive(True)
        if str(self.groupes_coches) == 'None':
            return
        try:
            self.layer.commitChanges()
        except:
            pass
        self.tool.reset()
        self.resetSB()
        self.bGeom = None

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
                symbol.setWidth(2)
            symbol.setOpacity(0.4)

            # Couleurs aléatoires, le dernier paramètre règle le niveau de transparence (de 0 à 100%) Impose
            # l'importation de random layer_style = {} layer_style['color'] = '%d, %d, %d' % (random.randrange(0,
            # 256), random.randrange(0, 256), random.randrange(0, 256)) layer_style['outline'] = '#000000'
            # symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style) # replace default symbol layer with the
            # configured one if symbol_layer is not None: symbol.changeSymbolLayer(0, symbol_layer)

            # Couleur rouge sur tous les objets
            symbol.setColor(QColor(255, 0, 0))

            # create renderer object
            category = QgsRendererCategory(unique_value, symbol, str(unique_value))
            # entry for the list of category items
            categories.append(category)
        # Création du rendu de l'objet (on ne fais rien si c'est un objet texte)
        if self.drawShape != 'text':
            renderer = QgsCategorizedSymbolRenderer(fieldName, categories)
            # assign the created renderer to the layer
            if renderer is not None:
                layer.setRenderer(renderer)
        layer.triggerRepaint()

    def verifCocheGroupes(self):
        for group in self.root.children():
            # Test couvrant les cas d'écriture avec accent et/ou majuscule en entête (Le résultat du test est un mot
            # en majuscules et sans espaces)
            # test = ''.join(x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if group not in self.group_no_select and group not in self.group_drawing:
                if isinstance(group, QgsLayerTreeGroup):
                    coche = self.root.findGroup(str(group.name()))
                elif isinstance(group, QgsLayerTreeLayer):
                    lyr = self.project.mapLayersByName(group.name())[0]
                    coche = self.root.findLayer(lyr)
                if coche.isVisible():
                    self.groupes_coches.append(group)
        if self.groupes_coches:
            return True
        else:
            return False

    def msgisEVTNone(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setWindowTitle(self.tr("WARNING!"))
        msgBox.setText(self.tr("Command not operational, empty project"))
        msgBox.setStandardButtons(QMessageBox.Yes)
        msgBox.setDefaultButton(QMessageBox.Yes)
        buttonYes = msgBox.button(QMessageBox.Yes)
        buttonYes.setText(self.tr('Start again'))
        # Pour que la fenêtre reste au premier plan de toutes les applications en cours
        msgBox.setWindowModality(Qt.WindowModal)
        msgBox.setWindowFlags(Qt.WindowStaysOnTopHint)
        returnValue = msgBox.exec()
        if returnValue == buttonYes:
            # print('OK clicked')
            pass

    def msgForgottenTick(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setWindowTitle(self.tr("WARNING!"))
        msgBox.setText(self.tr("No layer, no group are checked. Start again"))
        msgBox.setStandardButtons(QMessageBox.Yes)
        msgBox.setDefaultButton(QMessageBox.Yes)
        buttonYes = msgBox.button(QMessageBox.Yes)
        buttonYes.setText(self.tr('Start again'))
        # Pour que la fenêtre reste au premier plan de toutes les applications en cours
        msgBox.setWindowModality(Qt.WindowModal)
        msgBox.setWindowFlags(Qt.WindowStaysOnTopHint)
        returnValue = msgBox.exec()
        if returnValue == buttonYes:
            # print('OK clicked')
            pass

    def msgForgottenPolygon(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle(self.tr("WARNING!"))
        # msgBox.setText(self.tr("Selection not possible. the checked layer is not a polygon."))
        msgBox.setText(self.tr("Sélection impossible.  la couche cochée n'est pas un polygone."))
        msgBox.setStandardButtons(QMessageBox.Yes)
        msgBox.setDefaultButton(QMessageBox.Yes)
        buttonYes = msgBox.button(QMessageBox.Yes)
        buttonYes.setText(self.tr('Start again'))
        # Pour que la fenêtre reste au premier plan de toutes les applications en cours
        msgBox.setWindowModality(Qt.WindowModal)
        msgBox.setWindowFlags(Qt.WindowStaysOnTopHint)
        returnValue = msgBox.exec()
        if returnValue == buttonYes:
            # print('OK clicked')
            pass

    def msgNoSelect(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle(self.tr("WARNING!"))
        # msgBox.setText(self.tr("Selection not possible. No layers are selected in the Layer Manager."))
        msgBox.setText(self.tr("Sélection impossible.  Aucune couche n'est sélectionnée dans le gestionnaire de couches."))
        msgBox.setStandardButtons(QMessageBox.Yes)
        msgBox.setDefaultButton(QMessageBox.Yes)
        buttonYes = msgBox.button(QMessageBox.Yes)
        buttonYes.setText(self.tr('Start again'))
        # Pour que la fenêtre reste au premier plan de toutes les applications en cours
        msgBox.setWindowModality(Qt.WindowModal)
        msgBox.setWindowFlags(Qt.WindowStaysOnTopHint)
        returnValue = msgBox.exec()
        if returnValue == buttonYes:
            # print('OK clicked')
            pass

