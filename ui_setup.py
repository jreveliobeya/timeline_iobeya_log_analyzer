# ui_setup.py
from PyQt5 import QtWidgets, QtGui, QtCore
from timeline_canvas import TimelineCanvas
from ui_widgets import VirtualTreeWidget, SearchWidget
from datetime import datetime


class DateRangeDialog(QtWidgets.QDialog):
    def __init__(self, parent, min_date, max_date):
        super().__init__(parent)
        self.setWindowTitle("Sélectionner une plage de dates")
        layout = QtWidgets.QVBoxLayout(self)
        hbox = QtWidgets.QHBoxLayout()
        self.start_calendar = QtWidgets.QCalendarWidget()
        self.end_calendar = QtWidgets.QCalendarWidget()
        self.start_calendar.setMinimumDate(min_date)
        self.start_calendar.setMaximumDate(max_date)
        self.end_calendar.setMinimumDate(min_date)
        self.end_calendar.setMaximumDate(max_date)
        self.start_calendar.setSelectedDate(min_date)
        self.end_calendar.setSelectedDate(max_date)
        hbox.addWidget(self.start_calendar)
        hbox.addWidget(self.end_calendar)
        layout.addLayout(hbox)
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_range(self):
        return self.start_calendar.selectedDate(), self.end_calendar.selectedDate()


class UiSetup:
    def __init__(self, main_window, app_logic_instance):  # <--- RECEVOIR app_logic_instance
        self.mw = main_window
        self.app_logic = app_logic_instance  # <--- STOCKER app_logic_instance

        self._setup_main_widget_and_layout()

        self._create_menu_bar()
        self._create_toolbar()

        self._create_timeline_section()
        self._create_message_types_panel()
        self._create_right_panel()

        self._arrange_splitters()

        # La statusBar est créée et assignée dans LogAnalyzerApp.__init__ après appel à UiSetup
        # ou directement dans LogAnalyzerApp.setup_ui si vous préférez

        # Connect calendar button
        self.mw.calendar_btn.clicked.connect(self._open_calendar_dialog)

    def _setup_main_widget_and_layout(self):
        # Always use a central widget with a layout for QMainWindow
        self.mw.central_widget = QtWidgets.QWidget()
        self.mw.setCentralWidget(self.mw.central_widget)
        self.mw.main_layout = QtWidgets.QVBoxLayout(self.mw.central_widget)
        self.mw.main_layout.setContentsMargins(0, 0, 0, 0)
        self.mw.main_layout.setSpacing(0)

    def _create_menu_bar(self):
        menu_bar = self.mw.menuBar()

        file_menu = menu_bar.addMenu("&Fichier")
        load_file_action_menu = QtWidgets.QAction("Charger Fichier Log...", self.mw)
        load_file_action_menu.setShortcut(QtGui.QKeySequence.Open)
        load_file_action_menu.triggered.connect(self.mw.load_log_file)
        file_menu.addAction(load_file_action_menu)

        load_archive_action_menu = QtWidgets.QAction("Charger Archive Log (.zip)...", self.mw)
        load_archive_action_menu.triggered.connect(self.mw.load_log_archive)
        file_menu.addAction(load_archive_action_menu)
        file_menu.addSeparator()
        exit_action = QtWidgets.QAction("Quitter", self.mw)
        exit_action.setShortcut(QtGui.QKeySequence.Quit)
        exit_action.triggered.connect(self.mw.close)
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("&Affichage")

        self.mw.dark_mode_action = QtWidgets.QAction("Mode Sombre", self.mw, checkable=True)
        self.mw.dark_mode_action.setChecked(self.mw.is_dark_mode)
        self.mw.dark_mode_action.triggered.connect(self.mw.toggle_dark_mode)
        view_menu.addAction(self.mw.dark_mode_action)

        view_menu.addSeparator()
        reset_view_action_menu = QtWidgets.QAction("Réinitialiser Vue", self.mw)
        reset_view_action_menu.triggered.connect(lambda: self.app_logic.reset_all_filters_and_view(initial_load=False))
        view_menu.addAction(reset_view_action_menu)

    def _create_toolbar(self):
        toolbar = self.mw.addToolBar("Outils")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QtCore.QSize(20, 20))
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        load_file_tb_action = QtWidgets.QAction(QtGui.QIcon.fromTheme("document-open", QtGui.QIcon(
            ":/qt-project.org/styles/commonstyle/images/fileopen.png")), "Charger Fichier", self.mw)
        load_file_tb_action.triggered.connect(self.mw.load_log_file)
        toolbar.addAction(load_file_tb_action)

        load_archive_tb_action = QtWidgets.QAction(QtGui.QIcon.fromTheme("document-open-archive", QtGui.QIcon(
            ":/qt-project.org/styles/commonstyle/images/ark.png")), "Charger Archive", self.mw)
        load_archive_tb_action.triggered.connect(self.mw.load_log_archive)
        toolbar.addAction(load_archive_tb_action)

        toolbar.addSeparator()
        reset_view_tb_action = QtWidgets.QAction(QtGui.QIcon.fromTheme("view-refresh", QtGui.QIcon(
            ":/qt-project.org/styles/commonstyle/images/refresh.png")), "Réinitialiser", self.mw)
        reset_view_tb_action.setToolTip("Réinitialiser tous les filtres et le zoom")
        reset_view_tb_action.triggered.connect(lambda: self.app_logic.reset_all_filters_and_view(initial_load=False))
        toolbar.addAction(reset_view_tb_action)
        toolbar.addSeparator()

        summary_widget_container = QtWidgets.QWidget()
        summary_layout = QtWidgets.QHBoxLayout(summary_widget_container)
        summary_layout.setContentsMargins(8, 2, 8, 2)
        summary_layout.setSpacing(8)

        self.mw.period_label = QtWidgets.QLabel("Pas de log chargé")
        self.mw.period_label.setObjectName("periodLabel")
        summary_layout.addWidget(QtWidgets.QLabel("📅"))
        summary_layout.addWidget(self.mw.period_label)

        # Add calendar button next to period label
        self.mw.calendar_btn = QtWidgets.QPushButton()
        self.mw.calendar_btn.setIcon(QtGui.QIcon.fromTheme("calendar", QtGui.QIcon(":/qt-project.org/styles/commonstyle/images/qtlogo-64.png")))
        self.mw.calendar_btn.setToolTip("Filtrer par plage de dates")
        summary_layout.addWidget(self.mw.calendar_btn)

        self.mw.stats_button = QtWidgets.QPushButton("📊")
        self.mw.stats_button.setObjectName("statsButton")
        self.mw.stats_button.setToolTip("Afficher les statistiques globales")
        self.mw.stats_button.clicked.connect(self.mw.show_stats_panel)
        summary_layout.addWidget(self.mw.stats_button)

        self.mw.total_label = QtWidgets.QLabel("0 entrées")
        self.mw.total_label.setObjectName("totalLabel")
        summary_layout.addWidget(self.mw.total_label)

        self.mw.error_btn = QtWidgets.QPushButton("ERROR: 0")
        self.mw.error_btn.setObjectName("errorButton")
        self.mw.error_btn.clicked.connect(lambda: self.app_logic.filter_by_specific_level('ERROR'))
        summary_layout.addWidget(self.mw.error_btn)

        self.mw.warn_btn = QtWidgets.QPushButton("WARN: 0")
        self.mw.warn_btn.setObjectName("warnButton")
        self.mw.warn_btn.clicked.connect(lambda: self.app_logic.filter_by_specific_level('WARN'))
        summary_layout.addWidget(self.mw.warn_btn)

        self.mw.info_btn = QtWidgets.QPushButton("INFO: 0")
        self.mw.info_btn.setObjectName("infoButton")
        self.mw.info_btn.clicked.connect(lambda: self.app_logic.filter_by_specific_level('INFO'))
        summary_layout.addWidget(self.mw.info_btn)

        self.mw.debug_btn = QtWidgets.QPushButton("DEBUG: 0")
        self.mw.debug_btn.setObjectName("debugButton")
        self.mw.debug_btn.clicked.connect(lambda: self.app_logic.filter_by_specific_level('DEBUG'))
        summary_layout.addWidget(self.mw.debug_btn)
        summary_layout.addStretch()

        summary_widget_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        toolbar.addWidget(summary_widget_container)

    def _create_timeline_section(self):
        self.mw.timeline_section_widget = QtWidgets.QWidget()
        self.mw.timeline_section_widget.setMinimumHeight(200)
        timeline_layout = QtWidgets.QVBoxLayout(self.mw.timeline_section_widget)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(0)

        # Create timeline canvas
        self.mw.timeline_canvas = TimelineCanvas(self.mw)
        self.mw.timeline_canvas.bar_clicked.connect(self.app_logic.on_timeline_bar_clicked)
        timeline_layout.addWidget(self.mw.timeline_canvas)

        # Create controls panel
        controls_panel = QtWidgets.QWidget()
        controls_layout = QtWidgets.QHBoxLayout(controls_panel)
        controls_layout.setContentsMargins(8, 4, 8, 4)
        controls_layout.setSpacing(8)

        # Add left arrow button
        self.mw.left_arrow_btn = QtWidgets.QPushButton("←")
        self.mw.left_arrow_btn.setToolTip("Déplacer la timeline vers la gauche")
        controls_layout.addWidget(self.mw.left_arrow_btn)
        self.mw.left_arrow_btn.clicked.connect(self.app_logic.pan_timeline_left)

        # Add radio buttons for granularity
        granularity_group = QtWidgets.QButtonGroup(controls_panel)
        self.mw.granularity_radios = {}
        for label in [("minute", "Minute"), ("hour", "Heure"), ("day", "Jour"), ("week", "Semaine")]:
            radio = QtWidgets.QRadioButton(label[1])
            granularity_group.addButton(radio)
            controls_layout.addWidget(radio)
            self.mw.granularity_radios[label[0]] = radio
        self.mw.granularity_radios["minute"].setChecked(True)
        granularity_group.buttonClicked.connect(self._on_granularity_radio_changed)

        # Add right arrow button
        self.mw.right_arrow_btn = QtWidgets.QPushButton("→")
        self.mw.right_arrow_btn.setToolTip("Déplacer la timeline vers la droite")
        controls_layout.addWidget(self.mw.right_arrow_btn)
        self.mw.right_arrow_btn.clicked.connect(self.app_logic.pan_timeline_right)

        timeline_layout.addWidget(controls_panel)
        self.mw.main_layout.addWidget(self.mw.timeline_section_widget)

    def _on_granularity_radio_changed(self, button):
        # Find which radio is checked and update granularity
        for key, radio in self.mw.granularity_radios.items():
            if radio.isChecked():
                self.app_logic.set_granularity(key)
                break

    def _create_message_types_panel(self):
        self.mw.message_types_panel = QtWidgets.QWidget()
        self.mw.message_types_panel.setMinimumWidth(200)
        layout = QtWidgets.QVBoxLayout(self.mw.message_types_panel)
        layout.setSpacing(4)

        search_layout = QtWidgets.QHBoxLayout()
        # Create the search input with explicit parent and store it in a class variable
        self.mw.message_type_search_input = QtWidgets.QLineEdit(self.mw.message_types_panel)
        self.mw.message_type_search_input.setObjectName("messageTypeSearchInput")  # Add object name for better tracking
        print(f"[UiSetup] self.mw.message_type_search_input CREATED: {self.mw.message_type_search_input} with parent: {self.mw.message_type_search_input.parent()}")
        self.mw.message_type_search_input.setPlaceholderText("Rechercher types de message...")
        self.mw.message_type_search_input.textChanged.connect(self.app_logic.on_message_type_search_changed_debounced)
        search_layout.addWidget(self.mw.message_type_search_input)

        # Create clear button with explicit parent
        message_type_search_clear_btn = QtWidgets.QPushButton("✕", self.mw.message_types_panel)
        message_type_search_clear_btn.setObjectName("messageTypeSearchClearBtn")
        message_type_search_clear_btn.setToolTip("Effacer la recherche")
        message_type_search_clear_btn.clicked.connect(self.mw.message_type_search_input.clear)
        search_layout.addWidget(message_type_search_clear_btn)

        layout.addLayout(search_layout)

        title_layout = QtWidgets.QHBoxLayout()
        title_label = QtWidgets.QLabel("<b>Types de Message</b>", self.mw.message_types_panel)  # <--- PARENT AJOUTÉ
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        select_top5_btn = QtWidgets.QPushButton("Top 5", self.mw.message_types_panel)  # <--- PARENT AJOUTÉ
        select_top5_btn.clicked.connect(self.app_logic.select_top5_message_types)
        select_top10_btn = QtWidgets.QPushButton("Top 10", self.mw.message_types_panel)  # <--- PARENT AJOUTÉ
        select_top10_btn.clicked.connect(self.app_logic.select_top10_message_types)
        select_all_visible_btn = QtWidgets.QPushButton("Sél. Visibles",
                                                       self.mw.message_types_panel)  # <--- PARENT AJOUTÉ
        select_all_visible_btn.setToolTip("Sélectionner tous les types visibles")
        select_all_visible_btn.clicked.connect(
            lambda: self.app_logic.set_check_state_for_visible_types(QtCore.Qt.Checked))
        deselect_all_btn = QtWidgets.QPushButton("Désél. Tout", self.mw.message_types_panel)  # <--- PARENT AJOUTÉ
        deselect_all_btn.setToolTip("Désélectionner tous les types")
        deselect_all_btn.clicked.connect(lambda: self.app_logic.set_check_state_for_all_types(QtCore.Qt.Unchecked))

        for btn in [select_top5_btn, select_top10_btn, select_all_visible_btn, deselect_all_btn]:
            title_layout.addWidget(btn)
        layout.addLayout(title_layout)

        self.mw.message_types_tree = QtWidgets.QTreeWidget(self.mw.message_types_panel)  # <--- PARENT AJOUTÉ
        self.mw.message_types_tree.setHeaderLabels(['Type de Message', 'Nombre'])
        self.mw.message_types_tree.setSortingEnabled(True)
        self.mw.message_types_tree.itemChanged.connect(self.app_logic.on_message_type_item_changed)
        header = self.mw.message_types_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.mw.message_types_tree.sortByColumn(1, QtCore.Qt.DescendingOrder)
        layout.addWidget(self.mw.message_types_tree)
        # Ajout temporaire pour debug visibilité
        layout.addWidget(QtWidgets.QLabel("Types de messages", self.mw.message_types_panel))

    def _create_right_panel(self):
        self.mw.right_panel = QtWidgets.QWidget()
        self.mw.right_panel.setMinimumWidth(300)
        layout = QtWidgets.QVBoxLayout(self.mw.right_panel)
        layout.setSpacing(4)

        self.mw.search_widget = SearchWidget()
        self.mw.search_widget.search_changed.connect(self.app_logic.on_search_changed)  # <--- CHANGÉ
        layout.addWidget(self.mw.search_widget)

        messages_label = QtWidgets.QLabel("<b>Messages dans l'Intervalle Sélectionné</b>")
        layout.addWidget(messages_label)
        self.mw.selected_messages_list = VirtualTreeWidget()
        self.mw.selected_messages_list.setHeaderLabels(['Heure', 'Niveau', 'Logger', 'Message'])
        self.mw.selected_messages_list.itemSelectionChanged.connect(self.app_logic.on_message_selected)  # <--- CHANGÉ
        self.mw.selected_messages_list.header().setSortIndicator(0, QtCore.Qt.AscendingOrder)
        layout.addWidget(self.mw.selected_messages_list)

        details_label = QtWidgets.QLabel("<b>Détails du Message</b>")
        layout.addWidget(details_label)
        self.mw.details_text = QtWidgets.QTextEdit()
        self.mw.details_text.setReadOnly(True)
        self.mw.details_text.setFontFamily("monospace")
        layout.addWidget(self.mw.details_text)
        # Ajout temporaire pour debug visibilité
        layout.addWidget(QtWidgets.QLabel("Panneau de droite", self.mw.right_panel))

    def _arrange_splitters(self):
        if not self.mw.timeline_section_widget or \
                not self.mw.message_types_panel or \
                not self.mw.right_panel:
            return

        self.mw.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.mw.main_splitter.addWidget(self.mw.timeline_section_widget)

        bottom_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bottom_splitter.addWidget(self.mw.message_types_panel)
        bottom_splitter.addWidget(self.mw.right_panel)
        bottom_splitter.setStretchFactor(0, 1)
        bottom_splitter.setStretchFactor(1, 3)

        self.mw.main_splitter.addWidget(bottom_splitter)
        self.mw.main_splitter.setStretchFactor(0, 1)
        self.mw.main_splitter.setStretchFactor(1, 2)

        # Remove all widgets from main_layout before adding (prevents duplicates)
        while self.mw.main_layout.count():
            item = self.mw.main_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self.mw.main_layout.addWidget(self.mw.main_splitter)

    def _open_calendar_dialog(self):
        # Determine min/max date from loaded logs
        entries = self.mw.log_entries_full
        if not entries:
            QtWidgets.QMessageBox.information(self.mw, "Aucune donnée", "Aucun log chargé.")
            return
        min_dt = min(e.get('datetime_obj') or datetime.strptime(e['datetime'], '%Y-%m-%d %H:%M:%S') for e in entries)
        max_dt = max(e.get('datetime_obj') or datetime.strptime(e['datetime'], '%Y-%m-%d %H:%M:%S') for e in entries)
        min_qdate = QtCore.QDate(min_dt.year, min_dt.month, min_dt.day)
        max_qdate = QtCore.QDate(max_dt.year, max_dt.month, max_dt.day)
        dlg = DateRangeDialog(self.mw, min_qdate, max_qdate)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            start_qdate, end_qdate = dlg.get_range()
            self._apply_date_filter(start_qdate, end_qdate)

    def _apply_date_filter(self, start_qdate, end_qdate):
        # Store the selected date range in the main window
        self.mw.date_filter_range = (start_qdate, end_qdate)
        # Trigger a view update (filtered data)
        self.app_logic.apply_date_filter_to_timeline()