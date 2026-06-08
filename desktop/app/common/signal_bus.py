# coding: utf-8
from PyQt5.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """ Signal bus """

    checkUpdateSig = pyqtSignal()
    micaEnableChanged = pyqtSignal(bool)
    playPlaylistRequested = pyqtSignal(list, int)
    playbackError = pyqtSignal(str)
    playbackTrackChanged = pyqtSignal(object, int)
    downloadStarted = pyqtSignal(str)
    downloadRequested = pyqtSignal(object, object)
    downloadFinished = pyqtSignal(str)
    downloadFailed = pyqtSignal(str)


signalBus = SignalBus()
