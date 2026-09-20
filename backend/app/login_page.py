def render_login_page(error: bool = False) -> str:
    error_block = (
        '<p style="color:#b42318;margin:0 0 16px 0;">Invalid username or password.</p>'
        if error
        else ""
    )
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Sign in | Kanban Studio</title>
    <style>
      :root {{
        --secondary-purple: #753991;
        --navy-dark: #032147;
        --gray-text: #888888;
        --surface: #f7f8fb;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: radial-gradient(circle at 8% 10%, rgba(32,157,215,0.22), transparent 40%), var(--surface);
        font-family: Segoe UI, Arial, sans-serif;
        color: var(--navy-dark);
      }}
      .card {{
        width: min(420px, 92vw);
        background: #fff;
        border: 1px solid rgba(3,33,71,0.09);
        border-radius: 24px;
        padding: 28px;
        box-shadow: 0 16px 32px rgba(3,33,71,0.12);
      }}
      h1 {{ margin: 0 0 8px 0; }}
      p {{ margin: 0 0 20px 0; color: var(--gray-text); }}
      label {{ display: block; font-size: 0.9rem; margin-bottom: 6px; }}
      input {{
        width: 100%;
        box-sizing: border-box;
        border: 1px solid rgba(3,33,71,0.12);
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 14px;
      }}
      button {{
        width: 100%;
        border: 0;
        border-radius: 999px;
        padding: 11px 14px;
        background: var(--secondary-purple);
        color: #fff;
        font-weight: 700;
        cursor: pointer;
      }}
      .hint {{ margin-top: 14px; font-size: 0.85rem; color: var(--gray-text); }}
      .hint code {{ background: #f0f2f8; border-radius: 5px; padding: 2px 5px; }}
    </style>
  </head>
  <body>
    <main class=\"card\">
      <h1>Sign in</h1>
      <p>Use the MVP credentials to open your board.</p>
      {error_block}
      <form method=\"post\" action=\"/api/auth/login\">
        <label for=\"username\">Username</label>
        <input id=\"username\" name=\"username\" type=\"text\" autocomplete=\"username\" required />
        <label for=\"password\">Password</label>
        <input id=\"password\" name=\"password\" type=\"password\" autocomplete=\"current-password\" required />
        <button type=\"submit\">Sign in</button>
      </form>
      <p class=\"hint\">For MVP: <code>user</code> / <code>password</code></p>
    </main>
  </body>
</html>
"""
