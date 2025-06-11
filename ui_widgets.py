#!/usr/bin/env python3
from PyQt5 import QtWidgets, QtGui, QtCore
from datetime import datetime # For VirtualTreeWidget sorting

class SortableTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    def __lt__(self, other):
        tree_widget = self.treeWidget()
        if not tree_widget:
            return self.text(0).lower() < other.text(0).lower()
        column = tree_widget.sortColumn()
        try:
            if column == 1:  # Count column
                return int(self.text(column)) < int(other.text(column))
            val1_str = self.text(column)
            val2_str = other.text(column)
            try:
                val1_num = float(val1_str)
                val2_num = float(val2_str)
                return val1_num < val2_num
            except ValueError:
                return val1_str.lower() < val2_str.lower()
        except (ValueError, AttributeError):
            return self.text(column).lower() < other.text(column).lower()


class LoadingDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading Log File")
        self.setMinimumSize(350, 120)
        self.setWindowFlags(
            QtCore.Qt.Dialog | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)  # No close button
        layout = QtWidgets.QVBoxLayout(self)
        self.status_label = QtWidgets.QLabel("Initializing...")
        layout.addWidget(self.status_label)
        self.detail_label = QtWidgets.QLabel("")
        self.detail_label.setStyleSheet("font-size: 10px; color: gray;")
        layout.addWidget(self.detail_label)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate by default
        layout.addWidget(self.progress_bar)
        # No explicit cancel button here, cancellation handled by LogAnalyzerApp.closeEvent if user closes main window

    def set_status(self, status_text):
        self.status_label.setText(status_text)

    def set_detail(self, detail_text):
        self.detail_label.setText(detail_text)

    def set_progress_range(self, min_val, max_val):
        self.progress_bar.setRange(min_val, max_val)
        
    def update_status(self, status_text, detail_text=""):
        """Update both status and detail in one call"""
        self.set_status(status_text)
        if detail_text:
            self.set_detail(detail_text)

    def set_progress_value(self, value):
        self.progress_bar.setValue(value)


class VirtualTreeWidget(QtWidgets.QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_items_data = []  # List of dicts
        self.filtered_items_data = []  # List of dicts (subset of all_items_data)
        self.visible_items = []  # List of QTreeWidgetItem currently in the tree
        self.items_per_page = 1000  # How many items to load at once
        self.current_page = 0
        self.search_filter = ""
        self.current_sort_column = -1  # No sort initially
        self.current_sort_order = QtCore.Qt.AscendingOrder

        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.header().sortIndicatorChanged.connect(self.on_sort_indicator_changed)

    def set_all_items_data(self, items_data):
        self.all_items_data = items_data
        self.apply_search_filter(self.search_filter, force_refresh=True)  # Re-apply current filter or show all

    def _sort_filtered_data(self):
        if not self.filtered_items_data or self.current_sort_column == -1:
            return

        col_idx = self.current_sort_column
        reverse_sort = (self.current_sort_order == QtCore.Qt.DescendingOrder)

        # Define how to get a sortable value from the item data dictionary
        def get_value_for_sort(item_data_dict):
            if col_idx == 0:  # Time column
                # Prefer datetime_obj for sorting if available and valid
                dt_obj = item_data_dict.get('datetime_obj')
                if isinstance(dt_obj, datetime) and dt_obj != datetime.min:
                    return dt_obj
                return item_data_dict.get('datetime', "")  # Fallback to string
            elif col_idx == 1:  # Level column
                return item_data_dict.get('log_level', "").lower()
            elif col_idx == 2:  # Logger column
                return item_data_dict.get('logger_name', "").lower()
            elif col_idx == 3:  # Message column (sort by first line)
                msg = item_data_dict.get('message', "")
                return (msg.split('\n')[0].lower() if msg else "")
            # Fallback for any other unexpected column index, though unlikely with fixed headers
            try:
                return item_data_dict.get(self.headerItem().text(col_idx), "").lower()
            except AttributeError:  # headerItem might not be set
                return ""

        try:
            self.filtered_items_data.sort(key=get_value_for_sort, reverse=reverse_sort)
        except TypeError:  # Fallback for mixed types (e.g. datetime vs string if obj is bad)
            self.filtered_items_data.sort(key=lambda x: str(get_value_for_sort(x)).lower(), reverse=reverse_sort)

    def on_sort_indicator_changed(self, logical_index, order):
        self.current_sort_column = logical_index
        self.current_sort_order = order
        self._sort_filtered_data()
        self.current_page = 0  # Reset to first page
        self._refresh_visible_items()

    def apply_search_filter(self, search_text, force_refresh=False):
        new_search_filter = search_text.lower()
        # Avoid re-filtering if text hasn't changed and data isn't forced,
        # unless previous filter resulted in self.filtered_items_data being a new list (not a slice)
        if not force_refresh and self.search_filter == new_search_filter and \
                self.filtered_items_data is not self.all_items_data:  # Check if it was actually filtered
            return

        self.search_filter = new_search_filter
        if not self.search_filter:
            self.filtered_items_data = self.all_items_data[:]  # Use a slice to ensure it's a mutable copy if needed
        else:
            self.filtered_items_data = [
                item for item in self.all_items_data
                if self.search_filter in item.get('message', '').lower() or \
                   self.search_filter in item.get('logger_name', '').lower()
            ]
        self._sort_filtered_data()  # Re-sort after filtering
        self.current_page = 0  # Reset to first page
        self._refresh_visible_items()

    def _refresh_visible_items(self):
        self.clear()  # Remove all existing QTreeWidgetItems
        self.visible_items = []
        self.current_page = 0  # Reset pagination
        self._load_more_items()

    def _load_more_items(self):
        start_idx = self.current_page * self.items_per_page
        if start_idx >= len(self.filtered_items_data):
            return  # No more items to load

        end_idx = min(start_idx + self.items_per_page, len(self.filtered_items_data))
        new_q_items = []
        for i in range(start_idx, end_idx):
            entry = self.filtered_items_data[i]
            # Create QTreeWidgetItem with display data
            item = QtWidgets.QTreeWidgetItem([ # Using standard QTreeWidgetItem here, Sortable is for the other tree
                entry['datetime'],
                entry['log_level'],
                entry['logger_name'],
                entry['message'].split('\n')[0]  # Show only first line in tree
            ])
            item.setData(0, QtCore.Qt.UserRole, entry)  # Store full entry data

        # Set text color based on log level
            log_level = entry.get('log_level', '').upper()
            color = None
            if log_level == 'ERROR':
                color = QtGui.QColor("red")
            elif log_level == 'WARN':
                color = QtGui.QColor("orange")
            elif log_level == 'DEBUG':
                color = QtGui.QColor("gray")
            # INFO and other levels will use default color (no explicit set needed or use black)
            # else: # Optional: Explicitly set INFO to black
            #     color = QtGui.QColor("black")

            if color:
                for col in range(item.columnCount()):
                    item.setForeground(col, QtGui.QBrush(color))

            new_q_items.append(item)

        if new_q_items:
            self.addTopLevelItems(new_q_items)
            self.visible_items.extend(new_q_items)
            self.current_page += 1

    def _on_scroll(self, value):
        scrollbar = self.verticalScrollBar()
        # Load more if near the bottom and more data is available
        if (scrollbar.maximum() > 0 and value >= scrollbar.maximum() * 0.8 and
                len(self.visible_items) < len(self.filtered_items_data)):
            self._load_more_items()


class SearchWidget(QtWidgets.QWidget):
    search_changed = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, placeholder_text=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self);
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)  # Consistent spacing for the layout elements

        layout.addWidget(QtWidgets.QLabel("🔍"))  # Search icon

        self.search_input = QtWidgets.QLineEdit();
        if placeholder_text:
            self.search_input.setPlaceholderText(placeholder_text)
        else:
            self.search_input.setPlaceholderText("Search messages and logger names...") # Default if none provided
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_text_changed_debounced)
        layout.addWidget(self.search_input)

        self.clear_button = QtWidgets.QPushButton("✕");
        self.clear_button.setFixedSize(24, 24)  # Small, square button
        self.clear_button.setToolTip("Clear search");
        self.clear_button.clicked.connect(self.clear_search)
        layout.addWidget(self.clear_button)

        # Timer for debouncing search input
        self.search_timer = QtCore.QTimer();
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._emit_search_changed)

        self.clear_button = QtWidgets.QPushButton("✕");
        self.clear_button.setFixedSize(24, 24)  # Small, square button
        self.clear_button.setToolTip("Clear search");
        self.clear_button.clicked.connect(self.clear_search)
        layout.addWidget(self.clear_button)


    def _on_text_changed_debounced(self, text): self.search_timer.stop(); self.search_timer.start(300)  # 300ms debounce

    def _emit_search_changed(self): self.search_changed.emit(self.search_input.text())

    def clear_search(self): self.search_input.clear()  # This will trigger textChanged -> search_changed


class WelcomeWidget(QtWidgets.QWidget):
    """A welcome widget displayed on application startup."""
    load_file_requested = QtCore.pyqtSignal()
    load_archive_requested = QtCore.pyqtSignal()

    def __init__(self, version="N/A", parent=None):
        super().__init__(parent)
        self.version = version
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        title_label = QtWidgets.QLabel("Timeline Log Analyzer")
        title_font = title_label.font()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title_label)

        version_label = QtWidgets.QLabel(f"Version {self.version}")
        version_font = version_label.font()
        version_font.setPointSize(10)
        version_label.setFont(version_font)
        version_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(version_label)

        layout.addSpacerItem(QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        load_file_button = QtWidgets.QPushButton("Load Single Log File")
        load_file_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))
        load_file_button.setMinimumHeight(40)
        load_file_button.clicked.connect(self.load_file_requested)
        layout.addWidget(load_file_button)

        load_archive_button = QtWidgets.QPushButton("Load Log Archive (.zip)")
        load_archive_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon)) # Using DirIcon as a proxy for archive
        load_archive_button.setMinimumHeight(40)
        load_archive_button.clicked.connect(self.load_archive_requested)
        layout.addWidget(load_archive_button)

        layout.addSpacerItem(QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        # Style buttons for better appearance
        button_style = """
            QPushButton {
                font-size: 14px;
                padding: 10px;
                margin: 5px;
            }
        """
        load_file_button.setStyleSheet(button_style)
        load_archive_button.setStyleSheet(button_style)

        self.setStyleSheet("background-color: #f0f0f0;") # Light gray background for the widget


class AboutDialog(QtWidgets.QDialog):
    """A dialog to show application information."""
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Timeline Log Analyzer")
        self.setFixedSize(450, 250)

        self.easter_egg_clicks = 0

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Title with icon
        title_label = QtWidgets.QLabel("📊 Timeline iObeya Log Analyzer")
        title_font = title_label.font()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title_label)

        # Version
        version_label = QtWidgets.QLabel(f"Version {version}")
        version_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(version_label)

        layout.addStretch(1)

        # Coder label (for the easter egg)
        self.coder_label = QtWidgets.QLabel("Vibe coded with ♊ Gemini and 🏄 Windsurf")
        self.coder_label.setAlignment(QtCore.Qt.AlignCenter)
        self.coder_label.setToolTip("...mostly but not only. Click me!")
        # Override the mousePressEvent to detect clicks for the easter egg
        self.coder_label.mousePressEvent = self.coder_label_clicked
        layout.addWidget(self.coder_label)

        layout.addStretch(1)

        # Copyright
        copyright_label = QtWidgets.QLabel("© Copyright iObeya")
        copyright_label.setAlignment(QtCore.Qt.AlignCenter)
        copyright_font = copyright_label.font()
        copyright_font.setPointSize(9)
        copyright_label.setFont(copyright_font)
        layout.addWidget(copyright_label)

        # Close button
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def coder_label_clicked(self, event):
        """Handle clicks on the label to trigger the easter egg."""
        self.easter_egg_clicks += 1
        if self.easter_egg_clicks >= 5:
            self.coder_label.setText("🚀 To infinity and beyond! 🚀")
            self.coder_label.setToolTip("You found it!")