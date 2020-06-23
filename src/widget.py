"""
Interface for abstraction of several PyQt widgets, to speed up GUI development in new modules.
Copyright Nikita Vladimirov, @nvladimus 2020
"""

from PyQt5.QtWidgets import (QGroupBox, QLineEdit, QPushButton, QTabWidget, QCheckBox, QComboBox,
                             QVBoxLayout, QWidget, QDoubleSpinBox, QFormLayout)
from PyQt5.QtCore import QLocale
import pyqtgraph as pg
import numpy as np

pg.setConfigOptions(antialias=True)  # Enable antialiasing for prettier plots


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
        self.windows = {}
        self.plots = {}
        self.image_views = {}
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

    def add_numeric_field(self, title, parent, value=0, vmin=-1e6, vmax=1e6,
                          enabled=True, decimals=0, func=None, **func_args):
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
        self.inputs[title].setSingleStep(1. / 10 ** decimals)
        self.inputs[title].setRange(vmin, vmax)
        self.inputs[title].setValue(value)
        self.inputs[title].setEnabled(enabled)
        self.layouts[parent].addRow(title, self.inputs[title])
        if enabled and func is not None:
            self.inputs[title].editingFinished.connect(lambda: func(self.inputs[title].value(), **func_args))
            # editingFinished() preferred over valueChanged() because the latter is too jumpy, doesn't let finish input.

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

    def add_combobox(self, title, parent, items=['Item1', 'Item2'], value='Item1', enabled=True, func=None):
        """Add a combobox to a parent container widget.
            Parameters
            :param title: str
                Name of the checkbox. Also, serves as system name of the widget. Beware of typos!
            :param parent: str
                Name of the parent container.
            :param items: list of strings (available options)
            :param value: currently selected option
            :param: enabled: Boolean
            :param: func: function reference
                Ref to the function executed when an item is changed.
        """
        assert parent in self.layouts, f"Parent title not found: {parent}"
        assert title not in self.inputs, f"Widget title already exists: {title}"
        assert value in items, f"Parameter value {value} does not match available options: {items}"
        self.inputs[title] = QComboBox()
        self.inputs[title].addItems(items)
        self.inputs[title].setEnabled(enabled)
        self.inputs[title].setCurrentText(value)
        if enabled and func is not None:
            self.inputs[title].currentTextChanged.connect(lambda: func(self.inputs[title].currentText()))
        self.layouts[parent].addRow(title, self.inputs[title])

    def add_window(self, title, size=(800, 600)):
        assert title not in self.inputs.keys(), f"Window title already exists: {title}"
        self.windows[title] = pg.GraphicsWindow()
        self.windows[title].resize(size[0], size[1])
        self.windows[title].setWindowTitle(title)

    def add_plot(self, title, parent, grid=True, color=(255, 255, 0)):
        assert parent in self.windows.keys(), f"Parent window title not found: {parent}"
        assert title not in self.plots.keys(), f"Plot title already exists: {title}"
        self.plots[title] = self.windows[parent].addPlot(title=title, y=np.random.normal(size=100), pen=color)
        self.plots[title].showGrid(x=grid, y=grid)

    def add_image_view(self, title, parent, size=(100, 200)):
        assert parent in self.windows.keys(), f"Parent window title not found: {parent}"
        assert title not in self.image_views.keys(), f"Plot title already exists: {title}"
        self.image_views[title] = pg.ImageView(name=title)
        img = pg.gaussianFilter(np.random.normal(size=size), (5, 5)) * 20 + 100
        self.image_views[title].setImage(img)
        self.windows[parent].addItem(self.image_views[title])

    def update_numeric_field(self, title, value):
        """"Deprecated"""
        assert title in self.inputs, "Numeric field not found: " + title + "\n"
        self.inputs[title].setValue(value)

    def update_string_field(self, title, text):
        """"Deprecated"""
        assert title in self.inputs, "Text field not found: " + title + "\n"
        self.inputs[title].setText(text)

    def update_param(self, title, value):
        assert title in self.inputs, f"{title} field not found"
        if isinstance(self.inputs[title], QDoubleSpinBox):
            self.inputs[title].setValue(value)
        elif isinstance(self.inputs[title], QLineEdit):
            self.inputs[title].setText(value)

    def update_plot(self, title, data):
        assert title in self.plots.keys(), f"{title} plot not found"
        pass

    def update_image_view(self, title, image):
        assert title in self.plots.keys(), f"{title} image view not found"
        pass
