"""Local interface catalogs. Translation never changes data or form values."""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from flask import abort, redirect, request
from jinja2.ext import Extension

CATALOGS = json.loads(Path(__file__).with_name("translations.json").read_text(encoding="utf-8"))
LANGUAGES = {"en": "English", "vi": "Tiếng Việt", "es": "Español",
             "fr": "Français", "de": "Deutsch", "zh": "简体中文"}


def language():
    selected = request.cookies.get("atlas_language", "en")
    return selected if selected in LANGUAGES else "en"


def translate(value):
    value = str(value)
    return CATALOGS[language()].get(value, value)


class InterfaceText(Extension):
    """Mark literal HTML text for lookup while leaving Jinja expressions intact."""
    def preprocess(self, source, name, filename=None):
        if not name or not name.endswith(".html"):
            return source

        def mark(match):
            text = match.group(1)
            if any(token in text for token in ("{{", "{%", "{#")):
                return match.group(0)
            phrase = html.unescape(text.strip())
            if phrase not in CATALOGS["en"]:
                return match.group(0)
            before = text[:len(text) - len(text.lstrip())]
            after = text[len(text.rstrip()):]
            return ">" + before + "{{ _(" + repr(phrase) + ") }}" + after + "<"

        return re.sub(r">([^<>]+)<", mark, source)


def init_app(app):
    app.jinja_env.add_extension(InterfaceText)
    app.jinja_env.globals.update(_=translate)

    @app.context_processor
    def locale_context():
        return {"language": language(), "languages": LANGUAGES,
                "return_to": request.full_path.rstrip("?")}

    @app.get("/language")
    def choose_language():
        selected = request.args.get("language", "")
        target = request.args.get("next", "/")
        parts = urlsplit(target)
        allowed = {"/", "/mission", "/vaccinations", "/infections", "/improvements", "/benchmark"}
        if selected not in LANGUAGES:
            abort(400)
        if (parts.scheme or parts.netloc or parts.path not in allowed
                or "\\" in target or any(ord(c) < 32 for c in target)):
            abort(400)
        response = redirect(target, code=303)
        response.set_cookie("atlas_language", selected, max_age=31536000,
                            httponly=True, samesite="Lax", secure=request.is_secure)
        return response

    @app.after_request
    def locale_headers(response):
        if response.mimetype == "text/html":
            response.headers["Content-Language"] = "zh-Hans" if language() == "zh" else language()
            response.vary.add("Cookie")
        return response
