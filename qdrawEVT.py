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
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QMenu, QInputDialog, QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit,\
    QDateTimeEdit, QTimeEdit, QPushButton, QComboBox, QLabel, QCheckBox

from qgis.PyQt.QtGui import QIcon, QColor, QFont

from qgis.core import *

# from qgis.core import QgsFeature, QgsProject, QgsGeometry,QgsPointXY,\
#     QgsCoordinateTransform, QgsCoordinateTransformContext, QgsMapLayer,\
#     QgsFeatureRequest, QgsVectorLayer, QgsLayerTreeGroup, QgsRenderContext,\
#     QgsCoordinateReferenceSystem, QgsWkbTypes, QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling

from qgis.gui import QgsRubberBand

from .drawtools import DrawPoint, DrawRect, DrawLine, DrawCircle, DrawPolygon,\
    SelectPoint, XYDialog, DMSDialog

from .qdrawsettings import QdrawSettings

from .qdrawlayerdialogEVT import QDrawLayerDialog

from datetime import datetime, date, time

import os, unicodedata

from . import resources

# Obtenir l'instance du projet en cours
project = QgsProject.instance()
# Root du projet en cours
root = project.layerTreeRoot()
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
            'qdraw_{}.qm'.format(locale))
        #print('locale_path = '+str(locale_path))

        # # Obtenir l'instance du projet en cours
        # self.project = QgsProject.instance()
        # # Root du projet en cours
        # self.root = self.project.layerTreeRoot()
        # # Test existance du groupe Evènements avec suppression des espaces et des accents dans le nom du groupe testé
        # self.evt = False
        # self.groupevt = False
        # for group in self.root.children():
        #     test = ''.join(
        #         x for x in unicodedata.normalize('NFKD', group.name()) if unicodedata.category(x)[0] == 'L').upper()
        #     if test == 'EVENEMENTS':
        #         self.evt = True
        #         self.groupevt = group

        self.translator = None
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.iface = iface
        self.sb = self.iface.statusBarIface()
        self.tool = None
        self.toolname = None

        self.bGeom = None

        self.actions = []
        self.menu = '&QdrawEVT'
        self.toolbar = self.iface.addToolBar('QdrawEVT')
        self.toolbar.setObjectName('QdrawEVT')

        self.settings = QdrawSettings()

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

    def isEVT(self):
        # Obtenir l'instance du projet en cours
        self.project = QgsProject.instance()
        # Root du projet en cours
        self.root = self.project.layerTreeRoot()
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
                QIcon(':/plugins/qdraw/resources/icon_DrawPt_EVT.png'))
            self.actions[1].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdraw/resources/icon_DrawPtXY_EVT.png'))
            self.actions[1].menu().actions()[1].setIcon(
                QIcon(':/plugins/qdraw/resources/icon_DrawPtDMS_EVT.png'))
        elif not self.isEVT():
            self.actions[1].setIcon(
                QIcon(':/plugins/qdraw/resources/icon_DrawPt.png'))
            self.actions[1].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdraw/resources/icon_DrawPtXY.png'))
            self.actions[1].menu().actions()[1].setIcon(
                QIcon(':/plugins/qdraw/resources/icon_DrawPtDMS.png'))
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
        crsSrc = crs # projection définie dans drawXYPoint() qdraw.py (WGS84)
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
                QIcon(':/plugins/qdraw/resources/icon_DrawPt_EVT.png'))
            self.actions[1].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdraw/resources/icon_DrawPtXY_EVT.png'))
            self.actions[1].menu().actions()[1].setIcon(
                QIcon(':/plugins/qdraw/resources/icon_DrawPtDMS_EVT.png'))
        elif not self.isEVT():
            self.actions[1].setIcon(
                QIcon(':/plugins/qdraw/resources/icon_DrawPt.png'))
            self.actions[1].menu().actions()[0].setIcon(
                QIcon(':/plugins/qdraw/resources/icon_DrawPtXY.png'))
            self.actions[1].menu().actions()[1].setIcon(
                QIcon(':/plugins/qdraw/resources/icon_DrawPtDMS.png'))
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

        rb = self.tool.rb
        g = rb.asGeometry()

        # Modification qdrawEVT
        # Obtenir l'instance du projet en cours
        project = QgsProject.instance()
        # Root du projet en cours
        root = project.layerTreeRoot()
        # Test existance du groupe Evènements avec suppression des espaces et des accents dans le nom du groupe testé
        evt = False
        groupevt = False
        for group in root.children():
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
            name = ''
            ok = True
            add = False
            index = 0
            layers = []
            while not name.strip() and ok:
                # Lancement de la boite de dialogue avec passage de la définition de self.drawShape (gtype en sortie)
                dlg = QDrawLayerDialog(self.iface, self.drawShape, self.layerevtname, evt)
                name, add, index, layers, ok = dlg.getName(
                    self.iface, self.drawShape, self.layerevtname, evt)
        if ok and not warning and evt:
            layer = None
            if add:
                layer = layers[index]
                if self.drawShape in ['point', 'XYpoint', 'text']:
                    g = g.centroid()
            elif not add and evt:
                if self.drawShape == 'text':
                    layer = QgsVectorLayer(
                        "Point?crs=" + self.iface.mapCanvas().mapSettings().destinationCrs().authid() + "&field=" + self.tr(
                            'Drawings') + ":string(255)", name, "memory")
                    g = g.centroid()  # force geometry as point
                elif self.drawShape in ['point', 'XYpoint'] and not evt:
                    layer = QgsVectorLayer(
                        "Point?crs=" + self.XYcrs.authid() + "&field=" + self.tr('Drawings') + ":string(255)", name,
                        "ogr")
                    g = g.centroid()
                elif self.drawShape == 'line' and not evt:
                    layer = QgsVectorLayer(
                        "LineString?crs=" + self.iface.mapCanvas().mapSettings().destinationCrs().authid() + "&field=" + self.tr(
                            'Drawings') + ":string(255)", name, "memory")
                    # fix_print_with_import
                    print(
                        "LineString?crs=" + self.iface.mapCanvas().mapSettings().destinationCrs().authid() + "&field=" + self.tr(
                            'Drawings') + ":string(255)")
                else:
                    layer = QgsVectorLayer(
                        "Polygon?crs=" + self.iface.mapCanvas().mapSettings().destinationCrs().authid() + "&field=" + self.tr(
                            'Drawings') + ":string(255)", name, "memory")
            # ajout dessin de texte
            if self.drawShape == 'text':
                symbols = layer.renderer().symbols(QgsRenderContext())  # todo which context ?
                symbols[0].setColor(self.settings.getColor())
                feature = QgsFeature()
                feature.setGeometry(g)
                feature.setAttributes([name])
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
                layer = project.mapLayersByName(self.layerevtname)[0]
                self.iface.setActiveLayer(layer)
                layer.startEditing()
                features = QgsFeature()
                # Récupération de la structure de la couche
                features.setFields(layer.fields())  # retrieve the fields from layer and set them to the feature
                # with edit(layer):
                # Ajout de la géométrie dans la couche
                features.setGeometry(g)
                # Ouverture du formulaire et enregistrement de l'objet si click sur ok
                # avec possibilité d'attribution de focus (voir source)
                form = self.iface.getFeatureForm(layer, features)
                if form_wgt_libelle in lst_form_wgt:
                    libelle = form.findChild(QLineEdit, form_wgt_libelle)
                    libelle.setText(name)
                if form_wgt_utilisatr in lst_form_wgt:
                    utilisateur = form.findChild(QLineEdit, form_wgt_utilisatr)
                    utilisateur.setText(os.environ.get("USERNAME"))
                if self.drawShape in ['point', 'XYpoint']:
                    # Transformation de la coordonnée en EPSG 4326
                    crsSrc = QgsCoordinateReferenceSystem("EPSG:2154")  # L93
                    crsDest = QgsCoordinateReferenceSystem("EPSG:4326")  # WGS 84
                    xform1 = QgsCoordinateTransform(crsSrc, crsDest, project)
                    geom = g.centroid().asPoint()
                    # Transformation crsSrc -> crsDest
                    pt1 = xform1.transform(geom)
                    x1, y1 = pt1.x(), pt1.y()
                    # Inscription en donnée attributaire
                    if form_wgt_x_gps in lst_form_wgt:
                        x_gps = form.findChild(QLineEdit, form_wgt_x_gps)
                        x_gps.setText(str(round(x1, 6)))
                        features.setAttribute(form_wgt_x_gps, x_gps.text())
                    if form_wgt_y_gps in lst_form_wgt:
                        y_gps = form.findChild(QLineEdit, form_wgt_y_gps)
                        y_gps.setText(str(round(y1, 6)))
                        features.setAttribute(form_wgt_y_gps, y_gps.text())
                elif self.drawShape == 'line':
                    if form_wgt_longueur in lst_form_wgt:
                        longueur = form.findChild(QLineEdit, form_wgt_longueur)
                        longueur.setText(str(round(g.length(),2)))
                        features.setAttribute(form_wgt_longueur, longueur.text())
                elif self.drawShape == 'polygon':
                    if form_wgt_longueur in lst_form_wgt:
                        surface = form.findChild(QLineEdit, form_wgt_surface)
                        surface.setText(str(round(g.area(), -2)))
                        features.setAttribute(form_wgt_surface, surface.text)
                if form_wgt_source in lst_form_wgt:
                    source = form.findChild(QLineEdit, form_wgt_source)
                    source.setFocus(True)
                if form_wgt_h_constat in lst_form_wgt:
                    constat = form.findChild(QDateTimeEdit, 'h_constat')
                if form_wgt_remarques in lst_form_wgt:
                    remarques = form.findChild(QPlainTextEdit, form_wgt_remarques)
                # Inscription automatique de la date et de l'heure de création de l'évènement
                features.setAttribute(form_wgt_date, date.today().strftime('%d/%m/%Y'))
                features.setAttribute(form_wgt_h_creation, datetime.today().strftime('%Hh%Mmn'))
                # placer ici les attributs avec contrainte NO NULL et inscription automatique
                features.setAttribute(form_wgt_utilisatr, utilisateur.text())
                features.setAttribute(form_wgt_libelle, libelle.text())
                if form.exec_():
                    # placer ici l'inscription des données des attributs saisis dans le formulaire
                    # features.setAttribute(form_wgt_utilisatr, utilisateur.text())
                    # features.setAttribute(form_wgt_libelle, libelle.text())
                    features.setAttribute(form_wgt_source, source.text())
                    features.setAttribute(form_wgt_h_constat, constat.text())
                    features.setAttribute(form_wgt_remarques, remarques.toPlainText())
                    layer.dataProvider().addFeatures([features])
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
                layer.commitChanges()

        if ok and not warning and not evt:
            layer = None
            if add:
                layer = layers[index]
                if self.drawShape in ['point', 'XYpoint', 'text']:
                    g = g.centroid()
            else:
                if self.drawShape in ['point', 'text']:
                    layer = QgsVectorLayer("Point?crs="+self.iface.mapCanvas().mapSettings().destinationCrs().authid()+"&field="+self.tr('Drawings')+":string(255)", name, "memory")
                    g = g.centroid()  # force geometry as point
                elif self.drawShape == 'XYpoint':
                    layer = QgsVectorLayer("Point?crs="+self.XYcrs.authid()+"&field="+self.tr('Drawings')+":string(255)", name, "memory")
                    g = g.centroid()
                elif self.drawShape == 'line':
                    layer = QgsVectorLayer("LineString?crs="+self.iface.mapCanvas().mapSettings().destinationCrs().authid()+"&field="+self.tr('Drawings')+":string(255)", name, "memory")
                    # fix_print_with_import
                    print("LineString?crs="+self.iface.mapCanvas().mapSettings().destinationCrs().authid()+"&field="+self.tr('Drawings')+":string(255)")
                else:
                    layer = QgsVectorLayer("Polygon?crs="+self.iface.mapCanvas().mapSettings().destinationCrs().authid()+"&field="+self.tr('Drawings')+":string(255)", name, "memory")
            layer.startEditing()
            symbols = layer.renderer().symbols(QgsRenderContext())  # todo which context ?
            symbols[0].setColor(self.settings.getColor())
            feature = QgsFeature()
            feature.setGeometry(g)
            feature.setAttributes([name])
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
        self.tool.reset()
        self.resetSB()
        self.bGeom = None
