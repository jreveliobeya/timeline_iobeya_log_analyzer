import re
import os
from PyQt5 import QtWidgets, QtCore
from datetime import datetime, timedelta

class DateSelectionDialog(QtWidgets.QDialog):
    """A dialog to select a date range to filter files from a zip archive."""

    def __init__(self, file_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Date Range")
        self.file_list = file_list
        self.file_dates = self._extract_dates_from_files()

        self.setup_ui()
        self.update_file_list()

    def _extract_dates_from_files(self):
        """Extracts dates from filenames using regex."""
        # Regex to find dates in YYYY-MM-DD format in filenames
        date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})')
        file_dates = {}
        future_date = datetime.now().date() + timedelta(days=1)

        for filename in self.file_list:
            if filename.startswith('__MACOSX/') or os.path.basename(filename).startswith('._') or not (filename.endswith('.log') or filename.endswith('.log.gz')):
                continue

            match = date_pattern.search(filename)
            if match:
                try:
                    date_obj = datetime.strptime(match.group(1), '%Y-%m-%d').date()
                    file_dates[filename] = date_obj
                except ValueError:
                    file_dates[filename] = future_date # Assign future date if parsing fails
            else:
                # If no date is in the filename, assign the future date
                file_dates[filename] = future_date

        return file_dates

    def setup_ui(self):
        """Sets up the UI components of the dialog."""
        layout = QtWidgets.QVBoxLayout(self)

        # Filter and Date selectors
        filter_layout = QtWidgets.QHBoxLayout()
        self.filter_combo = QtWidgets.QComboBox()
        self.filter_combo.addItems(["All Logs", "Application Logs (app*)", "Error Logs (error*)"])
        filter_layout.addWidget(QtWidgets.QLabel("Filter by type:"))
        filter_layout.addWidget(self.filter_combo)
        layout.addLayout(filter_layout)

        form_layout = QtWidgets.QFormLayout()
        self.start_date_edit = QtWidgets.QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.end_date_edit = QtWidgets.QDateEdit()
        self.end_date_edit.setCalendarPopup(True)

        if self.file_dates:
            min_date = min(self.file_dates.values())
            max_date = max(self.file_dates.values())
            self.start_date_edit.setDate(QtCore.QDate(min_date.year, min_date.month, min_date.day))
            self.end_date_edit.setDate(QtCore.QDate(max_date.year, max_date.month, max_date.day))

        form_layout.addRow("Start Date:", self.start_date_edit)
        form_layout.addRow("End Date:", self.end_date_edit)
        layout.addLayout(form_layout)

        # File list
        self.files_list_widget = QtWidgets.QListWidget()
        layout.addWidget(self.files_list_widget)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Connect signals
        self.start_date_edit.dateChanged.connect(self.update_file_list)
        self.end_date_edit.dateChanged.connect(self.update_file_list)
        self.filter_combo.currentIndexChanged.connect(self.update_file_list)

    def update_file_list(self):
        """Updates the list of files based on the selected date range."""
        self.files_list_widget.clear()
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        filter_text = self.filter_combo.currentText()

        for filename, file_date in sorted(self.file_dates.items()):
            # Date filter
            if not (start_date <= file_date <= end_date):
                continue

            # Filename filter
            basename = os.path.basename(filename)
            if "Application Logs" in filter_text and not basename.startswith('app'):
                continue
            if "Error Logs" in filter_text and not basename.startswith('error'):
                continue

            self.files_list_widget.addItem(filename)

    def get_selected_files(self):
        """Returns the list of files that are currently visible in the list widget."""
        return [self.files_list_widget.item(i).text() for i in range(self.files_list_widget.count())]
