# serve_md.py

Local Markdown server for browsing and viewing `.md` files in a web browser. Styled like a website - light and dark theme support.

## Requirements

- Python 3
- Install `markdown` package: `pip install markdown`

## Configuration

Edit the constants at the top of `serve_md.py`:

```python
PORT = 8888
THEME = "dark"  # Options: "light" or "dark"
```

## Usage

1. `cd` into the directory you want to browse.
2. Run the script:
   ```bash
   python3 /Users/stefm1/test/serve_md.py
   ```
3. Open `http://localhost:8888` in a browser.
4. Click any folder to navigate or any `.md` file to view it rendered.
5. Press `Ctrl+C` in the terminal to stop the server.

## Troubleshooting

If port `8888` is already in use by another process:

```bash
lsof -ti :8888 | xargs kill
```
