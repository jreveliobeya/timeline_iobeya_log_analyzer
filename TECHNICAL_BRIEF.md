# Technical Brief: iObeya Timeline Log Analyzer

## 1. Project Goal

This document serves as a technical knowledge base for the iObeya Timeline Log Analyzer. Its purpose is to provide a comprehensive overview for future development, capturing the current architecture, key technical decisions, and lessons learned.

The primary goal of the application is to provide a high-performance, user-friendly desktop tool for analyzing iObeya log files. It must handle large datasets efficiently while offering powerful interactive visualization and filtering capabilities.

## 2. Core Architecture

The application follows a modular architecture that separates UI, business logic, and data processing.

-   **`iobeya_log_analyzer.py` (Main Application)**: This is the entry point. It's responsible for initializing the main window, setting up the core UI layout (toolbars, panels, docks), and handling top-level user actions (e.g., opening files, showing dialogs). It owns instances of `AppLogic` and other major UI components.

-   **`app_logic.py` (Business Logic Controller)**: This is the brain of the application. It manages the application's state, holds the log data (in a pandas DataFrame), and contains all the filtering and data manipulation logic. It acts as a mediator between the UI components and the data, ensuring that when a filter is changed in one part of the UI, all other relevant parts are updated coherently.

-   **`log_processing.py` (Data Loading)**: Contains the `LogLoaderThread`, which runs the entire log parsing process in a separate thread. This is critical to prevent the UI from freezing while processing large files or archives. It handles file reading (including `.gz` and `.zip`), parsing, and the creation of the main pandas DataFrame.

-   **UI Modules (`timeline_canvas.py`, `statistics_dialog.py`, `ui_widgets.py`, etc.)**: These files define specific, reusable UI components. This separation keeps the main application file cleaner and makes individual components easier to manage.
    -   `timeline_canvas.py`: A custom Matplotlib widget for the interactive timeline.
    -   `statistics_dialog.py`: The dialog for displaying global statistics with its own charts.
    -   `ui_widgets.py`: Contains smaller, reusable widgets like the `SearchWidget`.

## 3. Key Features & Implementation Details

-   **Pandas DataFrame as the Core Data Structure**: All log entries are stored in a single `pandas.DataFrame`. This was a crucial decision for performance, enabling fast filtering, aggregation, and manipulation of millions of rows.

-   **On-Demand Full Entry Loading**: To conserve memory, the main DataFrame only stores structured data (timestamp, level, message type, etc.). The full, multi-line raw log message is *not* stored in the DataFrame. It is reconstructed on-demand from the individual columns only when a user clicks on an entry in the list.

-   **High-Performance Full-Text Search (FTS)**: Implemented using an in-memory **SQLite database** with the **FTS5 extension**. When logs are loaded, their content is indexed in this temporary database. This allows for near-instantaneous text searches across the entire dataset, a feature that would be prohibitively slow with simple string matching on a large DataFrame.

-   **Coherent Filtering System**: The `AppLogic` class orchestrates a multi-layered filtering system. Filters (Time Range, Log Level, Message Type, FTS) are combined. A key feature is that applying one filter (e.g., FTS) dynamically updates the available options in other filters (e.g., the Message Type list only shows types present in the search results).

-   **Centralized UI/State Reset**: The `reset_for_new_data()` method in `AppLogic` was created to solve persistent bugs related to UI elements duplicating or state not being cleared when a new log file/archive was loaded. This method now provides a single, reliable entry point to reset the entire application to a clean slate.

## 4. Key Challenges & Lessons Learned

## 5. Release Process

To release a new version of the application, the following steps must be taken:

1.  **Update Version Number in `iobeya_log_analyzer.py`**:
    The version number is hardcoded in two places and must be updated in both:
    *   In the `LogAnalyzerApp.__init__` method: `self.app_version = "x.y.z"`
    *   In the `main()` function: `app.setApplicationVersion("x.y.z")`

2.  **Update `README.md`**:
    *   Add a new entry to the "Version History" section for the new version (`vX.Y.Z`).
    *   Mark the new version as `(Current)`.
    *   Move the `(Current)` tag from the previous version.
    *   List the key changes for the new version.

3.  **Commit and Tag**:
    *   Commit all changes with a descriptive message (e.g., `feat: Release vX.Y.Z`).
    *   It is recommended to also create a git tag for the new version (e.g., `git tag -a vX.Y.Z -m "Version X.Y.Z"`).

-   **Initial Performance Bottlenecks**: The application initially used standard Python lists and dictionaries, which was extremely slow and memory-intensive for large logs. **Lesson**: For any serious data manipulation in Python, switching to a library like `pandas` is non-negotiable. It solved both performance and memory issues.

-   **UI Freezing During Load**: The application was unusable while loading large files. **Lesson**: Any long-running or I/O-bound task **must** be moved to a background thread (`QThread` in PyQt) to keep the UI responsive. Communication back to the main thread must be done via signals and slots.

-   **State Management Bugs**: We faced numerous issues with filters not resetting, UI components duplicating, and inconsistent state. **Lesson**: A centralized state management approach is critical. The creation of `reset_for_new_data` and consolidating filter logic within `AppLogic` was the correct solution to ensure stability.

-   **File Corruption via Tooling**: There were several instances where automated tooling (my own actions) corrupted source files, leading to syntax errors that were difficult to debug. This happened when attempting complex, multi-location replacements in a single step. **Lesson**: When making significant changes, proceed with caution. Verify file integrity, and prefer smaller, incremental changes over large, complex ones. If a file becomes un-parsable, manual inspection and restoration is the only way forward.

-   **AttributeErrors from Threading**: We encountered `AttributeError` crashes when the background loading thread tried to update UI elements that no longer existed (e.g., a closed progress dialog). **Lesson**: Ensure robust signal/slot connections and check that UI elements exist before updating them from a different thread. The creation of `update_loading_dialog` and `reset_app_state_after_error` helped make this process more resilient.
