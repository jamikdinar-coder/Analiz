import hashlib  # ← добавь в импорты наверху

@st.cache_data(ttl=600, show_spinner=False)
def get_iiko_session() -> Optional[Tuple[requests.Session, str, str]]:
    session = requests.Session()
    
    # SHA-1 хэш пароля — именно так требует iiko REST API
    pass_sha1 = hashlib.sha1(USER_PASS.encode("utf-8")).hexdigest()
    
    urls = [
        f"https://{SERVER}/resto/api/auth",          # ← правильный путь для iiko cloud
        f"https://{SERVER}/resto/api/auth/login",
        f"http://{SERVER}:8080/resto/api/auth",
    ]
    
    errors = []
    for url in urls:
        try:
            resp = session.get(
                url,
                params={"login": USER_LOGIN, "pass": pass_sha1},  # ← SHA-1
                timeout=10,
                verify=False
            )
            if resp.status_code == 200:
                token = resp.text.strip().strip('"')
                if token and len(token) > 5:
                    base_url = url.split("/resto")[0]
                    return session, token, base_url
                else:
                    errors.append(f"{url} → HTTP 200, токен: `{resp.text[:100]}`")
            else:
                errors.append(f"{url} → HTTP {resp.status_code}: `{resp.text[:200]}`")
        except Exception as e:
            errors.append(f"{url} → `{type(e).__name__}: {e}`")
    
    st.error("❌ Не удалось подключиться к iiko.")
    for err in errors:
        st.warning(err)
    return None
