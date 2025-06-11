# iObeya Timeline Log Analyzer

## Overview

The iObeya Timeline Log Analyzer is a Python-based desktop application designed for viewing and analyzing application log files. It provides an interactive timeline visualization, powerful filtering capabilities, and memory-efficient handling of large log datasets, making it easier to navigate, understand, and troubleshoot log data.

![Global View of the application](images/global_view.jpg)

## Key Features

*   **Welcome Screen**: A user-friendly startup panel with quick access to load a single file or a log archive.
*   **Flexible Log Loading**:
    *   Load individual log files (`.log`, `.log.gz`).
    *   Load compressed log archives (`.zip`) containing both plain text and gzipped logs.
*   **Advanced Archive Filtering**: When loading archives, a dialog allows you to:
    *   Filter files by a specific **date range**.
    *   Filter files by type: **All Logs**, **Application Logs (`app*`)**, or **Error Logs (`error*`)**.
*   **Interactive Timeline Visualization**:
    *   View log event distribution over time.
    *   Adjustable granularity (Day, Hour, Minute) for the timeline display.
    *   Zoom and pan capabilities on the timeline.
    *   When more than 10 message types are selected, their individual bars in the timeline are aggregated into a single "Other Types" bar to maintain clarity.
*   **Powerful Filtering**: Combine multiple filters for precise analysis:
    *   Filter by **Log Level** (INFO, WARN, ERROR, DEBUG).
    *   Filter by **Message Type** (derived from logger names).
    *   Filter by a specific **Time Range** by clicking and dragging on the timeline.
    *   Perform **Text Search** on log message previews.
*   **Detailed Log View**: Select a log entry from the list to see its full, multi-line content in a dedicated details panel.
*   **Statistics Panel**: View summary statistics about the loaded log data.
*   **Memory Efficient**: Utilizes pandas DataFrames and on-demand loading of full log entries to handle very large files.
*   **About Dialog**: Includes application version, copyright information, and a fun hidden easter egg.

## Installation and Running

1.  **Clone the Repository**
    ```bash
    git clone git@github.com:jreveliobeya/timeline_iobeya_log_analyzer.git
    cd timeline_iobeya_log_analyzer
    ```

2.  **Install Dependencies**
    The project requires `PyQt5` and `pandas`. Install them using pip:
    ```bash
    pip install PyQt5 pandas
    ```

3.  **Run the Application**
    ```bash
    python iobeya_log_analyzer.py
    ```

## Using the Analyzer

1.  **Loading Logs**: From the welcome screen or the main toolbar, choose one of the following:
    *   **Load Single Log File**: Select and load a single `.log` or `.log.gz` file.
    *   **Load Log Archive**: Select a `.zip` archive. A dialog will appear, allowing you to filter files by date and type before loading:
        ![File Selection Dialog](images/file_selection_dialog.jpg)
        *   Use the **Filter by type** dropdown to narrow down files (e.g., show only `app*` logs).
        *   Select a **Start Date** and **End Date** using the calendar widgets.
        *   The file list updates automatically. Click "OK" to load the selected files.
    *   A progress dialog will show the loading status. Once loaded, the main UI will appear.

2.  **Navigating the UI**:
    *   **Toolbar**: Contains actions for loading files/archives, resetting the view, and viewing the "About" dialog.
    *   **Timeline Section**: Displays the log event distribution over time. Click and drag to select a time range.
    *   **Message Types Panel (Left)**: Lists all unique message types. Use the checkboxes and search bar to filter.
    *   **Selected Messages List (Center)**: Displays log entries matching the current filters.
    *   **Details Panel (Right)**: Shows the full, multi-line content of the selected log entry.

3.  **Applying Filters**:
    *   All active filters (Log Level, Message Type, Time Range, Text Search) are combined to refine the displayed log entries.
    *   Click the "Reset View" button in the toolbar to clear all filters and reset the timeline zoom.

4.  **Viewing Information**:
    *   Click the **📊** button to open the statistics dialog.
    *   Click the **ℹ️** button on the far right of the toolbar to open the "About" dialog.

## Known Issues / Future Enhancements

*   Full-text search on complete log messages (currently searches previews) could be a future enhancement.
*   Support for more diverse log formats.

