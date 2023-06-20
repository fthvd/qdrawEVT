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

from .qdrawlayerdialogEVT import QDrawLayerDialog

from datetime import datetime, date, time

import os, unicodedata, random

from . import resources

# # Obtenir l'instance du projet en cours
project = QgsProject.instance()
# Root du projet en cours
root = project.layerTreeRoot()
# minse en variable du groupe Enjeux pour cochage/décochage avec la commande groupe_enjeux.setItemVisibilityCheckedRecursive(True/False)
# groupe_enjeux = root.findGroup('Enjeux')

# Test existance du groupe Evènements avec suppression des espaces et des accents dans le nom du groupe testé
evt = False
groupevt = False
for group in root.children():
    test = ''.join(
        x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
    if test == 'EVENEMENTS':
        evt = True
        groupevt = group

# Inscrire ici le nom des couches evenement et les noms de colonnes attributaires
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

#Fonction de reconstruction du chemin absolu vers la ressource image ou autre fichier
def resolve(name, basepath=None):
  if not basepath:
    basepath = os.path.dirname(os.path.realpath(__file__))
  return os.path.join(basepath, name)

class QdrawEVT(object):
    def __init__(self, iface):

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
        # minse en variable du groupe Enjeux pour cochage/décochage avec la commande groupe_enjeux.setItemVisibilityCheckedRecursive(True/False)
        for group in self.root.children():
            # Test couvrant les cas d'écriture avec accent et/ou majuscule en entête (Mettre le mot à rechercher en majuscules)
            test = ''.join(x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test == 'ENJEUX':
                self.groupe_enjeux = self.root.findGroup('Enjeux')

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
            self.tr('Polygon buffer drawing tool on the selected layer'),
            bufferMenu)
        polygonBufferAction.triggered.connect(self.drawPolygonBuffer)
        bufferMenu.addAction(polygonBufferAction)
        icon_path = ':/plugins/qdrawEVT/resources/icon_DrawT_EVT.png'
        self.add_action(
            icon_path,
            text=self.tr('Buffer drawing tool on the selected layer'),
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

        tab = AttributesTable(self.iface, name)

        # Pour que la fenêtre reste au premier plan de toutes les applications en cours
        tab.setWindowFlags(Qt.WindowStaysOnTopHint)

        layers = QgsProject().instance().mapLayers().values()
        for layer in layers:
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

                    tab.addLayer(layer, fields_name, fields_type, cells, idx_visible)

                    # Pour contrôle
                    # print("Couche " + layer.name())
                    # print("alias : " + str(fields_aliases))
                    # print("Longueur chaine alias : " + str(len(fields_aliases)))

        tab.loadingWindow.close()
        tab.show()
        tab.activateWindow();
        tab.showNormal();

        self.results.append(tab)

    def closeAttributesTable(self, tab):
        self.results.remove(tab)

    def isEVT(self):
        # # Obtenir l'instance du projet en cours
        # self.project = QgsProject.instance()
        # # Root du projet en cours
        # self.root = self.project.layerTreeRoot()
        # Test existance du groupe Evènements avec suppression des espaces et des accents dans le nom du groupe testé
        self.evt = False
        self.groupevt = False
        for group in self.root.children():
            test = ''.join(
                x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test == 'EVENEMENTS':
                return True

    def drawPoint(self):
        # Modification qdrawEVT
        if self.isEVT():
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
        if self.isEVT():
            self.actions[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPt_EVT.png'))
            self.actions[1].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtXY_EVT.png'))
            self.actions[1].menu().actions()[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtDMS_EVT.png'))
        elif not self.isEVT():
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
            tuple, ok = XYDialog().getPoint(ms.destinationCrs())
        except:
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr('Error'), self.tr('Saisie incorrecte ou clic sur Annuler'))
            return
        point = tuple[0]
        ptOrigin = point
        crsSrc = crs # projection définie dans drawXYPoint() qdrawEVT.py (WGS84)
        crsDest = QgsCoordinateReferenceSystem("EPSG:2154")
        crsTransform = QgsCoordinateTransform(crsSrc,crsDest, QgsProject.instance())
        # Transformation crsSrc -> crsDest
        point = crsTransform.transform(ptOrigin)
        crs = QgsCoordinateReferenceSystem(2154)
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
                self.draw()
                mc.setCenter(point)
                mc.refresh()
#                # wait .5 seconds to simulate a flashing effect
#                QTimer.singleShot(500,self.resetSB)

    def drawDMSPoint(self):
        # Modification qdrawEVT
        mc = self.iface.mapCanvas()
        ms = mc.mapSettings()
        self.layerevtname = evtpnt
        if self.isEVT():
            self.actions[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPt_EVT.png'))
            self.actions[1].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtXY_EVT.png'))
            self.actions[1].menu().actions()[1].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawPtDMS_EVT.png'))
        elif not self.isEVT():
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
        self.XYcrs = QgsCoordinateReferenceSystem(4326)
        if ok:
            if point.x() == 0 and point.y() == 0:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    self.tr('Error'), self.tr('Invalid input !'))
                return
            self.drawDMSPoint()
            if self.tool:
                self.tool.reset()
            self.tool = QgsRubberBand(self.iface.mapCanvas(), QgsWkbTypes.PointGeometry)
            self.tool.setColor(self.settings.getColor())
            self.tool.setWidth(3)
            self.tool.addPoint(point)
            self.drawShape = 'XYpoint'
            self.draw()
            mc.setCenter(point)
            mc.refresh()

    def drawLine(self):
        # Modification qdrawEVT
        if self.isEVT():
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
        if self.isEVT():
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
        if self.isEVT():
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
        if self.isEVT():
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
        if self.isEVT():
            self.actions[6].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawT_EVT.png'))
            self.actions[6].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawTP_EVT.png'))
            self.actions[6].setText(
                self.tr('Buffer drawing tool on the selected layer'))
            self.actions[6].menu().actions()[0].setText(
                self.tr('Polygon buffer drawing tool on the selected layer'))
        elif not self.isEVT():
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
        if self.isEVT():
            self.actions[6].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawTP_EVT.png'))
            self.actions[6].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdrawEVT/resources/icon_DrawT_EVT.png'))
            self.actions[6].setText(
                self.tr('Polygon buffer drawing tool on the selected layer'))
            self.actions[6].menu().actions()[0].setText(
                self.tr('Buffer drawing tool on the selected layer'))
        elif not self.isEVT():
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
        # if self.isEVT():
        #     self.actions[7].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_Settings_EVT.png'))
        # else:
        #     self.actions[7].setIcon(QIcon(':/plugins/qdrawEVT/resources/icon_Settings.png'))
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
            self.iface.mapCanvas().mapSettings().destinationCrs(),
            QgsCoordinateReferenceSystem(2154))
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
                    print('error with '+layer.name()+' on '+str(feature.id()))
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
        if self.drawShape in ['point', 'xypoint', 'Text']:
            mc.zoomScale(5000)
        else:
            mc.zoomToFeatureExtent(g.boundingBox())
        # Test existence du groupe Evènements avec suppression des espaces et des accents dans le nom du groupe testé
        evt = False
        groupevt = False
        for group in self.root.children():
            test = ''.join(
                x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
            if test == 'EVENEMENTS':
                evt = True
                groupevt = group
        if groupevt:
            # Définition de la liste des couches du groupe Evènements
            layer_list = [layer.name() for layer in groupevt.children()]
            # if 'EVENEMENT_LIGNE' in layer_list and 'EVENEMENT_POINT' in layer_list and 'EVENEMENT_POLYGONE' in layer_list:
            if self.layerevtname in layer_list:
                evt = True
            else:
                self.layerevtname = None
                evt = False
        else:
            self.layerevtname = None
            evt = False

        ok = True
        warning = False
        errBuffer_noAtt = False
        errBuffer_Vertices = False

        layer = self.iface.layerTreeView().currentLayer()
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
                    "Polygon?crs=" + layer.crs().authid(), "", "memory"))
                if g.length() == 0 and ok:
                    warning = True
                    errBuffer_Vertices = True

        if self.toolname == 'drawCopies':
            if g.length() < 0:
                warning = True
                errBuffer_noAtt = True

        if ok and not warning:
            name_draw = ''
            ok = True
            add = False
            index = 0
            layers = []
            while not name_draw.strip() and ok:
                # Lancement de la boite de dialogue avec passage de la définition de self.drawShape (gtype en sortie)
                dlg = QDrawLayerDialog(self.iface, self.drawShape, self.layerevtname, evt)
                name_draw, add, index, layers, ok = dlg.getName(
                    self.iface, self.drawShape, self.layerevtname, evt)
        if ok and not warning and evt:
            # ajout dessin de texte
            if self.drawShape == 'text':
                symbols = layer.renderer().symbols(QgsRenderContext())  # todo which context ?
                symbols[0].setColor(self.settings.getColor())
                feature = QgsFeature()
                feature.setGeometry(g)
                feature.setAttributes([name_draw])
                layer.dataProvider().addFeatures([feature])
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
                layer.setLabelsEnabled(True)
                layer.setLabeling(layer_settings)
            else:
                layer = self.project.mapLayersByName(self.layerevtname)[0]
                self.iface.setActiveLayer(layer)
                layer.setReadOnly(False)
                layer.startEditing()
                pr = layer.dataProvider()
                features = QgsFeature()
                # Ajout de la géométrie dans la couche
                features.setGeometry(g)
                # Récupération de la structure de la couche
                features.setFields(layer.fields())  # retrieve the fields from layer and set them to the feature
                # print('layer.fields().count() = ' + str(layer.fields().count()))
                #features.setAttribute(form_wgt_libelle, name_draw)
                features.setAttribute(form_wgt_utilisatr, os.environ.get("USERNAME"))
                # features.setAttribute(form_wgt_remarques, '')
                if self.drawShape in ['point', 'XYpoint']:
                    # Transformation de la coordonnée en EPSG 4326
                    crsSrc = QgsCoordinateReferenceSystem("EPSG:2154")  # L93
                    crsDest = QgsCoordinateReferenceSystem("EPSG:4326")  # WGS 84
                    xform1 = QgsCoordinateTransform(crsSrc, crsDest, self.project)
                    geom = g.centroid().asPoint()
                    # Transformation crsSrc -> crsDest
                    pt1 = xform1.transform(geom)
                    x1, y1 = pt1.x(), pt1.y()
                    # Inscription en donnée attributaire
                    features.setAttribute(form_wgt_x_gps, round(x1, 6))
                    features.setAttribute(form_wgt_y_gps, round(y1, 6))
                elif self.drawShape == 'line':
                    features.setAttribute(form_wgt_longueur, int(round(g.length(),0)))
                elif self.drawShape == 'polygon':
                    features.setAttribute(form_wgt_surface, int(round(g.area(), -2)))
                # Ouverture du formulaire et enregistrement de l'objet si click sur ok
                # avec possibilité d'attribution de focus (voir source)
                # features.setAttribute(form_wgt_libelle, name_draw)
                form = self.iface.getFeatureForm(layer, features)
                # print('version_info[0] = ' + str(version_info[0]))
                # if version_info[0] >= 3:
                form.setMode(QgsAttributeEditorContext.AddFeatureMode)
                if form_wgt_libelle in lst_form_wgt:
                    libelle = form.findChild(QLineEdit, form_wgt_libelle)
                    libelle.setText(name_draw)
                if form_wgt_date in lst_form_wgt:
                    date = form.findChild(QDateTimeEdit, form_wgt_date)
                if form_wgt_h_creation in lst_form_wgt:
                    h_creation = form.findChild(QDateTimeEdit, form_wgt_h_creation)
                if form_wgt_utilisatr in lst_form_wgt:
                    utilisateur = form.findChild(QLineEdit, form_wgt_utilisatr)
                if self.drawShape in ['point', 'XYpoint']:
                    if form_wgt_x_gps in lst_form_wgt:
                        x_gps = form.findChild(QLineEdit, form_wgt_x_gps)
                    if form_wgt_y_gps in lst_form_wgt:
                        y_gps = form.findChild(QLineEdit, form_wgt_y_gps)
                elif self.drawShape == 'line':
                    if form_wgt_longueur in lst_form_wgt:
                        longueur = form.findChild(QLineEdit, form_wgt_longueur)
                elif self.drawShape == 'polygon':
                    if form_wgt_surface in lst_form_wgt:
                        surface = form.findChild(QLineEdit, form_wgt_surface)
                if form_wgt_source in lst_form_wgt:
                    source = form.findChild(QLineEdit, form_wgt_source)
                    source.setFocus(True)
                if form_wgt_h_constat in lst_form_wgt:
                    constat = form.findChild(QDateTimeEdit, 'h_constat')
                if form_wgt_remarques in lst_form_wgt:
                    remarques = form.findChild(QPlainTextEdit, form_wgt_remarques)
                # test_today = datetime.today().strftime(h_creation.text())
                # form.show()
                test_draw = form.exec_()
                if test_draw == 1:
                    #print("test_draw = OK")
                    # placer ici l'inscription dans la couche des données saisies dans le formulaire
                    # features.setAttribute(form_wgt_date, datetime.today().strftime(date.text()))
                    # features.setAttribute(form_wgt_h_creation, datetime.today().strftime(h_creation.text()))
                    features.setAttribute(form_wgt_utilisatr, utilisateur.text())
                    test_h_constat = datetime.today().strftime(constat.text())
                    # Test de l'attribut h_constat : si il est différent de l'attribut h_creation,inscription dans la couche, sinon rien
                    if test_h_constat != datetime.today().strftime(h_creation.text()):
                        # print('test_h_constat : ' + test_h_constat)
                        features.setAttribute(form_wgt_h_constat, datetime.today().strftime(test_h_constat))
                    # features.setAttribute(form_wgt_libelle, libelle.text())
                    # features.setAttribute(form_wgt_source, source.text())
                    # features.setAttribute(form_wgt_remarques, remarques.toPlainText())
                    # if self.drawShape in ['point', 'XYpoint']:
                    #     features.setAttribute(form_wgt_x_gps, x_gps.text())
                    #     features.setAttribute(form_wgt_y_gps, y_gps.text())
                    # elif self.drawShape == 'line':
                    #     features.setAttribute(form_wgt_longueur, longueur.text())
                    # elif self.drawShape == 'polygon':
                    #     features.setAttribute(form_wgt_surface, surface.text())
                    # layer.addFeatures([features])
                    layer.commitChanges()
                    layer.setReadOnly(True)
                    self.QgisV3LayerRandomColor(layer, form_wgt_libelle)
                else:
                    #print("test_draw = Annuler")
                    layer.rollBack()
                    layer.commitChanges()
                    layer.setReadOnly(True)
                    pass

        if ok and not warning and not evt:
            test_draw = 1
            layer = None
            if add:
                layer = layers[index]
                if self.drawShape in ['point', 'XYpoint', 'text']:
                    g = g.centroid()
            else:
                if self.drawShape in ['point', 'text']:
                    layer = QgsVectorLayer("Point?crs="+self.iface.mapCanvas().mapSettings().destinationCrs().authid()+"&field="+self.tr('Drawings')+":string(255)", name_draw, "memory")
                    g = g.centroid()  # force geometry as point
                elif self.drawShape == 'XYpoint':
                    layer = QgsVectorLayer("Point?crs="+self.XYcrs.authid()+"&field="+self.tr('Drawings')+":string(255)", name_draw, "memory")
                    g = g.centroid()
                elif self.drawShape == 'line':
                    layer = QgsVectorLayer("LineString?crs="+self.iface.mapCanvas().mapSettings().destinationCrs().authid()+"&field="+self.tr('Drawings')+":string(255)", name_draw, "memory")
                    # fix_print_with_import
                else:
                    layer = QgsVectorLayer("Polygon?crs="+self.iface.mapCanvas().mapSettings().destinationCrs().authid()+"&field="+self.tr('Drawings')+":string(255)", name_draw, "memory")
            layer.startEditing()
            symbols = layer.renderer().symbols(QgsRenderContext())  # todo which context ?
            symbols[0].setColor(self.settings.getColor())
            feature = QgsFeature()
            feature.setGeometry(g)
            feature.setAttributes([name_draw])
            layer.dataProvider().addFeatures([feature])
            #ajout dessin de texte
            if self.drawShape == 'text':
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
                layer.setLabelsEnabled(True)
                layer.setLabeling(layer_settings)
            layer.commitChanges()
            if not add:
                pjt = QgsProject.instance()
                pjt.addMapLayer(layer, False)
                if pjt.layerTreeRoot().findGroup(self.tr('Drawings')) is None:
                    pjt.layerTreeRoot().insertChildNode(
                        0, QgsLayerTreeGroup(self.tr('Drawings')))
                group = pjt.layerTreeRoot().findGroup(
                    self.tr('Drawings'))
                group.insertLayer(0, layer)
            self.iface.layerTreeView().refreshLayerSymbology(layer.id())
            self.iface.mapCanvas().refresh()

        else:
            if warning:
                if errBuffer_noAtt:
                    self.iface.messageBar().pushWarning(
                        self.tr('Warning'),
                        self.tr('You didn\'t click on a layer\'s attribute !'))
                elif errBuffer_Vertices:
                    self.iface.messageBar().pushWarning(
                        self.tr('Warning'),
                        self.tr('You must give a non-null value for a \
                        point\'s or line\'s perimeter !'))
                else:
                    self.iface.messageBar().pushWarning(
                        self.tr('Warning'),
                        self.tr('There is no selected layer, or it is not \
                        vector nor visible !'))
        # Modification pour ajout de la sélection des couches intersectant
        # une ligne ou un polygone, avec cochage automatique du groupe enjeux
        # self.tool.reset()
        # self.resetSB()
        # self.bGeom = None
        if self.drawShape not in ['point', 'XYpoint', 'text'] and test_draw == 1:
            # Définition du choix d'une sélection en intersection
            box = QMessageBox()
            box.setIcon(QMessageBox.Information)
            box.setText(self.tr("Drawing completed. Make a selection in its grip?"))
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.Yes)
            buttonYes = box.button(QMessageBox.Yes)
            # buttonYes.setText(self.tr('Continue'))
            buttonNo = box.button(QMessageBox.No)
            # buttonNo.setText(self.tr('Cancel'))
            # Pour que la fenêtre reste au premier plan de toutes les applications en cours
            box.setWindowFlags(Qt.WindowStaysOnTopHint)
            box.exec_()
            if box.clickedButton() == buttonYes:
                warning = True
                ok = True
                active = False
                errBuffer_noAtt = False
                errBuffer_Vertices = False

                buffer_geom = None
                buffer_geom_crs = None

                for group in self.root.children():
                    # Test couvrant les cas d'écriture avec accent et/ou majuscule en entête (Mettre le mot à rechercher en majuscules)
                    test = ''.join(
                        x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
                    if test == 'DESSINS':
                        self.groupe_dessin = self.root.findGroup('Dessins')
                        # Décochage, groupe inutile dans la sélection
                        self.groupe_dessin.setItemVisibilityCheckedRecursive(False)
                    if test == 'EVENEMENTS':
                        self.groupe_evt = self.root.findGroup('Evenements')
                        # Décochage, groupe inutile dans la sélection
                        self.groupe_evt.setItemVisibilityCheckedRecursive(False)
                    if test == 'ENJEUX':
                        self.groupe_enjeux = self.root.findGroup('Enjeux')
                        # Cochage des groupes désirés dans la sélection
                        self.groupe_enjeux.setItemVisibilityCheckedRecursive(True)
                    if test == 'ADMINISTRATIF':
                        self.groupe_administratif = self.root.findGroup('Administratif')
                        # Décochage, groupe inutile dans la sélection
                        self.groupe_administratif.setItemVisibilityCheckedRecursive(False)

                # Nous vérifions s'il y a au moins une couche visible
                for layer in QgsProject().instance().mapLayers().values():
                    if QgsProject.instance().layerTreeRoot().findLayer(layer.id()).isVisible():
                        warning = False
                        active = True
                        break
                # Création de buffer sur la couche courante
                if self.request == 'buffer':
                    layer = self.iface.layerTreeView().currentLayer()
                    if layer is not None and layer.type() == QgsMapLayer.VectorLayer and QgsProject.instance().layerTreeRoot().findLayer(
                            layer.id()).isVisible():
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
                    self.loadingWindow.activateWindow();
                    self.loadingWindow.showNormal();
                    for layer in QgsProject().instance().mapLayers().values():
                        if layer.type() == QgsMapLayer.VectorLayer and QgsProject.instance().layerTreeRoot().findLayer(
                                layer.id()).isVisible():
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
                                    print('error with ' + layer.name() + ' on ' + str(feature.id()))
                                    feat_id.append(feature.id())
                                index += 1
                                self.loadingWindow.setValue(int((float(index) / nbfeatures) * 100))
                                if self.loadingWindow.wasCanceled():
                                    self.loadingWindow.reset()
                                    break
                                QApplication.processEvents()
                            layer.selectByIds(feat_id)

                    self.loadingWindow.close()
                    self.showAttributesTable(name_draw)
                    # Pour épurer l'affichage, déselection de toutes les entités sélectionnées
                    # (évite les grandes zone jaunes)
                    if not self.settings.keepselect:
                        # print('keepselect non coché')
                        # root = QgsProject.instance().layerTreeRoot()
                        for checked_layers in self.root.checkedLayers():
                            try:
                                checked_layers.removeSelection()
                            except:
                                pass
                        self.iface.mapCanvas().refresh()
                    else:
                        # print('keepselect coché')
                        pass
                else:
                    # Display a warning in the message bar depending of the error
                    if active == False:
                        self.iface.messageBar().pushWarning(self.tr('Warning'), self.tr('There is no active layer !'))
                    elif ok == False:
                        pass
                    elif errBuffer_noAtt:
                        self.iface.messageBar().pushWarning(self.tr('Warning'),
                                                            self.tr("You didn't click on a layer's attribute !"))
                    elif errBuffer_Vertices:
                        self.iface.messageBar().pushWarning(self.tr('Warning'), self.tr(
                            "You must give a non-null value for a point's or line's perimeter!"))
                    else:
                        self.iface.messageBar().pushWarning(self.tr('Warning'), self.tr(
                            'There is no selected layer, or it is not vector nor visible!'))

                # Recochage des groupes décochés pour la sélection
                # avec try: pour parer à l'absence du groupe dans le projet
                try:
                    self.groupe_dessin.setItemVisibilityCheckedRecursive(True)
                except:
                    pass
                try:
                    self.groupe_evt.setItemVisibilityCheckedRecursive(True)
                except:
                    pass
                # Décochage du groupe Enjeux testé, pertinent avec la recopie des styles de colonnes, à voir
                # try:
                #     self.groupe_enjeux.setItemVisibilityChecked(False)
                # except:
                #     pass
        else:
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
        for unique_value in unique_values:
            # initialize the default symbol for this geometry type
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())

            # configure a symbol layer
            layer_style = {}
            # Couleurs aléatoires, le dernier paramètre règle le niveau de transparence (de 0 à 100%)
            layer_style['color'] = '%d, %d, %d, %d' % (random.randrange(0, 256), random.randrange(0, 256), random.randrange(0, 256), 25)
            # Couleur rouge, le dernier paramètre règle le niveau de transparence (de 0 à 100%)
            # layer_style['color'] = '%d, %d, %d, %d' % (255, 0, 0, 25)
            layer_style['outline'] = '#000000'
            symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)

            # replace default symbol layer with the configured one
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)

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

