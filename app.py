from __future__ import annotations

import os

from waitress import serve

from immunisation_app import create_app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    serve(app, host="0.0.0.0", port=port)

