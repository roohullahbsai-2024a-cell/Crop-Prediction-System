import os
import sys

# Ensure root directory is on the path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app as flask_app


class VercelPathFixMiddleware:
    """
    Ensures incoming requests route to Flask correctly regardless of whether
    Vercel routes by the original URI or the rewritten destination path (/api/index.py).
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        forwarded_uri = environ.get("HTTP_X_FORWARDED_URI") or environ.get("HTTP_X_NOW_ROUTE_MATCHES")
        if forwarded_uri and not forwarded_uri.startswith("/api/index"):
            environ["PATH_INFO"] = forwarded_uri.split("?")[0]
        else:
            path = environ.get("PATH_INFO", "")
            for prefix in ["/api/index.py", "/api/index"]:
                if path == prefix:
                    environ["PATH_INFO"] = "/"
                    break
                elif path.startswith(prefix + "/"):
                    environ["PATH_INFO"] = path[len(prefix):]
                    break
        return self.wsgi_app(environ, start_response)


flask_app.wsgi_app = VercelPathFixMiddleware(flask_app.wsgi_app)
app = flask_app

if __name__ == "__main__":
    app.run()
