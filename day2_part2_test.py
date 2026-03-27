import json
import time
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
ADMIN_BEARER = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QHRlc3QuY29tIiwiZXhwIjoxNzc0NjE2NDUxLCJ0eXBlIjoiYWNjZXNzIn0.jW6zwc91OJrakThFve-IZVbO4ZTnuhSFsAKY8lx_3mE"

results = []


def add_result(module, check, ok, expected, actual, details=None):
    results.append(
        {
            "module": module,
            "check": check,
            "ok": ok,
            "expected": expected,
            "actual": actual,
            "details": details,
        }
    )


def req(method, path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.request(method, f"{BASE_URL}{path}", headers=headers, timeout=30, **kwargs)
    return r


def ensure_user(email, password, full_name, phone, city="Bishkek"):
    register_payload = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "city": city,
        "preferred_language": "en",
        "password": password,
        "confirm_password": password,
    }
    req("POST", "/auth/register", json=register_payload)

    login_payload = {"email": email, "password": password}
    login_resp = req("POST", "/auth/login", json=login_payload)
    if login_resp.status_code != 200:
        raise RuntimeError(f"Login failed for {email}: {login_resp.status_code} {login_resp.text}")
    return login_resp.json()["access_token"]


def get_or_create_category():
    cats_resp = req("GET", "/categories")
    if cats_resp.status_code == 200 and cats_resp.json():
        return cats_resp.json()[0]["id"]

    slug = f"auto-cat-{int(time.time())}"
    create_payload = {
        "name": f"AutoCategory {int(time.time())}",
        "slug": slug,
        "display_order": 1,
    }
    admin_headers = {"Authorization": ADMIN_BEARER}
    create_resp = req("POST", "/admin/categories", headers=admin_headers, json=create_payload)
    if create_resp.status_code not in (200, 201):
        raise RuntimeError(f"Cannot create category: {create_resp.status_code} {create_resp.text}")
    return create_resp.json()["id"]


def create_listing(user_token, category_id):
    payload = {
        "title": f"Test Listing {int(time.time())}",
        "description": "Temporary listing for API tests",
        "price": 12345,
        "currency": "USD",
        "city": "Bishkek",
        "condition": "used",
        "category_id": category_id,
        "latitude": None,
        "longitude": None,
        "is_negotiable": True,
    }
    r = req("POST", "/listings/", token=user_token, json=payload)
    if r.status_code != 201:
        raise RuntimeError(f"Create listing failed: {r.status_code} {r.text}")
    return r.json()["id"]


def main():
    suffix = int(time.time())
    user1_email = f"day2_u1_{suffix}@test.com"
    user2_email = f"day2_u2_{suffix}@test.com"
    pwd = "Passw0rd!123"

    token1 = ensure_user(user1_email, pwd, "Day2 User One", f"+996700{suffix % 1000000:06d}")
    token2 = ensure_user(user2_email, pwd, "Day2 User Two", f"+996701{suffix % 1000000:06d}")

    me1 = req("GET", "/users/me", token=token1).json()
    me2 = req("GET", "/users/me", token=token2).json()

    category_id = get_or_create_category()
    listing_id = create_listing(token1, category_id)

    # FAVORITES
    fav1 = req("POST", f"/favorites/{listing_id}", token=token2)
    add_result("FAVORITES", "Добавить листинг в избранное", fav1.status_code == 201, 201, fav1.status_code)

    fav_dup = req("POST", f"/favorites/{listing_id}", token=token2)
    add_result("FAVORITES", "Добавить тот же листинг снова", fav_dup.status_code == 409, 409, fav_dup.status_code, fav_dup.text)

    fav_del = req("DELETE", f"/favorites/{listing_id}", token=token2)
    add_result("FAVORITES", "Удалить из избранного", fav_del.status_code == 204, 204, fav_del.status_code)

    fav_list = req("GET", "/favorites?page=1&page_size=20", token=token2)
    add_result("FAVORITES", "Получить список избранного", fav_list.status_code == 200, 200, fav_list.status_code)

    # MESSAGING
    conv_expected = req("POST", "/conversations", token=token2, json={"listing_id": listing_id, "recipient_id": me1["id"]})
    add_result("MESSAGING", "POST /conversations (как в чеклисте)", conv_expected.status_code in (200, 201), "200/201", conv_expected.status_code, conv_expected.text)

    conv1 = req("POST", "/conversations/start", token=token2, json={"listing_id": listing_id, "recipient_user_id": me1["id"]})
    conv_id = conv1.json()["id"] if conv1.status_code in (200, 201) else None
    add_result("MESSAGING", "Создать conversation (фактический роут)", conv1.status_code in (200, 201), "200/201", conv1.status_code)

    conv2 = req("POST", "/conversations/start", token=token2, json={"listing_id": listing_id, "recipient_user_id": me1["id"]})
    same_conv = False
    if conv1.status_code in (200, 201) and conv2.status_code in (200, 201):
        same_conv = conv1.json().get("id") == conv2.json().get("id")
    add_result("MESSAGING", "Создать ту же conversation снова (reuse)", same_conv, "same conversation id", conv2.json().get("id") if conv2.status_code in (200, 201) else conv2.status_code)

    conv_list = req("GET", "/conversations", token=token2)
    add_result("MESSAGING", "Получить список conversations", conv_list.status_code == 200, 200, conv_list.status_code)

    msg_send = req("POST", "/messages", token=token2, json={"conversation_id": conv_id, "message_type": "text", "text_body": "Hello from day2 part2"})
    msg_id = msg_send.json()["id"] if msg_send.status_code == 201 else None
    add_result("MESSAGING", "Отправить текстовое сообщение", msg_send.status_code == 201, 201, msg_send.status_code)

    msg_list_user1 = req("GET", f"/messages/{conv_id}", token=token1)
    add_result("MESSAGING", "Получить messages внутри conversation", msg_list_user1.status_code == 200, 200, msg_list_user1.status_code)

    read_marked = False
    if msg_list_user1.status_code == 200:
        for item in msg_list_user1.json().get("items", []):
            if item.get("id") == msg_id:
                read_marked = item.get("is_read") is True
                break
    add_result("MESSAGING", "Пометить сообщение как прочитанное", read_marked, True, read_marked)

    # ATTACHMENTS
    temp_dir = Path("uploads") / "_test_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    png_path = temp_dir / "test.png"
    pdf_path = temp_dir / "test.pdf"
    exe_path = temp_dir / "test.exe"
    zip_path = temp_dir / "test.zip"

    png_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0DIHDR")
    pdf_path.write_bytes(b"%PDF-1.4\n%test\n")
    exe_path.write_bytes(b"MZfakeexe")
    zip_path.write_bytes(b"PK\x03\x04fakezip")

    with png_path.open("rb") as f:
        up_png = req("POST", "/attachments/upload", token=token2, files={"file": ("test.png", f, "image/png")}, data={"message_id": str(msg_id)})
    png_attachment_id = up_png.json().get("id") if up_png.status_code == 201 else None
    add_result("ATTACHMENTS", "Загрузить картинку", up_png.status_code == 201, 201, up_png.status_code)

    with pdf_path.open("rb") as f:
        up_pdf = req("POST", "/attachments/upload", token=token2, files={"file": ("test.pdf", f, "application/pdf")}, data={"message_id": str(msg_id)})
    add_result("ATTACHMENTS", "Загрузить PDF", up_pdf.status_code == 201, 201, up_pdf.status_code)

    with exe_path.open("rb") as f:
        up_exe = req("POST", "/attachments/upload", token=token2, files={"file": ("test.exe", f, "application/octet-stream")}, data={"message_id": str(msg_id)})
    add_result("ATTACHMENTS", "Загрузить .exe (должен отклонить)", up_exe.status_code >= 400, ">=400", up_exe.status_code)

    with zip_path.open("rb") as f:
        up_zip = req("POST", "/attachments/upload", token=token2, files={"file": ("test.zip", f, "application/zip")}, data={"message_id": str(msg_id)})
    add_result("ATTACHMENTS", "Загрузить .zip (должен отклонить)", up_zip.status_code >= 400, ">=400", up_zip.status_code)

    msg_with_attachment = req(
        "POST",
        "/messages",
        token=token2,
        json={
            "conversation_id": conv_id,
            "message_type": "file",
            "attachment_id": png_attachment_id,
        },
    )
    msg_with_attachment_ok = False
    if msg_with_attachment.status_code == 201:
        msg_with_attachment_ok = len(msg_with_attachment.json().get("attachments", [])) > 0
    add_result(
        "ATTACHMENTS",
        "Отправить сообщение с attachment_id",
        msg_with_attachment_ok,
        "message linked with attachment",
        msg_with_attachment.status_code,
        msg_with_attachment.text,
    )

    get_attachment = req("GET", f"/attachments/{png_attachment_id}", token=token1)
    add_result("ATTACHMENTS", "Получить attachment", get_attachment.status_code == 200, 200, get_attachment.status_code)

    # NOTIFICATIONS
    notify_list = req("GET", "/notifications", token=token1)
    has_new_message = False
    first_notification_id = None
    if notify_list.status_code == 200:
        items = notify_list.json().get("items", [])
        if items:
            first_notification_id = items[0].get("id")
        has_new_message = any(n.get("type") == "new_message" for n in items)
    add_result("NOTIFICATIONS", "После сообщения появился new_message", has_new_message, True, has_new_message)
    add_result("NOTIFICATIONS", "GET /notifications", notify_list.status_code == 200, 200, notify_list.status_code)

    unread_count = req("GET", "/notifications/unread-count", token=token1)
    add_result("NOTIFICATIONS", "GET /notifications/unread-count", unread_count.status_code == 200, 200, unread_count.status_code, unread_count.text)

    patch_read = req("PATCH", f"/notifications/{first_notification_id}/read", token=token1)
    add_result("NOTIFICATIONS", "PATCH /notifications/{id}/read", patch_read.status_code == 200, 200, patch_read.status_code, patch_read.text)

    patch_all = req("PATCH", "/notifications/read-all", token=token1)
    add_result("NOTIFICATIONS", "PATCH /notifications/read-all", patch_all.status_code == 200, 200, patch_all.status_code, patch_all.text)

    # REPORTS
    report_payload = {
        "target_type": "listing",
        "target_id": listing_id,
        "reason_code": "spam",
        "reason_text": "Suspicious listing for test",
    }
    report1 = req("POST", "/reports", token=token2, json=report_payload)
    add_result("REPORTS", "Создать репорт на листинг", report1.status_code == 201, 201, report1.status_code)

    report2 = req("POST", "/reports", token=token2, json=report_payload)
    add_result("REPORTS", "Создать второй репорт на тот же листинг", report2.status_code == 409, 409, report2.status_code, report2.text)

    report_my = req("GET", "/reports/my", token=token2)
    add_result("REPORTS", "GET /reports/my", report_my.status_code == 200, 200, report_my.status_code, report_my.text)

    passed = sum(1 for r in results if r["ok"])
    total = len(results)

    print(json.dumps({"passed": passed, "total": total, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
