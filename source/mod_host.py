#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# MOD-App
# Copyright (C) 2014-2015 Filipe Coelho <falktx@falktx.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE file.

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from mod_settings import *

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

if config_UseQt5:
    from PyQt5.QtCore import pyqtSignal, pyqtSlot, qCritical, qWarning, Qt, QFileInfo, QProcess, QSettings, QThread, QTimer, QUrl
    from PyQt5.QtGui import QDesktopServices
    from PyQt5.QtWidgets import QAction, QApplication, QDialog, QFileDialog, QInputDialog, QLineEdit, QMainWindow, QMessageBox
    from PyQt5.QtWebKitWidgets import QWebView, QWebSettings
else:
    from PyQt4.QtCore import pyqtSignal, pyqtSlot, qCritical, qWarning, Qt, QFileInfo, QProcess, QSettings, QThread, QTimer, QUrl
    from PyQt4.QtGui import QDesktopServices
    from PyQt4.QtGui import QAction, QApplication, QDialog, QFileDialog, QInputDialog, QLineEdit, QMainWindow, QMessageBox
    from PyQt4.QtWebKit import QWebView, QWebSettings

# ------------------------------------------------------------------------------------------------------------
# Imports (UI)

from ui_mod_host import Ui_HostWindow

# ------------------------------------------------------------------------------------------------------------
# Import (WebServer)

# need to set initial settings before importing MOD stuff
setInitialSettings()

from mod import webserver

# prevent buffer size changes
from mod import jack
jack.DEV_HOST = 0

# ------------------------------------------------------------------------------------------------------------
# WebServer Thread

class WebServerThread(QThread):
    # signals
    running = pyqtSignal()

    # globals
    prepareWasCalled = False

    def __init__(self, parent=None):
        QThread.__init__(self, parent)

    def run(self):
        if not self.prepareWasCalled:
            self.prepareWasCalled = True
            webserver.prepare()

        self.running.emit()
        webserver.start()

    def stopWait(self):
        webserver.stop()
        return self.wait(5000)

# ------------------------------------------------------------------------------------------------------------
# Host Window

class HostWindow(QMainWindow):
    # signals
    SIGTERM = pyqtSignal()
    SIGUSR1 = pyqtSignal()

    # --------------------------------------------------------------------------------------------------------

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_HostWindow()
        self.ui.setupUi(self)

        # ----------------------------------------------------------------------------------------------------
        # Internal stuff

        self.fCurrentPedalboard = ""
        self.fFirstHostInit     = True
        self.fIdleTimerId       = 0
        self.fWebFrame          = None

        # to be filled with key-value pairs of current settings
        self.fSavedSettings = {}

        self.fHostProccess = QProcess(self)
        self.fHostProccess.setProcessChannelMode(QProcess.ForwardedChannels)

        self.fWebServerThread = WebServerThread(self)

        # ----------------------------------------------------------------------------------------------------
        # Set up GUI

        self.ui.webview = QWebView(self.ui.swp_webview)
        self.ui.webview.setMinimumWidth(980)
        self.ui.swp_webview.layout().addWidget(self.ui.webview)

        self.ui.label_progress.hide()
        self.ui.stackedwidget.setCurrentIndex(0)

        # TESTING
        # webview will be blue until host and webserver are running
        # when webserver finishes color will be red
        # when host is stopped manually color will be green
        self.ui.webview.setHtml("<html><body bgcolor='blue'></body></html>")

        # ----------------------------------------------------------------------------------------------------
        # Set up GUI (special stuff for Mac OS)

        if MACOS:
            self.ui.act_file_quit.setMenuRole(QAction.QuitRole)
            self.ui.act_settings_configure.setMenuRole(QAction.PreferencesRole)
            self.ui.act_help_about.setMenuRole(QAction.AboutRole)
            #self.ui.menu_Settings.setTitle("Panels")
            #self.ui.menu_Help.hide()

        # ----------------------------------------------------------------------------------------------------
        # Load Settings

        self.loadSettings(True)

        # ----------------------------------------------------------------------------------------------------
        # Connect actions to functions

        self.SIGUSR1.connect(self.slot_handleSIGUSR1)
        self.SIGTERM.connect(self.slot_handleSIGTERM)

        self.fWebServerThread.running.connect(self.slot_webServerRunning)
        self.fWebServerThread.finished.connect(self.slot_webServerFinished)

        self.ui.act_file_new.triggered.connect(self.slot_fileNew)
        self.ui.act_file_open.triggered.connect(self.slot_fileOpen)
        self.ui.act_file_save.triggered.connect(self.slot_fileSave)
        self.ui.act_file_save_as.triggered.connect(self.slot_fileSaveAs)

        self.ui.act_host_start.triggered.connect(self.slot_hostStart)
        self.ui.act_host_stop.triggered.connect(self.slot_hostStop)
        self.ui.act_host_restart.triggered.connect(self.slot_hostRestart)

        self.ui.act_pedalboard_new.triggered.connect(self.slot_pedalboardNew)
        self.ui.act_pedalboard_save.triggered.connect(self.slot_pedalboardSave)
        self.ui.act_pedalboard_save_as.triggered.connect(self.slot_pedalboardSaveAs)
        self.ui.act_pedalboard_share.triggered.connect(self.slot_pedalboardShare)

        self.ui.act_settings_configure.triggered.connect(self.slot_configure)

        self.ui.act_help_about.triggered.connect(self.slot_about)
        self.ui.act_help_project.triggered.connect(self.slot_showProject)
        self.ui.act_help_website.triggered.connect(self.slot_showWebsite)

        # ----------------------------------------------------------------------------------------------------
        # Final setup

        self.setProperWindowTitle()

        QTimer.singleShot(0, self.slot_hostStart)

    # --------------------------------------------------------------------------------------------------------
    # Setup

    def stopWebServer(self):
        if self.fWebServerThread.isRunning() and not self.fWebServerThread.stopWait():
            qWarning("WebServer Thread failed top stop cleanly, forcing terminate")
            self.fWebServerThread.terminate()

    def setProperWindowTitle(self):
        title = "MOD Application"

        if self.fCurrentPedalboard:
            title += " - %s" % self.fCurrentPedalboard

        self.setWindowTitle(title)

    # --------------------------------------------------------------------------------------------------------
    # Files

    def loadProjectNow(self):
        if not self.fCurrentPedalboard:
            return qCritical("ERROR: loading project without filename set")

        # TODO

    def loadProjectLater(self, filename):
        print("TODO")
        return

        #self.fProjectFilename = QFileInfo(filename).absoluteFilePath()
        #self.setProperWindowTitle()
        #QTimer.singleShot(0, self.slot_loadProjectNow)

    def saveProjectNow(self):
        if not self.fCurrentPedalboard:
            return qCritical("ERROR: saving project without filename set")

    def dummyCallback(self, a=None, b=None, c=None):
        pass

    # --------------------------------------------------------------------------------------------------------
    # Files (menu actions)

    @pyqtSlot()
    def slot_fileNew(self):
        return QMessageBox.information(self, self.tr("information"), "TODO")

    @pyqtSlot()
    def slot_fileOpen(self):
        return QMessageBox.information(self, self.tr("information"), "TODO")

        fileFilter = self.tr("MOD Project File (*.modp)")
        filename   = QFileDialog.getOpenFileName(self, self.tr("Open MOD Project File"), self.fSavedSettings[MOD_KEY_MAIN_PROJECT_FOLDER], filter=fileFilter)

        if config_UseQt5:
            filename = filename[0]
        if not filename:
            return

        newFile = True

        #if self.fPluginCount > 0:
            #ask = QMessageBox.question(self, self.tr("Question"), self.tr("There are some plugins loaded, do you want to remove them now?"),
                                                                          #QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            #newFile = (ask == QMessageBox.Yes)

        if newFile:
            # TODO - clear all
            #self.fProjectFilename = filename
            self.setProperWindowTitle()
            self.loadProjectNow()
        else:
            #filenameOld = self.fProjectFilename
            #self.fProjectFilename = filename
            self.loadProjectNow()
            #self.fProjectFilename = filenameOld

    @pyqtSlot()
    def slot_fileSave(self, saveAs=False):
        return QMessageBox.information(self, self.tr("information"), "TODO")

        if self.fCurrentPedalboard and not saveAs:
            return self.saveProjectNow()

        name, ok = QInputDialog.getText(self, self.tr("Pedalboard name"), self.tr("Pedalboard name"),
                                        QLineEdit.Normal, self.fCurrentPedalboard if saveAs else "")

        print(name, ok)

        #fileFilter = self.tr("MOD Project File (*.mod-app)")
        #filename   = QFileDialog.getSaveFileName(self, self.tr("Save MOD Project File"), self.fSavedSettings[MOD_KEY_MAIN_PROJECT_FOLDER], filter=fileFilter)

        #if config_UseQt5:
            #filename = filename[0]
        #if not filename:
            #return

        #if not filename.lower().endswith(".mod-app"):
            #filename += ".mod-app"

        if self.fCurrentPedalboard != name:
            self.fCurrentPedalboard = name
            self.setProperWindowTitle()

        self.saveProjectNow()

    @pyqtSlot()
    def slot_fileSaveAs(self):
        return QMessageBox.information(self, self.tr("information"), "TODO")

        self.slot_fileSave(True)

    @pyqtSlot()
    def slot_loadProjectNow(self):
        return QMessageBox.information(self, self.tr("information"), "TODO")

        self.loadProjectNow()

    # --------------------------------------------------------------------------------------------------------
    # Pedalboard (menu actions)

    @pyqtSlot()
    def slot_pedalboardNew(self):
        if self.fWebFrame is None:
            return
        self.fWebFrame.evaluateJavaScript("desktop.reset()")

    @pyqtSlot()
    def slot_pedalboardSave(self):
        if self.fWebFrame is None:
            return
        self.fWebFrame.evaluateJavaScript("desktop.saveCurrentPedalboard(false)")

    @pyqtSlot()
    def slot_pedalboardSaveAs(self):
        if self.fWebFrame is None:
            return
        self.fWebFrame.evaluateJavaScript("desktop.saveCurrentPedalboard(true)")

    @pyqtSlot()
    def slot_pedalboardShare(self):
        return QMessageBox.information(self, self.tr("information"), "TODO")

        if self.fWebFrame is None:
            return
        self.fWebFrame.evaluateJavaScript("")

    # --------------------------------------------------------------------------------------------------------
    # Settings (menu actions)

    @pyqtSlot()
    def slot_configure(self):
        dialog = SettingsWindow(self)
        if not dialog.exec_():
            return

        self.loadSettings(False)

    # --------------------------------------------------------------------------------------------------------
    # About (menu actions)

    @pyqtSlot()
    def slot_about(self):
        QMessageBox.about(self, self.tr("About"), self.tr("""
            <b>MOD Desktop Application</b><br/><br/>
            Some text will be here.<br/>
            And some more will be here too, and here and here.
        """))

    @pyqtSlot()
    def slot_showProject(self):
        QDesktopServices.openUrl(QUrl("https://github.com/portalmod/mod-app"))

    @pyqtSlot()
    def slot_showWebsite(self):
        QDesktopServices.openUrl(QUrl("http://portalmod.com/"))

    # --------------------------------------------------------------------------------------------------------
    # Host (menu actions)

    @pyqtSlot()
    def slot_hostStart(self):
        if self.fHostProccess.state() == QProcess.Running:
            return

        # start mod-host asynchronously
        # qt will signal either "error" or "started" depending on the process state
        self.fHostProccess.error.connect(self.slot_hostStartError)
        self.fHostProccess.started.connect(self.slot_hostStartSuccess)
        self.fHostProccess.finished.connect(self.slot_hostFinished)

        hostPath = self.fSavedSettings[MOD_KEY_HOST_PATH]
        hostArgs = "--verbose" if self.fSavedSettings[MOD_KEY_HOST_VERBOSE] else "--nofork"
        self.fHostProccess.start(hostPath, [hostArgs])

    @pyqtSlot(QProcess.ProcessError)
    def slot_hostStartError(self, error):
        print("host start error")
        # we're not interested on any more errors
        self.fHostProccess.error.disconnect(self.slot_hostStartError)
        self.fHostProccess.started.disconnect(self.slot_hostStartSuccess)
        self.fHostProccess.finished.disconnect(self.slot_hostFinished)

        # stop webserver
        self.stopWebServer()

        # set error to print and display to user
        if error == QProcess.FailedToStart:
            errorStr = self.tr("Process failed to start.")
        elif error == QProcess.Crashed:
            errorStr = self.tr("Process crashed.")
        elif error == QProcess.Timedout:
            errorStr = self.tr("Process timed out.")
        elif error == QProcess.WriteError:
            errorStr = self.tr("Process write error.")
        else:
            errorStr = self.tr("Unkown error.")

        errorStr = self.tr("Could not start host backend.\n") + errorStr
        qWarning(errorStr)

        # don't show error if this is the first time starting the host
        if self.fFirstHostInit:
            self.fFirstHostInit = False
            return

        # show the error message
        QMessageBox.critical(self, self.tr("Error"), errorStr)

    @pyqtSlot()
    def slot_hostStartSuccess(self):
        print("host start success")
        self.fFirstHostInit = False
        self.fWebServerThread.start()

    @pyqtSlot(int, QProcess.ExitStatus)
    def slot_hostFinished(self, exitCode, exitStatus):
        print("host finished")

    @pyqtSlot()
    def slot_hostStop(self, forced = False):
        # we're done with mod-host, disconnect to ignore possible errors when closing
        try:
            self.fHostProccess.error.disconnect(self.slot_hostStartError)
            self.fHostProccess.started.disconnect(self.slot_hostStartSuccess)
            self.fHostProccess.finished.disconnect(self.slot_hostFinished)
        except:
            pass

        self.fWebFrame = None

        #if self.fPluginCount > 0:
            #if not forced:
                #ask = QMessageBox.question(self, self.tr("Warning"), self.tr("There are still some plugins loaded, you need to remove them to stop the engine.\n"
                                                                            #"Do you want to do this now?"),
                                                                            #QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                #if ask != QMessageBox.Yes:
                    #return

            #self.removeAllPlugins()
            #self.host.set_engine_about_to_close()
            #self.host.remove_all_plugins()

        # unload page
        self.ui.webview.setHtml("<html><body bgcolor='green'></body></html>")

        # stop webserver
        self.stopWebServer()

        # stop mod-host
        if self.fHostProccess.state() == QProcess.Running:
            self.fHostProccess.terminate()
            self.fHostProccess.waitForFinished()

    @pyqtSlot()
    def slot_hostRestart(self):
        self.ui.stackedwidget.setCurrentIndex(0)
        self.slot_hostStop(True)
        self.slot_hostStart()

    # --------------------------------------------------------------------------------------------------------
    # Web Server

    @pyqtSlot()
    def slot_webServerRunning(self):
        # load webserver page in our webview
        self.ui.webview.loadStarted.connect(self.slot_webviewLoadStarted)
        self.ui.webview.loadProgress.connect(self.slot_webviewLoadProgress)
        self.ui.webview.loadFinished.connect(self.slot_webviewLoadFinished)

        self.ui.webview.load(QUrl(config["addr"]))

    @pyqtSlot()
    def slot_webServerFinished(self):
        print("webserver finished")
        # testing red color for server finished
        self.ui.webview.setHtml("<html><body bgcolor='red'></body></html>")

    # --------------------------------------------------------------------------------------------------------
    # Web View

    @pyqtSlot()
    def slot_webviewLoadStarted(self):
        self.ui.label_progress.setText(self.tr("Loading backend..."))
        self.ui.label_progress.show()
        print("load started")

    @pyqtSlot(int)
    def slot_webviewLoadProgress(self, progress):
        self.ui.label_progress.setText(self.tr("Loading backend... %i%%" % progress))
        print("load progress", progress)

    @pyqtSlot(bool)
    def slot_webviewLoadFinished(self, ok):
        # load finished or failed
        self.ui.webview.loadStarted.disconnect(self.slot_webviewLoadStarted)
        self.ui.webview.loadProgress.disconnect(self.slot_webviewLoadProgress)
        self.ui.webview.loadFinished.disconnect(self.slot_webviewLoadFinished)

        if ok:
            # for js evaulation
            self.fWebFrame = self.ui.webview.page().currentFrame()

            # show webpage
            self.ui.label_progress.setText("")
            self.ui.label_progress.hide()
            self.ui.stackedwidget.setCurrentIndex(1)

            # postpone app stuff
            QTimer.singleShot(0, self.slot_webviewPostFinished)

        else:
            # stop js evaulation
            self.fWebFrame = None

            # hide webpage
            self.ui.label_progress.setText(self.tr("Loading backend... failed!"))
            self.ui.label_progress.show()
            self.ui.stackedwidget.setCurrentIndex(0)

        print("load finished")

    @pyqtSlot(bool)
    def slot_webviewPostFinished(self):
        self.fWebFrame.evaluateJavaScript("desktop.prepareForApp()")

    # --------------------------------------------------------------------------------------------------------
    # Settings

    def saveSettings(self):
        settings = QSettings()

        settings.setValue("Geometry", self.saveGeometry())

    def loadSettings(self, firstTime):
        qsettings   = QSettings()
        websettings = self.ui.webview.settings()

        if firstTime:
            self.restoreGeometry(qsettings.value("Geometry", ""))

        self.fSavedSettings = {
            # Main
            MOD_KEY_MAIN_PROJECT_FOLDER:      qsettings.value(MOD_KEY_MAIN_PROJECT_FOLDER,      MOD_DEFAULT_MAIN_PROJECT_FOLDER,      type=str),
            MOD_KEY_MAIN_REFRESH_INTERVAL:    qsettings.value(MOD_KEY_MAIN_REFRESH_INTERVAL,    MOD_DEFAULT_MAIN_REFRESH_INTERVAL,    type=int),
            # Host
            MOD_KEY_HOST_JACK_BUFSIZE_CHANGE: qsettings.value(MOD_KEY_HOST_JACK_BUFSIZE_CHANGE, MOD_DEFAULT_HOST_JACK_BUFSIZE_CHANGE, type=bool),
            MOD_KEY_HOST_JACK_BUFSIZE_VALUE:  qsettings.value(MOD_KEY_HOST_JACK_BUFSIZE_VALUE,  MOD_DEFAULT_HOST_JACK_BUFSIZE_VALUE,  type=int),
            MOD_KEY_HOST_VERBOSE:             qsettings.value(MOD_KEY_HOST_VERBOSE,             MOD_DEFAULT_HOST_VERBOSE,             type=bool),
            MOD_KEY_HOST_PATH:                qsettings.value(MOD_KEY_HOST_PATH,                MOD_DEFAULT_HOST_PATH,                type=str),
            # WebView
            MOD_KEY_WEBVIEW_INSPECTOR:        qsettings.value(MOD_KEY_WEBVIEW_INSPECTOR,        MOD_DEFAULT_WEBVIEW_INSPECTOR,        type=bool),
            MOD_KEY_WEBVIEW_VERBOSE:          qsettings.value(MOD_KEY_WEBVIEW_VERBOSE,          MOD_DEFAULT_WEBVIEW_VERBOSE,          type=bool)
        }

        websettings.setAttribute(QWebSettings.DeveloperExtrasEnabled, self.fSavedSettings[MOD_KEY_WEBVIEW_INSPECTOR])

        if self.fIdleTimerId != 0:
            self.killTimer(self.fIdleTimerId)

        self.fIdleTimerId = self.startTimer(self.fSavedSettings[MOD_KEY_MAIN_REFRESH_INTERVAL])

    # --------------------------------------------------------------------------------------------------------
    # Misc

    @pyqtSlot()
    def slot_handleSIGUSR1(self):
        print("Got SIGUSR1 -> Saving project now")
        self.slot_fileSave()

    @pyqtSlot()
    def slot_handleSIGTERM(self):
        print("Got SIGTERM -> Closing now")
        self.close()

    # --------------------------------------------------------------------------------------------------------
    # Qt events

    def closeEvent(self, event):
        if self.fIdleTimerId != 0:
            self.killTimer(self.fIdleTimerId)
            self.fIdleTimerId = 0

        self.saveSettings()
        self.slot_hostStop(True)

        QMainWindow.closeEvent(self, event)

    def timerEvent(self, event):
        if event.timerId() == self.fIdleTimerId:
            pass

        QMainWindow.timerEvent(self, event)

# ------------------------------------------------------------------------------------------------------------
