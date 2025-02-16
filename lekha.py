import os
import time
import markdown
import threading
import http.server
import socketserver
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configurations
SRC_FOLDER = "./src"
OUTPUT_FOLDER = "./sites"
PORT = 8000

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class ChangeHandler(FileSystemEventHandler):

    def __init__(self, observer):
        self.changes = []
        self.observer = observer

    def on_modified(self, event):
        if event.is_directory:
            return
        self.changes.append(event.src_path)
        self.process_changes()

    def process_changes(self):
        if self.changes:
            recompile(self.changes)
            self.changes = []

def recompile(changes):
    print("Files changed:", changes)

    for filepath in changes:
        if filepath.endswith(".md"):
            convert_markdown_to_html(filepath)

def convert_markdown_to_html(md_filepath):
    with open(md_filepath, "r", encoding="utf-8") as md_file:
        md_content = md_file.read()

    html_content = markdown.markdown(md_content)

    # Output file name (same as input but with .html extension)
    filename = os.path.basename(md_filepath).replace(".md", ".html")
    html_filepath = os.path.join(OUTPUT_FOLDER, filename)

    with open(html_filepath, "w", encoding="utf-8") as html_file:
        html_file.write(html_content)

    print(f"Converted {md_filepath} → {html_filepath}")

def start_http_server(stop_event):
    os.chdir(OUTPUT_FOLDER)  # Serve files from 'sites/' folder
    handler = http.server.SimpleHTTPRequestHandler

    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Serving HTML files at http://localhost:{PORT}")

        while not stop_event.is_set():
            httpd.handle_request()

        print("HTTP server shutting down...")

def start_file_watcher(stop_event):
    observer = Observer()
    event_handler = ChangeHandler(observer)
    observer.schedule(event_handler, SRC_FOLDER, recursive=True)
    observer.start()

    print(f"Watching for file changes in {SRC_FOLDER}...")

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping file watcher...")
        observer.stop()
        observer.join()
        raise

def main():
    stop_event = threading.Event()

    server_thread = threading.Thread(target=start_http_server, args=(stop_event,))
    server_thread.daemon = True
    server_thread.start()

    try:
        start_file_watcher(stop_event)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        stop_event.set()

        print("Waiting for server thread to stop...")
        server_thread.join(timeout=5)

        print("All processes stopped.")

if __name__ == "__main__":
    main()
