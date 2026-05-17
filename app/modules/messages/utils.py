def parse_jwt_token(environ, auth) -> str | None:
    token = None

    if auth and isinstance(auth, dict):
        token = auth.get("token") or auth.get("authorization")

    if not token and environ.get("QUERY_STRING"):
        import urllib.parse

        qs = urllib.parse.parse_qs(environ.get("QUERY_STRING", ""))
        token_list = qs.get("token") or qs.get("authorization")
        if token_list:
            token = token_list[0]

    if not token:
        token = environ.get("HTTP_AUTHORIZATION") or environ.get("HTTP_TOKEN")
        if token and token.startswith("Bearer "):
            token = token[7:].strip()

    return token
