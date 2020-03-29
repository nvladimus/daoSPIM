"""
Interface for abstraction of several PyQt widgets, to speed up GUI development in new modules.
Copyright Nikita Vladimirov, @nvladimus 2020
"""

from PyQt5.QtWidgets import (QGroupBox, QLineEdit, QPushButton, QTabWidget, QCheckBox,
                             QVBoxLayout, QWidget, QDoubleSpinBox, QFormLayout)
from PyQt5.QtCore import QLocale


class widget(QWidget):
    """Base class for GUI widgets."""
    def __init__(self, title='Control window'):
        """
        Parameters:
        :param title: str
        """
        super().__init__()
        self.setWindowTitle(title)
        self.containers = {}
        self.inputs = {}
        self.layouts = {}
        self.layout_window = QVBoxLayout(self)

    def add_groupbox(self, title='Group 1', parent=None):
        """ Add a groupbox widget.
        Parameters
        :param title: str
        :param parent: str
                Name of the existing parent container. If None (default), the widget is added directly
                to the main window.
        """
        assert title not in self.containers, "Container name already exists"
        new_widget = QGroupBox(title)
        self.containers[title] = new_widget
        self.layouts[title] = QFormLayout()
        self.containers[title].setLayout(self.layouts[title])
        if parent is None:
            self.layout_window.addWidget(new_widget)
        else:
            assert parent in self.layouts, "Parent container name not found: " + parent + "\n"
            assert title not in self.inputs, "Widget name already exists: " + title + "\n"
            self.layouts[parent].addWidget(new_widget)

    def add_tabs(self, title, tabs=['Tab1', 'Tab2']):
        """Add tabs widget
        Parameters:
            :param title: str
                A unique string ID for this group of tabs
            :param tabs: list of str,
                Names of tabs, e.g. ['Tab1', 'Tab2']
        """
        assert len(tabs) > 0, "Define the list of tab names (len > 1)"
        assert title not in self.containers, "Container name already exists:" + title + "\n"
        for tab_name in tabs:
            assert tab_name not in self.containers, "Container name already exists:" + tab_name + "\n"
        new_widget = QTabWidget()
        self.containers[title] = new_widget
        self.layout_window.addWidget(new_widget)
        for i in range(len(tabs)):
            new_tab = QWidget()
            self.containers[title].addTab(new_tab, tabs[i])
            self.containers[tabs[i]] = new_tab
            self.layouts[tabs[i]] = QFormLayout()
            self.containers[tabs[i]].setLayout(self.layouts[tabs[i]])

    def add_numeric_field(self, title, parent, value=0, vmin=0, vmax=100,
                          enabled=True, decimals=1, func=None, **func_args):
        """Add a QDoubleSpinBox() widget to the parent container widget (groupbox or tab).
        Parameters
            :param title: str
                Label of the parameter. Also, serves as system name of the widget. Beware of typos!
            :param parent: str
                Name of the parent container
            :param value: float
                Initial value of the field.
            :param func: function reference
                Name of the function which must be called every time the value is changed.
            :param: **func_args:
                Function's additional key-value parameters (dictionary), besides the field value.
        """
        assert parent in self.layouts, "Parent container name not found: " + parent + "\n"
        assert title not in self.inputs, "Widget name already exists: " + title + "\n"
        self.inputs[title] = QDoubleSpinBox()
        self.inputs[title].setLocale(QLocale(QLocale.English, QLocale.UnitedStates)) # comma -> period: 0,1 -> 0.1
        self.inputs[title].setDecimals(decimals)
        self.inputs[title].setRange(vmin, vmax)
        self.inputs[title].setValue(value)
        self.inputs[title].setEnabled(enabled)
        self.layouts[parent].addRow(title, self.inputs[title])
        if enabled and func is not None:
            self.inputs[title].editingFinished.connect(lambda: func(self.inputs[title].value(), **func_args))

    def add_string_field(self, title, parent, value='', enabled=True, func=None):
        """ Add a QLineEdit() widget to the parent container widget (groupbox or tab).
        :param title: str
                Label of the parameter. Also, serves as system name of the widget. Beware of typos!
        :param parent: str
                Name of the parent container
        :param value: str
                Initial value of the field.
        :param enabled: bool
            If True, user can edit value.
        :param func: function reference
                Name of the function which must be called every time the value is changed.
        :return: None
        """
        assert parent in self.layouts, "Parent container name not found: " + parent + "\n"
        assert title not in self.inputs, "Widget name already exists: " + title + "\n"
        self.inputs[title] = QLineEdit(value)
        self.inputs[title].setEnabled(enabled)
        self.layouts[parent].addRow(title, self.inputs[title])
        if enabled and func is not None:
            self.inputs[title].editingFinished.connect(lambda: func(self.inputs[title].text()))

    def add_button(self, title, parent, func):
        """Add a button to a parent container widget (groupbox or tab).
            Parameters
            :param title: str
                Name of the button. Also, serves as system name of the widget. Beware of typos!
            :param parent: str
                Name of the parent container.
            :param: func: function reference
                Name of the function that is executed on button click.
        """
        assert parent in self.layouts, "Parent container name not found: " + parent + "\n"
        assert title not in self.inputs, "Button name already exists: " + title + "\n"
        self.inputs[title] = QPushButton(title)
        self.inputs[title].clicked.connect(func)
        self.layouts[parent].addRow(self.inputs[title])

    def add_checkbox(self, title, parent, value=False, enabled=True, func=None):
        """Add a checkbox to a parent container widget (groupbox or tab).
            Parameters
            :param title: str
                Name of the checkbox. Also, serves as system name of the widget. Beware of typos!
            :param parent: str
                Name of the parent container.
            :param value: Boolean
            :param: enabled: Boolean
            :param: func: function reference
                Name of the function that is executed on button click.
        """
        assert parent in self.layouts, "Parent container name not found: " + parent + "\n"
        assert title not in self.inputs, "Button name already exists: " + title + "\n"
        self.inputs[title] = QCheckBox(title)
        self.inputs[title].setChecked(value)
        self.inputs[title].setEnabled(enabled)
        if enabled and func is not None:
            self.inputs[title].stateChanged.connect(lambda: func(self.inputs[title].isChecked()))
        self.layouts[parent].addRow(self.inputs[title])

    def update_numeric_field(self, title, value):
        assert title in self.inputs, "Numeric field not found: " + title + "\n"
        self.inputs[title].setValue(value)

    def update_string_field(self, title, text):
        assert title in self.inputs, "Text field not found: " + title + "\n"
        self.inputs[title].setText(text)