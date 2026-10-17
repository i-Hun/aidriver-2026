#!/usr/bin/env python3
"""Собирает данные раздела /stories/aidriver-2026 из волта.

Источник: ~/.hermes/workspace/notes/projects/Статьи/AI Driver & RecSys 2026 — доклады.md
          ~/.hermes/workspace/notes/projects/Статьи/AI Driver & RecSys 2026 — посты канала.md
          (другой каталог заметок — переменная окружения AIDRIVER_NOTES)

Выход:   data/aidriver-2026.json в корне этого репозитория (страница импортирует его при сборке)

Запуск:  python3 scripts/aidriver_site_data.py [--check]
         --check  не писать файл, только напечатать статистику и расхождения.
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
LABEL_ORDER = [
    "Что показали",
    "Что ещё прозвучало",
    "Метод/архитектура",
    "Бенчмарки",
    "Вопросы и направления",
    "Что взять в наш проект",
    "Оговорки",
    "Формулировка",
]

HEAD_RE = re.compile(r"^### (.+?) — (.+?) \((big|small), (\d{1,2}:\d{2})–(\d{1,2}:\d{2}) MSK\)\s*$")
ITEM_RE = re.compile(r"^- \*\*(.+?):\*\* (.+)$")
TAG_RE = re.compile(r"^#([A-Za-zА-Яа-я0-9_]+)")
POST_HEAD_RE = re.compile(r"^## (\d{1,2}:\d{2})–(\d{1,2}:\d{2}) MSK · (.+)$")
POST_ID_RE = re.compile(r"^message_id (\d+)")


def split_people(s: str) -> tuple[str, str]:
    """«Алексей Васильев, Sber AI Lab» → (спикер, организация).

    Пленарка перечисляет нескольких людей — тогда организация пустая,
    а строка спикеров остаётся целиком.
    """
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


def render_inline(text: str) -> str:
    """Экранирует HTML и превращает `code` в <code>code</code>."""
    out = html.escape(text, quote=False)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", out)


def parse_talks() -> list[dict]:
    lines = TALKS_MD.read_text(encoding="utf-8").splitlines()
    talks: list[dict] = []
    cur: dict | None = None
    for line in lines:
        m = HEAD_RE.match(line)
        if m:
            title, people, hall, t0, t1 = m.groups()
            speaker, org = split_people(people)
            cur = {
                "slug": f"{hall}-{t0.replace(':', '')}",
                "title": title.strip(),
                "speaker": speaker,
                "org": org,
                "hall": hall,
                "hallLabel": HALLS[hall],
                "time": f"{t0}–{t1}",
                "items": [],
                "tags": [],
            }
            talks.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("#") and " " not in line:
            for tag in TAG_RE.findall(line):
                if tag not in cur["tags"]:
                    cur["tags"].append(tag)
            continue
        mi = ITEM_RE.match(line)
        if mi:
            label, text = mi.groups()
            cur["items"].append({"label": label.strip(), "text": text.strip(),
                                 "html": render_inline(text.strip())})
    for t in talks:
        order = {lab: i for i, lab in enumerate(LABEL_ORDER)}
        t["items"].sort(key=lambda it: order.get(it["label"], 99))
        # карточка на сайте показывает «Что показали» целиком и остальное по раскрытию
        lead = next((it for it in t["items"] if it["label"] == "Что показали"), None)
        lead_text = re.sub(r"[`*]", "", lead["text"] if lead else "")
        if len(lead_text) > 320:
            head = lead_text[:320]
            dot = max(head.rfind(". "), head.rfind("! "), head.rfind("? "))
            lead_text = (head[: dot + 1] if dot > 120 else head.rsplit(" ", 1)[0].rstrip(",;:") + "…")
        t["lead"] = lead_text
    return talks


def parse_posts() -> list[dict]:
    if not POSTS_MD.exists():
        return []
    lines = POSTS_MD.read_text(encoding="utf-8").splitlines()
    posts: list[dict] = []
    cur: dict | None = None
    for line in lines:
        m = POST_HEAD_RE.match(line)
        if m:
            t0, t1, rest = m.groups()
            title, _, people = rest.partition(" — ")
            cur = {"time": f"{t0}–{t1}", "title": title.strip(),
                   "people": people.strip(), "messageId": None}
            posts.append(cur)
            continue
        if cur is None:
            continue
        mi = POST_ID_RE.match(line)
        if mi:
            cur["messageId"] = int(mi.group(1))
    return [p for p in posts if p["messageId"]]


def norm(s: str) -> str:
    return re.sub(r"[^a-zа-я0-9]+", " ", s.lower()).strip()


def tokens(s: str) -> set[str]:
    return {w for w in norm(s).split() if len(w) > 2}


def match_post(talk: dict, posts: list[dict]) -> dict | None:
    """Пост сопоставляется по пересечению слов заголовка и по времени."""
    best, best_score = None, 0.0
    tt = tokens(talk["title"])
    for p in posts:
        pt = tokens(p["title"])
        if not tt or not pt:
            continue
        score = len(tt & pt) / min(len(tt), len(pt))
        if p["time"] == talk["time"]:
            score += 0.15
        if score > best_score:
            best, best_score = p, score
    if best is not None and best_score >= 0.6:
        return best
    return None


def main() -> None:
    check = "--check" in sys.argv
    talks = parse_talks()
    posts = parse_posts()
    for t in talks:
        p = match_post(t, posts)
        t["post"] = ({"messageId": p["messageId"],
                      "url": f"https://t.me/ai_n_ns/{p['messageId']}"} if p else None)

    now = datetime.now(MSK)
    live = now.date().isoformat() == "2026-10-17" and now.hour * 60 + now.minute < 17 * 60 + 25
    data = {
        "event": {
            "title": "AI Driver & RecSys 2026",
            "subtitle": "Конференция Сбера по рекомендательным системам: разборы докладов по записи",
            "date": "17 октября 2026",
            "place": "Офис Сбера, Москва, Кутузовский пр-т 32",
            "programUrl": "https://developers.sber.ru/kak-v-sbere/events/ai_driver_october_2026",
            "channelUrl": "https://t.me/ai_n_ns",
            "sourceNote": "Разборы собраны по собственной записи двух потоков и её расшифровке "
                          "(faster-whisper large-v3-turbo). Числа — только те, что прозвучали в докладе.",
        },
        "updated": now.isoformat(timespec="minutes"),
        "live": live,
        "stats": {
            "talks": len(talks),
            "halls": len({t["hall"] for t in talks}),
            "withPost": sum(1 for t in talks if t["post"]),
        },
        "talks": talks,
    }
    if check:
        print(json.dumps(data["stats"], ensure_ascii=False))
        for t in talks:
            print(f"{t['slug']:11} {t['time']:13} {t['hallLabel']:12} "
                  f"items={len(t['items']):2} post={t['post']['messageId'] if t['post'] else '—':>5} "
                  f"{t['title'][:60]}")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"ok: {len(talks)} докладов, {data['stats']['withPost']} с постом → {OUT}")


if __name__ == "__main__":
    main()
