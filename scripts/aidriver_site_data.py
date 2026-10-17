#!/usr/bin/env python3
"""Собирает данные раздела /stories/aidriver-2026 из волта.

Единица контента — ОПУБЛИКОВАННЫЙ ПОСТ канала @ai_n_ns, а не внутренний разбор:
на сайте должен быть текст с канала.

Источник: ~/.hermes/workspace/notes/projects/Статьи/AI Driver & RecSys 2026 — посты канала.md
          (другой каталог заметок — переменная окружения AIDRIVER_NOTES)
          зал для поста берётся из файла «… — доклады.md» по message_id.

Выход:   data/aidriver-2026.json в корне этого репозитория (страница импортирует его при сборке)

Запуск:  python3 scripts/aidriver_site_data.py [--check]
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

NOTES = Path(os.environ.get("AIDRIVER_NOTES") or
             Path.home() / ".hermes/workspace/notes/projects/Статьи")
TALKS_MD = NOTES / "AI Driver & RecSys 2026 — доклады.md"
POSTS_MD = NOTES / "AI Driver & RecSys 2026 — посты канала.md"
OUT = Path(__file__).resolve().parent.parent / "data/aidriver-2026.json"
MSK = timezone(timedelta(hours=3))

HALLS = {"big": "Большой зал", "small": "Малый зал"}

POST_HEAD_RE = re.compile(r"^## (\d{1,2}:\d{2})–(\d{1,2}:\d{2}) MSK · (.+)$")
POST_ID_RE = re.compile(r"^message_id (\d+)")
TALK_HEAD_RE = re.compile(r"^### .+ \((big|small), \d{1,2}:\d{2}–\d{1,2}:\d{2} MSK\)\s*$")
TALK_POST_RE = re.compile(r"^\s*-\s+\*\*Пост в канале:\*\*\s*\[?(\d+)\)?")
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
CODE_RE = re.compile(r"`([^`]+)`")
TAG_LINE_RE = re.compile(r"^#\S")


def split_people(s: str) -> tuple[str, str]:
    """«Алексей Васильев, Sber AI Lab» → (спикер, организация)."""
    depth = 0
    parts, cur = [], ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
            continue
        cur += ch
    parts.append(cur.strip())
    if len(parts) == 2 and "(" not in parts[1]:
        return parts[0], parts[1]
    return s.strip(), ""


def inline_md(text: str) -> str:
    """Экранирует HTML и превращает inline-markdown поста в безопасный HTML."""
    out = html.escape(text, quote=False)
    out = LINK_RE.sub(lambda m: f'<a href="{html.escape(m.group(2), quote=True)}" '
                                 f'target="_blank" rel="noopener">{m.group(1)}</a>', out)
    out = BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = CODE_RE.sub(r"<code>\1</code>", out)
    return out


def body_to_html(paragraphs: list[str]) -> str:
    """Абзацы поста → HTML. Строки «— …» собираются в список."""
    blocks: list[str] = []
    bullets: list[str] = []

    def flush() -> None:
        nonlocal bullets
        if bullets:
            blocks.append("<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>")
            bullets = []

    for para in paragraphs:
        text = para.strip()
        if not text:
            continue
        if text.startswith("— "):
            bullets.append(inline_md(text[2:].strip()))
            continue
        flush()
        blocks.append(f"<p>{inline_md(text)}</p>")
    flush()
    return "".join(blocks)


def parse_posts() -> list[dict]:
    """Посты канала: заголовок, спикер, время, message_id, тело и хэштеги."""
    if not POSTS_MD.exists():
        return []
    lines = POSTS_MD.read_text(encoding="utf-8").splitlines()
    posts: list[dict] = []
    cur: dict | None = None
    body: list[str] = []
    in_body = False
    for line in lines:
        m = POST_HEAD_RE.match(line)
        if m:
            if cur is not None:
                cur["body"] = body
                posts.append(cur)
            t0, t1, rest = m.groups()
            title, _, people = rest.partition(" — ")
            speaker, org = split_people(people)
            cur = {"time": f"{t0}–{t1}", "t0": t0, "title": title.strip(),
                   "people": people.strip(), "speaker": speaker, "org": org,
                   "messageId": None, "rawBody": []}
            body = []
            in_body = False
            continue
        if cur is None:
            continue
        mi = POST_ID_RE.match(line)
        if mi:
            cur["messageId"] = int(mi.group(1))
            in_body = True
            continue
        if not in_body:
            continue
        if TAG_LINE_RE.match(line):
            cur.setdefault("tags", []).extend(
                t.lstrip("#") for t in re.findall(r"#[A-Za-zА-Яа-я0-9_]+", line))
            continue
        body.append(line)
    if cur is not None:
        cur["body"] = body
        posts.append(cur)
    return [p for p in posts if p["messageId"]]


def talk_index() -> list[dict]:
    """Доклады из файла разборов: заголовок, время, зал (в постах зала нет)."""
    if not TALKS_MD.exists():
        return []
    out: list[dict] = []
    for line in TALKS_MD.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^### (.+?) — .+ \((big|small), (\d{1,2}:\d{2})–(\d{1,2}:\d{2}) MSK\)\s*$", line)
        if m:
            out.append({"title": m.group(1).strip(), "hall": m.group(2),
                        "time": f"{m.group(3)}–{m.group(4)}"})
    return out


def tokens(s: str) -> set[str]:
    return {w for w in re.sub(r"[^a-zа-я0-9]+", " ", s.lower()).split() if len(w) > 2}


def match_hall(post: dict, talks: list[dict]) -> str:
    """Зал — по лучшему совпадению заголовка поста с заголовком доклада."""
    best, best_score = "", 0.0
    pt = tokens(post["title"])
    for t in talks:
        tt = tokens(t["title"])
        if not pt or not tt:
            continue
        score = len(pt & tt) / min(len(pt), len(tt))
        if t["time"] == post["time"]:
            score += 0.1
        if score > best_score:
            best, best_score = t["hall"], score
    return best if best_score >= 0.6 else ""


def make_preview(blocks: list[str], limit: int = 700) -> str:
    """Превью карточки: осмысленный текст до границы предложения, без лид-инов.

    Лид-ин вида «**Тренды.**» отбрасывается: он не несёт содержания без списка,
    который идёт следом. Обрезка — по последней точке в пределах лимита, иначе
    по границе слова с многоточием; обрыв на полуслове не допускается.
    """
    parts = []
    for b in blocks:
        t = re.sub(r"[`*]", "", b).strip()
        t = re.sub(r"^—\s*", "", t)
        if not t or re.fullmatch(r"[^.]{1,40}\.", t):
            continue
        parts.append(t)
    text = " ".join(parts).strip()
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    if len(text) <= limit:
        return text
    # Первое полное предложение содержательного текста — даже если оно длиннее лимита:
    # обрыв на полуслове в карточке читается как ошибка вёрстки.
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s)", text[:700])]
    if ends and ends[0] >= 120:
        return text[: ends[0]]
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"


def paragraphs(lines: list[str]) -> list[str]:
    """Строки поста → абзацы: пустая строка разделяет, пункты списка — отдельные строки."""
    out: list[str] = []
    buf: list[str] = []
    for line in lines:
        if not line.strip():
            if buf:
                out.append(" ".join(buf).strip())
                buf = []
            continue
        if line.startswith("— "):
            if buf:
                out.append(" ".join(buf).strip())
                buf = []
            out.append(line.strip())
            continue
        buf.append(line.strip())
    if buf:
        out.append(" ".join(buf).strip())
    return [p for p in out if p]


def clean_title(raw: str) -> str:
    """Заголовок поста в архиве — markdown-ссылка; оставить текст."""
    m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", raw.strip())
    return m.group(1).strip() if m else raw.strip()


def main() -> None:
    check = "--check" in sys.argv
    halls = talk_index()
    posts = parse_posts()

    talks: list[dict] = []
    for p in posts:
        hall = match_hall(p, halls)
        body = paragraphs(p["body"])
        body = [b for b in body if not re.match(r"^\*\*\[.+\]\(.+\)\*\*$", b)]
        intro = re.compile(r"—\s*(?:Большой|Малый) зал, \d{1,2}:\d{2}–\d{1,2}:\d{2} MSK\.?$")
        if body and ("на конференции AI Driver" in body[0]
                     or intro.search(body[0])
                     or body[0].startswith(p["speaker"].split(",")[0])):
            body = body[1:]
        tags = p.get("tags", [])
        talks.append({
            "slug": f"{hall or 'talk'}-{p['t0'].replace(':', '')}-{p['messageId']}",
            "title": clean_title(p["title"]),
            "speaker": p["speaker"],
            "org": p["org"],
            "hall": hall,
            "hallLabel": HALLS.get(hall, "Конференция"),
            "time": p["time"],
            "messageId": p["messageId"],
            "url": f"https://t.me/ai_n_ns/{p['messageId']}",
            "bodyHtml": body_to_html(body),
            "preview": make_preview(body),
            "tags": tags[:6],
        })
    talks.sort(key=lambda t: (t["time"].split("–")[0], t["hall"] != "big"))


    now = datetime.now(MSK)
    live = now.date().isoformat() == "2026-10-17" and now.hour * 60 + now.minute < 17 * 60 + 25
    data = {
        "event": {
            "title": "AI Driver & RecSys 2026",
            "subtitle": "Посты канала @ai_n_ns о докладах конференции — так, как они опубликованы",
            "date": "17 октября 2026",
            "place": "Офис Сбера, Москва, Кутузовский пр-т 32",
            "programUrl": "https://developers.sber.ru/kak-v-sbere/events/ai_driver_october_2026",
            "channelUrl": "https://t.me/ai_n_ns",
            "sourceNote": "Тексты постов — из канала @ai_n_ns, без правок; исходная запись докладов "
                          "расшифрована faster-whisper large-v3-turbo, числа — только прозвучавшие.",
        },
        "updated": now.isoformat(timespec="minutes"),
        "live": live,
        "stats": {
            "talks": len(talks),
            "halls": len({t["hall"] for t in talks if t["hall"]}),
            "withPost": len(talks),
        },
        "talks": talks,
    }
    if check:
        print(json.dumps(data["stats"], ensure_ascii=False))
        for t in talks:
            print(f"{t['messageId']:>5} {t['time']:13} {t['hallLabel']:12} "
                  f"{len(t['bodyHtml']):5}b {t['title'][:60]}")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"ok: {len(talks)} постов → {OUT}")


if __name__ == "__main__":
    main()
