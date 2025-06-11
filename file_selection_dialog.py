from PyQt5 import QtWidgets, QtCore
from datetime import datetime

class FileSelectionDialog(QtWidgets.QDialog):
    def __init__(self, file_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Files to Analyze")
        # Sort data by date, which is expected to be a datetime.date object
        self.file_data = sorted(file_data, key=lambda x: x['date'])
        
        self.init_ui()
        self.populate_file_list()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.setMinimumSize(600, 400)

        # Date range filter
        date_range_layout = QtWidgets.QHBoxLayout()
        self.start_date_edit = QtWidgets.QDateEdit(calendarPopup=True)
        self.end_date_edit = QtWidgets.QDateEdit(calendarPopup=True)
        date_range_layout.addWidget(QtWidgets.QLabel("From:"))
        date_range_layout.addWidget(self.start_date_edit)
        date_range_layout.addWidget(QtWidgets.QLabel("To:"))
        date_range_layout.addWidget(self.end_date_edit)
        date_range_layout.addStretch()
        layout.addLayout(date_range_layout)

        # File list
        self.file_list_widget = QtWidgets.QTreeWidget()
        self.file_list_widget.setHeaderLabels(["Select", "Day", "Date", "Filename"])
        self.file_list_widget.header().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.file_list_widget)

        # Selection buttons
        selection_layout = QtWidgets.QHBoxLayout()
        select_all_btn = QtWidgets.QPushButton("Select All Visible")
        deselect_all_btn = QtWidgets.QPushButton("Deselect All Visible")
        selection_layout.addWidget(select_all_btn)
        selection_layout.addWidget(deselect_all_btn)
        selection_layout.addStretch()
        layout.addLayout(selection_layout)

        # OK/Cancel buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(button_box)

        # Connections
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn.clicked.connect(self.deselect_all)
        self.start_date_edit.dateChanged.connect(self.filter_list_by_date)
        self.end_date_edit.dateChanged.connect(self.filter_list_by_date)

    def populate_file_list(self):
        self.file_list_widget.clear()
        if not self.file_data:
            self.start_date_edit.setDate(QtCore.QDate.currentDate())
            self.end_date_edit.setDate(QtCore.QDate.currentDate())
            return

        min_date = self.file_data[0]['date']
        max_date = self.file_data[-1]['date']
        
        self.start_date_edit.setDate(QtCore.QDate(min_date.year, min_date.month, min_date.day))
        self.end_date_edit.setDate(QtCore.QDate(max_date.year, max_date.month, max_date.day))

        for file_info in self.file_data:
            date_obj = file_info['date']
            day_of_week = date_obj.strftime('%A')
            date_str = date_obj.strftime('%Y-%m-%d')
            
            item = QtWidgets.QTreeWidgetItem([
                "",  # Checkbox placeholder
                day_of_week,
                date_str,
                file_info['filename']
            ])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(0, QtCore.Qt.Checked)
            item.setData(0, QtCore.Qt.UserRole, file_info) # Store original data
            self.file_list_widget.addTopLevelItem(item)
        
        self.file_list_widget.resizeColumnToContents(0)
        self.file_list_widget.resizeColumnToContents(1)
        self.file_list_widget.resizeColumnToContents(2)

    def filter_list_by_date(self):
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()

        for i in range(self.file_list_widget.topLevelItemCount()):
            item = self.file_list_widget.topLevelItem(i)
            file_info = item.data(0, QtCore.Qt.UserRole)
            item_date = file_info['date']
            
            if start_date <= item_date <= end_date:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def select_all(self):
        for i in range(self.file_list_widget.topLevelItemCount()):
            item = self.file_list_widget.topLevelItem(i)
            if not item.isHidden():
                item.setCheckState(0, QtCore.Qt.Checked)

    def deselect_all(self):
        for i in range(self.file_list_widget.topLevelItemCount()):
            item = self.file_list_widget.topLevelItem(i)
            if not item.isHidden():
                item.setCheckState(0, QtCore.Qt.Unchecked)

    def get_selected_files(self):
        selected_files = []
        for i in range(self.file_list_widget.topLevelItemCount()):
            item = self.file_list_widget.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Checked:
                selected_files.append(item.data(0, QtCore.Qt.UserRole)['filename'])
        return selected_files
