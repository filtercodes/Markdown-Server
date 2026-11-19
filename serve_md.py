import html
import http.server
import io
import os
import socketserver
import urllib.parse
from pathlib import Path
import markdown as md_lib

PORT = 8888
THEME = "dark"  # Options: "light" or "dark"

# Theme color palettes injected into MD_CSS via CSS custom properties
THEMES = {
    "light": {
        "bg": "#ffffff",
        "text": "#222222",
        "heading": "#333333",
        "link": "#0969da",
        "code_bg": "#f4f4f4",
        "table_border": "#dddddd",
        "table_even_row": "#f2f2f2",
        "blockquote_border": "#cccccc",
        "blockquote_text": "#555555",
    },
    "dark": {
        "bg": "#121212",
        "text": "#e0e0e0",
        "heading": "#ffffff",
        "link": "#58a6ff",
        "code_bg": "#1e1e1e",
        "table_border": "#333333",
        "table_even_row": "#1a1a1a",
        "blockquote_border": "#444444",
        "blockquote_text": "#aaaaaa",
    },
}

if THEME not in THEMES:
    raise ValueError(f"Invalid THEME '{THEME}'. Expected one of: {', '.join(THEMES.keys())}")

_PALETTE = THEMES[THEME]

# Clean, readable CSS for Markdown in browser
MD_CSS = f"""
<style>
    :root {{
        --bg: {_PALETTE["bg"]};
        --text: {_PALETTE["text"]};
        --heading: {_PALETTE["heading"]};
        --link: {_PALETTE["link"]};
        --code-bg: {_PALETTE["code_bg"]};
        --table-border: {_PALETTE["table_border"]};
        --table-even-row: {_PALETTE["table_even_row"]};
        --blockquote-border: {_PALETTE["blockquote_border"]};
        --blockquote-text: {_PALETTE["blockquote_text"]};
    }}
    body {{ font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; background-color: var(--bg); color: var(--text); }}
    a {{ color: var(--link); }}
    pre, code {{ background-color: var(--code-bg); padding: 2px 5px; border-radius: 3px; font-family: monospace; }}
    pre code {{ display: block; padding: 10px; overflow-x: auto; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid var(--table-border); padding: 8px; }}
    tr:nth-child(even) {{ background-color: var(--table-even-row); }}
    h1, h2, h3 {{ color: var(--heading); }}
    blockquote {{ border-left: 4px solid var(--blockquote-border); margin-left: 0; padding-left: 16px; color: var(--blockquote-text); }}
    /* Directory listing styles matching the active Markdown theme */
    ul.dir-list {{ list-style: none; padding: 0; margin: 16px 0; border-top: 1px solid var(--table-border); }}
    ul.dir-list li {{ border-bottom: 1px solid var(--table-border); }}
    ul.dir-list li a {{ display: block; padding: 10px 12px; font-size: 1.1rem; text-decoration: none; font-family: monospace; }}
    ul.dir-list li a:hover {{ background-color: var(--table-even-row); }}
</style>
"""

class MarkdownHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='.', **kwargs)

    def do_GET(self):
        path = self.path.split('?')[0]  # Remove query params if any

        # Check if the requested file is a .md file
        if Path(path).suffix == '.md':
            try:
                with open(Path('.' + path), 'r', encoding='utf-8') as f:
                    md_content = f.read()

                # Convert markdown to HTML
                html_body = md_lib.markdown(md_content, extensions=['tables', 'fenced_code'])

                # Construct full valid HTML document
                full_html = f"""<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <title>{Path(path).name}</title>
                    {MD_CSS}
                </head>
                <body>
                    {html_body}
                </body>
                </html>"""

                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(full_html.encode('utf-8'))
            except FileNotFoundError:
                self.send_error(404, "File not found")
        else:
            # Serve other files and directory listings via SimpleHTTPRequestHandler
            super().do_GET()

    def list_directory(self, path):
        """
        Overrides SimpleHTTPRequestHandler.list_directory to render folder
        navigation pages using the same MD_CSS theme (dark/light) as Markdown files.
        """
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(http.server.HTTPStatus.NOT_FOUND, "No permission to list directory")
            return None

        # Sort directories first, then files, both case-insensitively
        entries.sort(key=lambda name: (not os.path.isdir(os.path.join(path, name)), name.lower()))

        display_path = urllib.parse.unquote(self.path.split('?')[0], errors='surrogatepass')
        display_path = html.escape(display_path, quote=False)

        items = []
        # Include parent directory link when inside any subdirectory
        if display_path.strip('/'):
            items.append('<li><a href="../">../</a></li>')

        for name in entries:
            fullname = os.path.join(path, name)
            display_name = name
            link_name = name
            if os.path.isdir(fullname):
                display_name = name + "/"
                link_name = name + "/"
            elif os.path.islink(fullname):
                display_name = name + "@"

            href = urllib.parse.quote(link_name, errors='surrogatepass')
            label = html.escape(display_name, quote=False)
            items.append(f'<li><a href="{href}">{label}</a></li>')

        list_html = "\n".join(items)
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Index of {display_path}</title>
    {MD_CSS}
</head>
<body>
    <h1>Index of {display_path}</h1>
    <ul class="dir-list">
        {list_html}
    </ul>
</body>
</html>"""

        encoded = full_html.encode('utf-8', 'surrogateescape')
        buffer = io.BytesIO(encoded)
        self.send_response(http.server.HTTPStatus.OK)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return buffer


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='.', **kwargs)

if __name__ == "__main__":
    # Allow immediate port reuse after Ctrl+C without waiting for OS TIME_WAIT
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MarkdownHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print("Open .md files in your browser to see formatted markdown.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

