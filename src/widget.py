"""
Interface for abstraction of several PyQt widgets, to speed up GUI development in new modules.
Copyright Nikita Vladimirov, @nvladimus 2020
"""

from PyQt5.QtWidgets import (QGroupBox, QLineEdit, QPushButton, QTabWidget, QCheckBox, QComboBox,
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

    def add_groupbox(self, label='Group 1', parent=None):
        """ Add a groupbox widget.
        Parameters
        :param label: str
        :param parent: str
                Name of the existing parent container. If None (default), the widget is added directly
                to the main window.
        """
        assert label not in self.containers, "Container name already exists"
        new_widget = QGroupBox(label)
        self.containers[label] = new_widget
        self.layouts[label] = QFormLayout()
        self.containers[label].setLayout(self.layouts[label])
        if parent is None:
            self.layout_window.addWidget(new_widget)
        else:
            assert parent in self.layouts, "Parent container name not found: " + parent + "\n"
            assert label not in self.inputs, "Widget name already exists: " + label + "\n"
            self.layouts[parent].addWidget(new_widget)

    def add_tabs(self, label, tabs=['Tab1', 'Tab2']):
        """Add tabs widget
        Parameters:
            :param label: str
                A unique string ID for this group of tabs
            :param tabs: list of str,
                Names of tabs, e.g. ['Tab1', 'Tab2']
        """
        assert len(tabs) > 0, "Define the list of tab names (len > 1)"
        assert label not in self.containers, "Container name already exists:" + label + "\n"
        for tab_name in tabs:
            assert tab_name not in self.containers, "Container name already exists:" + tab_name + "\n"
        new_widget = QTabWidget()
        self.containers[label] = new_widget
        self.layout_window.addWidget(new_widget)
        for i in range(len(tabs)):
            new_tab = QWidget()
            self.containers[label].addTab(new_tab, tabs[i])
            self.containers[tabs[i]] = new_tab
            self.layouts[tabs[i]] = QFormLayout()
            self.containers[tabs[i]].setLayout(self.layouts[tabs[i]])

    def add_numeric_field(self, label, parent, value=0, vmin=-1e6, vmax=1e6,
                          enabled=True, decimals=0, func=None, **func_args):
        """Add a QDoubleSpinBox() widget to the parent container widget (groupbox or tab).
        Parameters
            :param label: str
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
        assert label not in self.inputs, "Widget name already exists: " + label + "\n"
        self.inputs[label] = QDoubleSpinBox()
        self.inputs[label].setLocale(QLocale(QLocale.English, QLocale.UnitedStates)) # comma -> period: 0,1 -> 0.1
        self.inputs[label].setDecimals(decimals)
        self.inputs[label].setSingleStep(1. / 10 ** decimals)
        self.inputs[label].setRange(vmin, vmax)
        self.inputs[label].setValue(value)
        self.inputs[label].setEnabled(enabled)
        self.layouts[parent].addRow(label, self.inputs[label])
        if enabled and func is not None:
            self.inputs[label].editingFinished.connect(lambda: func(self.inputs[label].value(), **func_args))
            # editingFinished() preferred over valueChanged() because the latter is too jumpy, doesn't let finish input.

    def add_string_field(self, label, parent, value='', enabled=True, func=None):
        """ Add a QLineEdit() widget to the parent container widget (groupbox or tab).
        :param label: str
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
        assert label not in self.inputs, "Widget name already exists: " + label + "\n"
        self.inputs[label] = QLineEdit(value)
        self.inputs[label].setEnabled(enabled)
        self.layouts[parent].addRow(label, self.inputs[label])
        if enabled and func is not None:
            self.inputs[label].editingFinished.connect(lambda: func(self.inputs[label].text()))

    def add_button(self, label, parent, func):
        """Add a button to a parent container widget (groupbox or tab).
            Parameters
            :param label: str
                Name of the button. Also, serves as system name of the widget. Beware of typos!
            :param parent: str
                Name of the parent container.
            :param: func: function reference
                Name of the function that is executed on button click.
        """
        assert parent in self.layouts, "Parent container name not found: " + parent + "\n"
        assert label not in self.inputs, "Button name already exists: " + label + "\n"
        self.inputs[label] = QPushButton(label)
        self.inputs[label].clicked.connect(func)
        self.layouts[parent].addRow(self.inputs[label])

    def add_checkbox(self, label, parent, value=False, enabled=True, func=None):
        """Add a checkbox to a parent container widget (groupbox or tab).
            Parameters
            :param label: str
                Name of the checkbox. Also, serves as system name of the widget. Beware of typos!
            :param parent: str
                Name of the parent container.
            :param value: Boolean
            :param: enabled: Boolean
            :param: func: function reference
                Name of the function that is executed on button click.
        """
        assert parent in self.layouts, "Parent container name not found: " + parent + "\n"
        assert label not in self.inputs, "Button name already exists: " + label + "\n"
        self.inputs[label] = QCheckBox(label)
        self.inputs[label].setChecked(value)
        self.inputs[label].setEnabled(enabled)
        if enabled and func is not None:
            self.inputs[label].stateChanged.connect(lambda: func(self.inputs[label].isChecked()))
        self.layouts[parent].addRow(self.inputs[label])

    def add_combobox(self, title, parent, items=['Item1'], enabled=True, func=None):
        """Add a combobox to a parent container widget.
            Parameters
            :param title: str
                Name of the checkbox. Also, serves as system name of the widget. Beware of typos!
            :param parent: str
                Name of the parent container.
            :param items: list of strings
            :param: enabled: Boolean
            :param: func: function reference
                Ref to the function executed when an item is changed.
        """
        assert parent in self.layouts, "Parent container name not found: " + parent + "\n"
        assert title not in self.inputs, "Widget name already exists: " + title + "\n"
        self.inputs[title] = QComboBox()
        self.inputs[title].addItems(items)
        self.inputs[title].setEnabled(enabled)
        if enabled and func is not None:
            self.inputs[title].currentTextChanged.connect(lambda: func(self.inputs[title].currentText()))
        self.layouts[parent].addRow(title, self.inputs[title])

    def update_numeric_field(self, title, value):
        """"Deprecated"""
        assert title in self.inputs, "Numeric field not found: " + title + "\n"
        self.inputs[title].setValue(value)

    def update_string_field(self, title, text):
        """"Deprecated"""
        assert title in self.inputs, "Text field not found: " + title + "\n"
        self.inputs[title].setText(text)

    def update(self, title, value):
        assert title in self.inputs, f"{title} field not found"
        if isinstance(self.inputs[title], QDoubleSpinBox):
            self.inputs[title].setValue(value)
        elif isinstance(self.inputs[title], QLineEdit):
            self.inputs[title].setText(value)
