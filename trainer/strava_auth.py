"""One-time OAuth authorization for the Strava API.

Run once per profile:  pixi run strava-auth [--profile NAME]

Opens a browser to Strava's consent page, catches the redirect on
localhost:8000, exchanges the code for tokens and writes them to the active
profile's strava_tokens.json. After that, StravaClient refreshes them on its own.

When the athlete is on another computer, the redirect to localhost goes
nowhere. Send them the link instead and have them paste back the address of
the page they land on (it fails to load — that's expected; the code is in it):

    pixi run strava-auth --profile alex --link
    pixi run strava-auth --profile alex --code 'http://localhost:8000/callback?...'

Codes are single-use and short-lived, so paste it back promptly.

Prereq: the athlete's app at https://www.strava.com/settings/api must have
"Authorization Callback Domain" set to `localhost`, and its Client ID and
Secret must be in the profile's `.env`. Log in to Strava in the browser *as
that athlete* — the consent page authorizes whoever is signed in.
"""

import argparse
import http.server
import json
import urllib.parse
import webbrowser

import requests

from trainer.config import active_profile
from trainer.identity import WrongAthlete, claimed_by, record

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


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--profile", help="athlete profile (default: the active one)")
    parser.add_argument("--link", action="store_true", help="print the consent link and stop")
    parser.add_argument("--code", help="the code, or the whole localhost URL the athlete landed on")
    parser.add_argument(
        "--reset-identity", action="store_true", help="replace a different recorded Strava account"
    )
    args = parser.parse_args(argv)
    profile = active_profile(args.profile)
    client_id = profile.require("STRAVA_CLIENT_ID")
    client_secret = profile.require("STRAVA_CLIENT_SECRET")

    authorize_url = "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "approval_prompt": "auto",
            "scope": SCOPE,
        }
    )

    if args.link:
        print(authorize_url)
        return

    if args.code:
        code, scopes = _parse_pasted(args.code)
    else:
        print("Opening browser to authorize...")
        print(f"If it doesn't open, visit:\n{authorize_url}\n")
        webbrowser.open(authorize_url)

        server = http.server.HTTPServer(("localhost", 8000), _CallbackHandler)
        server.handle_request()  # serve exactly one request, then stop
        server.server_close()
        code, scopes = _CallbackHandler.code, getattr(_CallbackHandler, "scopes", "")

    if not code:
        raise SystemExit(f"No code returned: {_CallbackHandler.error}")

    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    payload = resp.json()
    athlete = payload.get("athlete", {})
    name = f"{athlete.get('firstname')} {athlete.get('lastname')}"
    try:  # before the tokens are saved, so a wrong login never replaces the right one
        record(profile, "strava", athlete.get("id"), name, args.reset_identity)
    except WrongAthlete as exc:
        raise SystemExit(f"{exc}\nNothing was saved.") from exc

    profile.strava_tokens.write_text(
        json.dumps(
            {
                "access_token": payload["access_token"],
                "refresh_token": payload["refresh_token"],
                "expires_at": payload["expires_at"],
            },
            indent=2,
        )
    )
    print(f"Saved tokens to {profile.strava_tokens}")
    print(f"Authorized as {name} (id {athlete.get('id')})")
    if others := claimed_by("strava", athlete.get("id"), exclude=profile.name):
        print(
            f"\nWARNING: this Strava account is also authorized under {', '.join(others)}. "
            "If that's wrong, log in to Strava as the right athlete and re-run."
        )

    if scopes is not None and "activity:read_all" not in scopes:
        print(
            "\nWARNING: 'activity:read_all' was not granted, so private activities "
            "will be invisible. Re-run and tick 'View data about your private activities'."
        )


def _parse_pasted(text: str) -> tuple[str | None, str | None]:
    """Accept a bare code or the full redirect URL; scopes are only known from the URL."""
    text = text.strip()
    if "?" not in text:
        return text, None
    params = urllib.parse.parse_qs(urllib.parse.urlparse(text).query)
    if error := params.get("error", [None])[0]:
        raise SystemExit(f"Strava returned an error instead of a code: {error}")
    return params.get("code", [None])[0], params.get("scope", [""])[0]


if __name__ == "__main__":
    main()
