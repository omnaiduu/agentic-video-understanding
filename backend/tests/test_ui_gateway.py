from app.ui_gateway import wants_ui

ORIGIN = "http://127.0.0.1:3000"
VIDEO = "/videos/e693d646-6033-49f4-bf35-0f9a9d0b32c6"


def test_gateway_off_without_origin() -> None:
    assert wants_ui("GET", "/", "text/html", "") is False


def test_html_home_uses_ui() -> None:
    assert wants_ui("GET", "/", "text/html", ORIGIN) is True


def test_html_watch_page_uses_ui() -> None:
    assert wants_ui("GET", VIDEO, "text/html,application/xhtml+xml", ORIGIN) is True


def test_json_watch_stays_on_api() -> None:
    assert wants_ui("GET", VIDEO, "application/json", ORIGIN) is False


def test_video_file_stays_on_api() -> None:
    assert wants_ui("GET", f"{VIDEO}/file", "*/*", ORIGIN) is False


def test_chat_post_stays_on_api() -> None:
    assert wants_ui("POST", f"{VIDEO}/chat", "application/json", ORIGIN) is False


def test_video_list_stays_on_api() -> None:
    assert wants_ui("GET", "/videos", "application/json", ORIGIN) is False


def test_internal_stays_on_api() -> None:
    assert wants_ui("GET", "/internal/videos/x/audio", "text/html", ORIGIN) is False
