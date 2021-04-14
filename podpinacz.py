# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Podpinacz
                                 A QGIS plugin
 Podpina warstwy z inwentaryzacji do uzupełniania
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-04-02
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Kamil Drejer
        email                : kamil.drejer@ansee.pl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from PyQt5 import QtCore, QtGui, QtWidgets #works for pyqt5
from qgis.gui import QgsFileWidget
# from qgis.core import QgsProcessing
# from qgis.core import QgsProcessingAlgorithm
# from qgis.core import QgsProcessingMultiStepFeedback
# from qgis.core import QgsProcessingParameterVectorLayer
# from qgis.core import QgsProcessingParameterProviderConnection
# from qgis.core import QgsProcessingParameterDatabaseSchema
# from qgis.core import QgsProcessingParameterDatabaseTable
# from qgis.core import QgsProcessingParameterFieldMapping
# from qgis.core import QgsProcessingParameterFeatureSink
# from qgis.core import QgsProcessingContext
from qgis.core import QgsVectorLayerJoinInfo
from qgis.core import QgsProject
from qgis.core import QgsField
from qgis.core import QgsLayerTreeLayer
from qgis.core import QgsVectorLayer, QgsDataSourceUri
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCoordinateTransformContext
from qgis.core import QgsVectorFileWriter
from qgis.core import Qgis
from qgis.utils import iface
from PyQt5.QtCore import QVariant
import processing
import re


# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .podpinacz_dialog import PodpinaczDialog
import os.path


class Podpinacz:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Podpinacz_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Uzupełnianki krok 1')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Podpinacz', message)


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
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/podpinacz/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Podpinacz'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Uzupełnianki krok 1'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = PodpinaczDialog()

        self.dlg.dodajPola.clear()
        self.dlg.dodajPola.addItem('status_ochr')
        self.dlg.dodajPola.addItem('uza_st_och')
        self.dlg.dodajPola.addItem('zdj_fit')
        self.dlg.dodajPola.addItem('st_rozw')
        self.dlg.dodajPola.addItem('rodz_obs')
        self.dlg.dodajPola.addItem('funk_siedl')
        self.dlg.dodajPola.addItem('gniazd')
        self.dlg.dodajPola.addItem('pop')

        self.dlg.liczebnosc.clear()
        self.dlg.liczebnosc.addItem('liczba')
        self.dlg.liczebnosc.addItem('licz_min + licz_max')
        self.dlg.liczebnosc.setCurrentRow(0)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop





        result = self.dlg.exec_()
        # See if OK was pressed


        # self.dlg.output_path.setFilePath(QgsProject.instance().absolutePath())
        # self.dlg.output_path.setFilter(QgsVectorFileWriter.fileFilterString())



        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            print(self.dlg.output_path.filePath())
            if len(self.dlg.output_path.filePath())<4:
                iface.messageBar().pushMessage("Error", "Proszę wybrać plik do zapisu", level=Qgis.Critical)
                return

            grupy_string = ""
            if self.dlg.ptaki.isChecked():
                grupy_string = "grupa = 'Gatunki ptaków'"
            elif self.dlg.siedliska.isChecked():
                grupy_string = "grupa = 'siedliska' or grupa = 'Gatunki wątrobowców' or  grupa = 'Zbiorowiska roślinne' or  grupa = 'Gatunki grzybów' or  grupa = 'Gatunki brunatnic' or grupa = 'Gatunki krasnorostów' or grupa = 'Gatunki mchów' or grupa = 'Gatunki porostów' or grupa = 'Gatunki roślin naczyniowych'"
            elif self.dlg.reszta.isChecked():
                grupy_string = "grupa != 'Gatunki ptaków' and not (grupa = 'siedliska' or grupa = 'Gatunki wątrobowców' or  grupa = 'Zbiorowiska roślinne' or  grupa = 'Gatunki grzybów' or  grupa = 'Gatunki brunatnic' or grupa = 'Gatunki krasnorostów' or grupa = 'Gatunki mchów' or grupa = 'Gatunki porostów' or grupa = 'Gatunki roślin naczyniowych')"
            else:
                iface.messageBar().pushMessage("Error", "Proszę zaznaczyć grupę", level=Qgis.Critical)
                return

            tempfile = self.dlg.output_path.filePath()

            for layer in self.iface.mapCanvas().layers():
                if tempfile == layer.dataProvider().dataSourceUri():
                    iface.messageBar().pushMessage("Error", "Wybrano warstwę wczytaną do projektu. Proszę wybrać inną.", level=Qgis.Critical)
                    return

            lyr_out0 = iface.activeLayer()
            if lyr_out0.isValid():
                crs = lyr_out0.crs()
                crs.createFromId(2180)
                lyr_out0.setCrs(crs)

                if lyr_out0.wkbType()==100:
                    iface.messageBar().pushMessage("Error", "Proszę zaznaczyć warstwę posiadającą geometrię", level=Qgis.Critical)
                    return
            else:
                iface.messageBar().pushMessage("Error", "Proszę zaznaczyć warstwę do podpięcia", level=Qgis.Critical)
                return

             #"C:\\Users\\k.drejer\\Downloads\\outShapefile6.gpkg"

            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "ESRI Shapefile"
            options.fileEncoding = "UTF8"

            # Save memory layer to file
            QgsVectorFileWriter.deleteShapeFile(tempfile)
            error = QgsVectorFileWriter.writeAsVectorFormatV2(lyr_out0, tempfile, QgsCoordinateTransformContext(), options)

            if error == QgsVectorFileWriter.NoError:
                print("success! writing new memory layer")

            if tempfile[-4:] != '.shp':
                sciezka_wczytaj = tempfile+'.shp'
            else:
                sciezka_wczytaj = tempfile
            lyr_out = QgsVectorLayer(sciezka_wczytaj, "wczytana", "ogr" )

            if not lyr_out.isValid():
                iface.messageBar().pushMessage("Error", "Problem z plikiem wyjściowym, proszę wybrać inny", level=Qgis.Critical)
                return

            tablename_slowniki = "Slowniki"
            tablename_keys = "Slowniki_keys"

            if self.dlg.ptaki.isChecked():
                tablename_slowniki_filter = "Slowniki_ptaki"
                tablename_keys_filter = "Slowniki_keys_ptaki"

            elif self.dlg.siedliska.isChecked():
                tablename_slowniki_filter = "Slowniki_siedliska"
                tablename_keys_filter = "Slowniki_keys_siedliska"
            else:
                tablename_slowniki_filter = "Slowniki_reszta"
                tablename_keys_filter = "Slowniki_keys_reszta"

            #tablename_slowniki = '"Slowniki"."Slowniki" where layer like "Gatunki gadów (exp)"'

            geometrycol = ''

            uri = QgsDataSourceUri()
            uri.setConnection("54.38.243.14", "5432", "postgis", "devel", r'ohtah"mae4Xo')


            if len(QgsProject.instance().mapLayersByName(tablename_slowniki_filter)) == 0:
            	uri.setDataSource ("Slowniki", tablename_slowniki, "", grupy_string)
            	#uri.setDataSource ("Slowniki", tablename_slowniki,'','','hendle')
            	table=QgsVectorLayer (uri.uri().replace(' ()',''), tablename_slowniki, "postgres")
            	if not table.isValid():
            		print("Layer %s did not load" %table.name())
            	QgsProject.instance().addMapLayer(table)
            else:
            	table=QgsProject.instance().mapLayersByName(tablename_slowniki_filter)[0]
            	QgsProject.instance().addMapLayer(table)
            table.setName(tablename_slowniki_filter)

            if len(QgsProject.instance().mapLayersByName(tablename_keys_filter)) == 0:
            	uri.setDataSource ("Slowniki", tablename_keys,"", grupy_string)
            	gatunki=QgsVectorLayer (uri.uri().replace(' ()',''), tablename_keys, "postgres")
            	if not table.isValid():
            		print("Layer %s did not load" %gatunki.name())
            	QgsProject.instance().addMapLayer(gatunki)
            else:
            	gatunki=QgsProject.instance().mapLayersByName(tablename_keys_filter)[0]
            	QgsProject.instance().addMapLayer(gatunki)
            gatunki.setName(tablename_keys_filter)

            #table = QgsVectorLayer("", "table", "memory")
            #sQgsProject.instance().addMapLayer(table)
            field_names = lyr_out.fields().names()
            field_names = [each_string.lower() for each_string in field_names]


            lyr_out.startEditing()

            if '__nazwa__' not in field_names:
            	field = QgsField( '__nazwa__', QVariant.String )
            	lyr_out.addAttribute( field )

            if 'data' not in field_names:
            	field = QgsField( 'data', QVariant.Date )
            	lyr_out.addAttribute( field )

            if 'im_naz' not in field_names:
            	field = QgsField( 'im_naz', QVariant.String )
            	lyr_out.addAttribute( field )

            if self.dlg.liczebnosc.currentItem().text() == "liczba":
                if 'liczba' not in field_names:
                	field = QgsField( 'liczba', QVariant.String )
                	lyr_out.addAttribute( field )
            else:
                if 'licz_min' not in field_names:
                	field = QgsField( 'licz_min', QVariant.String )
                	lyr_out.addAttribute( field )
                if 'licz_max' not in field_names:
                	field = QgsField( 'licz_max', QVariant.String )
                	lyr_out.addAttribute( field )

            if 'jednostki' not in field_names:
            	field = QgsField( 'jednostki', QVariant.String )
            	lyr_out.addAttribute( field )

            for item in self.dlg.dodajPola.selectedItems():
                if item.text() not in field_names:
                	field = QgsField( item.text(), QVariant.String )
                	lyr_out.addAttribute( field )

            if 'uwagi_ost' not in field_names:
            	field = QgsField( 'uwagi_ost', QVariant.String )
            	lyr_out.addAttribute( field )

            if 'X_92' not in field_names:
            	field = QgsField( 'X_92', QVariant.Double )
            	lyr_out.addAttribute( field )

            if 'Y_92' not in field_names:
            	field = QgsField( 'Y_92', QVariant.Double )
            	lyr_out.addAttribute( field )





            for feature in lyr_out.getFeatures():
                fields = lyr_out.fields() # accessing layer fields
                lyr_out.changeAttributeValue(feature.id(),fields.indexFromName("X_92"), feature.geometry().centroid().asPoint()[0])
                lyr_out.changeAttributeValue(feature.id(),fields.indexFromName("Y_92"), feature.geometry().centroid().asPoint()[1])
                lyr_out.changeAttributeValue(feature.id(),fields.indexFromName("im_naz"), self.dlg.autor.text())
                lyr_out.changeAttributeValue(feature.id(),fields.indexFromName("data"), self.dlg.data_obs.date())

            lyr_out.commitChanges()

            tableField = 'handle'
            shpField = '__nazwa__'
            joinObject = QgsVectorLayerJoinInfo()
            joinObject.setJoinFieldName(tableField)
            joinObject.setTargetFieldName(shpField)

            joinObject.setJoinLayerId(table.id())

            joinObject.setUsingMemoryCache(True)
            joinObject.setJoinLayer(table)
            joinObject.setUpsertOnEdit(False)
            joinObject.setDynamicFormEnabled(False)
            joinObject.setPrefix('Slowniki_')
            lyr_out.addJoin(joinObject)

            lyr_out.loadNamedStyle('G:\\Dyski współdzielone\\1_Public\\QGiS\\Slowniki_inwentarki\\style_formularz.qml')

            lyr_out.setName('warstwa_podpieta')


            for field in lyr_out.fields():
                #print(str(field.name()))
                if len(re.findall("Slowniki.*", str(field.name())))!=0:
                    config = lyr_out.attributeTableConfig()
                    columns = config.columns()
                    for column in columns:
                        if column.name == str(field.name()):
                            column.hidden = True
                            break
                    config.setColumns( columns )
                    lyr_out.setAttributeTableConfig( config )

            root = QgsProject.instance().layerTreeRoot()

            QgsProject.instance().addMapLayer(lyr_out, False)
            root.addLayer(lyr_out)

            iface.messageBar().pushMessage("Sukces!", "Warstwa "+ iface.activeLayer().name() +"została podłączona", level=Qgis.Success)
