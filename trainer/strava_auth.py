"""One-time OAuth authorization for the Strava API.

Run once:  pixi run python -m trainer.strava_auth

Opens a browser to Strava's consent page, catches the redirect on
localhost:8000, exchanges the code for tokens and writes them to
.strava_tokens.json at the repo root. After that, StravaClient refreshes
them on its own.

Prereq: your app at https://www.strava.com/settings/api must have
"Authorization Callback Domain" set to `localhost`.
"""

import http.server
import json
import urllib.parse
import webbrowser

import requests

from trainer.config import require_env
from trainer.strava import TOKENS_PATH

REDIRECT_URI = "http://localhost:8000/callback"
# activity:read_all also covers activities you've marked private
SCOPE = "read,activity:read_all,profile:read_all"


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    code = None
    error = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CallbackHandler.code = params.get("code", [None])[0]
        _CallbackHandler.error = params.get("error", [None])[0]
        scopes = params.get("scope", [""])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        if _CallbackHandler.code:
            body = "<h2>Authorized.</h2><p>You can close this tab.</p>"
            if "activity:read_all" not in scopes:
                body += "<p><b>Warning:</b> private activities were not granted.</p>"
        else:
            body = f"<h2>Authorization failed</h2><p>{_CallbackHandler.error}</p>"
        self.wfile.write(body.encode())
        _CallbackHandler.scopes = scopes

    def log_message(self, *args):
        pass  # keep the console clean


def main():
    client_id = require_env("STRAVA_CLIENT_ID")
    client_secret = require_env("STRAVA_CLIENT_SECRET")

    authorize_url = "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "approval_prompt": "auto",
            "scope": SCOPE,
        }
    )

    print("Opening browser to authorize...")
    print(f"If it doesn't open, visit:\n{authorize_url}\n")
    webbrowser.open(authorize_url)

    server = http.server.HTTPServer(("localhost", 8000), _CallbackHandler)
    server.handle_request()  # serve exactly one request, then stop
    server.server_close()

    if not _CallbackHandler.code:
        raise SystemExit(f"No code returned: {_CallbackHandler.error}")

    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": _CallbackHandler.code,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    payload = resp.json()

    TOKENS_PATH.write_text(
        json.dumps(
            {
                "access_token": payload["access_token"],
                "refresh_token": payload["refresh_token"],
                "expires_at": payload["expires_at"],
            },
            indent=2,
        )
    )
    athlete = payload.get("athlete", {})
    print(f"Saved tokens to {TOKENS_PATH}")
    print(f"Authorized as {athlete.get('firstname')} {athlete.get('lastname')} (id {athlete.get('id')})")

    if "activity:read_all" not in getattr(_CallbackHandler, "scopes", ""):
        print(
            "\nWARNING: 'activity:read_all' was not granted, so private activities "
            "will be invisible. Re-run and tick 'View data about your private activities'."
        )


if __name__ == "__main__":
    main()
