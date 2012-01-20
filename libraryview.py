# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from PyQt4 import QtGui

class LibraryView(QtGui.QTreeView):
    def resizeEvent(self, evt):
        # Und ob du es tust.
        self.setColumnWidth(0, evt.size().width() - 100)
        return QtGui.QTreeView.resizeEvent(self, evt)
