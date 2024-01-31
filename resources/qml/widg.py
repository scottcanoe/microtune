# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'InputWidget.ui'
#
# Created by: PyQt5 UI code generator 5.14.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(936, 575)
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setGeometry(QtCore.QRect(50, 30, 191, 331))
        self.groupBox.setObjectName("groupBox")
        self.formLayoutWidget = QtWidgets.QWidget(self.groupBox)
        self.formLayoutWidget.setGeometry(QtCore.QRect(10, 30, 160, 241))
        self.formLayoutWidget.setObjectName("formLayoutWidget")
        self.formLayout = QtWidgets.QFormLayout(self.formLayoutWidget)
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.formLayout.setObjectName("formLayout")
        self.deviceComboBox = QtWidgets.QComboBox(self.formLayoutWidget)
        self.deviceComboBox.setObjectName("deviceComboBox")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.deviceComboBox)
        self.deviceLabel = QtWidgets.QLabel(self.formLayoutWidget)
        self.deviceLabel.setObjectName("deviceLabel")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.deviceLabel)
        self.pushButton = QtWidgets.QPushButton(self.groupBox)
        self.pushButton.setGeometry(QtCore.QRect(10, 280, 161, 32))
        self.pushButton.setObjectName("pushButton")
        self.widget = PlotWidget(Form)
        self.widget.setGeometry(QtCore.QRect(290, 60, 471, 281))
        self.widget.setObjectName("widget")

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.groupBox.setTitle(_translate("Form", "Input"))
        self.deviceLabel.setText(_translate("Form", "device"))
        self.pushButton.setText(_translate("Form", "start"))
from pyqtgraph import PlotWidget
