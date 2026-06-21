import http.server
import threading
import webbrowser

from ..core import green, bold, dim
from .api import Handler


def cmd_ui(args):
    ui_port = getattr(args, "port", 7502)
    server  = http.server.HTTPServer(("localhost", ui_port), Handler)
    url     = f"http://localhost:{ui_port}"
    print(f"\n  {green('✓')}  Porthole UI  →  {bold(url)}")
    print(f"  {dim('Press Ctrl+C to stop.')}\n")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n  {dim('UI stopped.')}")
