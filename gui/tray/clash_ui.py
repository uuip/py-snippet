# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'clash.ui'
##
## Created by: Qt User Interface Compiler version 6.2.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QMetaObject,
    QRect,
    Qt,
)
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QLineEdit,
)


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName("Dialog")
        Dialog.resize(308, 256)
        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.setGeometry(QRect(-70, 220, 341, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.groupBox = QGroupBox(Dialog)
        self.groupBox.setObjectName("groupBox")
        self.groupBox.setGeometry(QRect(10, 10, 281, 91))
        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName("label_3")
        self.label_3.setGeometry(QRect(10, 30, 51, 16))
        self.hostport = QLineEdit(self.groupBox)
        self.hostport.setObjectName("hostport")
        self.hostport.setGeometry(QRect(70, 30, 191, 20))
        self.token = QLineEdit(self.groupBox)
        self.token.setObjectName("token")
        self.token.setGeometry(QRect(70, 60, 191, 20))
        self.label_4 = QLabel(self.groupBox)
        self.label_4.setObjectName("label_4")
        self.label_4.setGeometry(QRect(10, 60, 31, 16))
        self.groupBox_2 = QGroupBox(Dialog)
        self.groupBox_2.setObjectName("groupBox_2")
        self.groupBox_2.setGeometry(QRect(10, 110, 281, 101))
        self.include = QLineEdit(self.groupBox_2)
        self.include.setObjectName("include")
        self.include.setGeometry(QRect(70, 30, 191, 20))
        self.exclude = QLineEdit(self.groupBox_2)
        self.exclude.setObjectName("exclude")
        self.exclude.setGeometry(QRect(70, 60, 191, 20))
        self.label = QLabel(self.groupBox_2)
        self.label.setObjectName("label")
        self.label.setGeometry(QRect(10, 30, 54, 16))
        self.label_2 = QLabel(self.groupBox_2)
        self.label_2.setObjectName("label_2")
        self.label_2.setGeometry(QRect(10, 60, 54, 16))

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)

    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", "Dialog", None))
        self.groupBox.setTitle(QCoreApplication.translate("Dialog", "clash client", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", "host:port", None))
        self.label_4.setText(QCoreApplication.translate("Dialog", "token", None))
        self.groupBox_2.setTitle(
            QCoreApplication.translate("Dialog", "\u8282\u70b9\u8fc7\u6ee4", None)
        )
        self.label.setText(QCoreApplication.translate("Dialog", "\u5305\u542b", None))
        self.label_2.setText(QCoreApplication.translate("Dialog", "\u6392\u9664", None))

    # retranslateUi
