# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'file_table.ui'
#
# Created by: PyQt5 UI code generator 5.12
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(798, 627)
        self.gridLayout_2 = QtWidgets.QGridLayout(Form)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(Form)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.lineEdit_local = QtWidgets.QLineEdit(Form)
        self.lineEdit_local.setObjectName("lineEdit_local")
        self.gridLayout.addWidget(self.lineEdit_local, 0, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(Form)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.lineEdit_remote = QtWidgets.QLineEdit(Form)
        self.lineEdit_remote.setObjectName("lineEdit_remote")
        self.gridLayout.addWidget(self.lineEdit_remote, 2, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.lineEdit_pattern = QtWidgets.QLineEdit(Form)
        self.lineEdit_pattern.setObjectName("lineEdit_pattern")
        self.gridLayout.addWidget(self.lineEdit_pattern, 1, 1, 1, 1)
        self.pushButton_upload = QtWidgets.QPushButton(Form)
        self.pushButton_upload.setObjectName("pushButton_upload")
        self.gridLayout.addWidget(self.pushButton_upload, 2, 2, 1, 1)
        self.pushButton_check = QtWidgets.QPushButton(Form)
        self.pushButton_check.setObjectName("pushButton_check")
        self.gridLayout.addWidget(self.pushButton_check, 0, 2, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 2, 0, 1, 1)
        self.tableView = QtWidgets.QTableView(Form)
        self.tableView.setObjectName("tableView")
        self.tableView.horizontalHeader().setHighlightSections(False)
        self.tableView.verticalHeader().setVisible(False)
        self.tableView.verticalHeader().setHighlightSections(False)
        self.gridLayout_2.addWidget(self.tableView, 0, 0, 1, 1)
        self.progressBar = QtWidgets.QProgressBar(Form)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName("progressBar")
        self.gridLayout_2.addWidget(self.progressBar, 1, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.label.setText(_translate("Form", "Local File Directory:"))
        self.lineEdit_local.setText(_translate("Form", "C:/Projects/ddh/dl_files/"))
        self.label_3.setText(_translate("Form", "Remote Directory"))
        self.lineEdit_remote.setText(_translate("Form", "/"))
        self.label_2.setText(_translate("Form", "Search Pattern:"))
        self.lineEdit_pattern.setText(_translate("Form", "**/*.lid"))
        self.pushButton_upload.setText(_translate("Form", "Upload"))
        self.pushButton_check.setText(_translate("Form", "Check"))


