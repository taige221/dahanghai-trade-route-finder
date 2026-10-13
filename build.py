#!/usr/bin/env python3
"""Build the self-contained ROM trade route finder."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "rom-investigation/output/trade-prices-long.csv"
OUT_PATH = Path(__file__).with_name("index.html")
CHARACTER_SCRIPT = ROOT / "rom-investigation/extract_character_data.py"
CHARACTER_JSON = ROOT / "rom-investigation/output/character-roster.json"
ITEM_SCRIPT = ROOT / "rom-investigation/extract_item_data.py"
ITEM_JSON = ROOT / "rom-investigation/output/item-catalog.json"
PORTRAIT_DIR = Path(__file__).with_name("assets") / "portraits"

PRICE_COLUMNS = [
    "外国港_无证无月卡买价",
    "本国或中立_无证无月卡买价",
    "外国港_交易月卡买价",
    "本国或中立_交易月卡买价",
    "外国港_对应免税证买价",
    "本国或中立_对应免税证买价",
]


def load_data() -> dict:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    ports = [None] * (max(int(row["port_id"]) for row in rows) + 1)
    goods = [None] * (max(int(row["good_id"]) for row in rows) + 1)
    for row in rows:
        ports[int(row["port_id"])] = row["港口"]
        goods[int(row["good_id"])] = row["贸易品"]

    sells = [[0] * len(goods) for _ in ports]
    offers: list[list[list[int]]] = [[] for _ in ports]
    for row in rows:
        port_id = int(row["port_id"])
        good_id = int(row["good_id"])
        sells[port_id][good_id] = int(row["交易所初始收购价"])
        if row["本港出售"] == "是":
            offers[port_id].append(
                [
                    good_id,
                    1 if row["货源"] == "本港特产" else 0,
                    *[int(row[column]) for column in PRICE_COLUMNS],
                ]
            )

    assert len(rows) == 8800
    assert len(ports) == 110 and all(ports)
    assert len(goods) == 80 and all(goods)
    assert all(len(row) == 80 for row in sells)
    assert all(len(row) == 10 for row in offers)
    characters = json.loads(CHARACTER_JSON.read_text(encoding="utf-8"))
    assert len(characters) == 165
    assert all(item["name"] and item["portrait"] for item in characters)
    assert len(list(PORTRAIT_DIR.glob("[0-9][0-9][0-9].png"))) == 165
    items = json.loads(ITEM_JSON.read_text(encoding="utf-8"))
    assert len(items) == 121
    assert len({item["id"] for item in items}) == 121
    assert sum(item["category"] == "武器" for item in items) == 34
    assert sum(item["category"] == "防具" for item in items) == 16
    return {"ports": ports, "goods": goods, "sells": sells, "offers": offers, "characters": characters, "items": items}


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark light">
  <link rel="icon" href="data:,">
  <title>航路账房 · 大航海时代2 二改贸易查询器</title>
  <style>
    :root {
      --ink: #10252a;
      --navy: #071b22;
      --navy-2: #0d2a32;
      --sea: #176b6d;
      --sea-bright: #39aaa4;
      --brass: #c69c54;
      --brass-light: #e4c987;
      --paper: #f0e5c9;
      --paper-2: #e4d2aa;
      --paper-line: rgba(50, 70, 64, .18);
      --gain: #146a4b;
      --loss: #a33a32;
      --flat: #75684f;
      --white: #f7f3e8;
      --shadow: 0 24px 70px rgba(0, 0, 0, .32);
    }

    * { box-sizing: border-box; }
    html { min-width: 320px; scroll-behavior: smooth; }
    body {
      margin: 0;
      color: var(--white);
      background:
        radial-gradient(circle at 12% 8%, rgba(57, 170, 164, .14), transparent 27rem),
        linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px),
        var(--navy);
      background-size: auto, 44px 44px, 44px 44px, auto;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      min-height: 100vh;
    }

    button, input, select { font: inherit; }
    button { cursor: pointer; }
    .shell { width: min(1480px, calc(100% - 40px)); margin: 0 auto; padding: 28px 0 56px; }

    .masthead {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 20px;
      align-items: center;
      padding: 8px 2px 28px;
      border-bottom: 1px solid rgba(228, 201, 135, .28);
    }
    .compass {
      width: 62px; height: 62px; border: 1px solid var(--brass); border-radius: 50%;
      display: grid; place-items: center; color: var(--brass-light); position: relative;
      box-shadow: inset 0 0 0 5px rgba(198, 156, 84, .08);
    }
    .compass::before, .compass::after { content: ""; position: absolute; background: rgba(228,201,135,.5); }
    .compass::before { width: 1px; height: 72px; }
    .compass::after { height: 1px; width: 72px; }
    .compass span { font: 700 20px Georgia, "Songti SC", serif; transform: rotate(-12deg); }
    .eyebrow { margin: 0 0 5px; color: var(--brass-light); font-size: 11px; letter-spacing: .24em; text-transform: uppercase; }
    h1 { margin: 0; font: 600 clamp(25px, 3vw, 42px)/1.1 Georgia, "Songti SC", "STSong", serif; letter-spacing: .04em; }
    .mast-note { color: rgba(247,243,232,.62); max-width: 340px; font-size: 12px; line-height: 1.65; text-align: right; }

    .workspace {
      display: grid; grid-template-columns: minmax(310px, 390px) minmax(0, 1fr); gap: 22px; margin-top: 24px;
    }
    .query-panel {
      align-self: start; position: sticky; top: 18px; padding: 24px;
      background: linear-gradient(145deg, rgba(18,51,59,.97), rgba(8,29,35,.98));
      border: 1px solid rgba(228,201,135,.32); border-radius: 4px 22px 4px 4px;
      box-shadow: var(--shadow);
    }
    .query-panel::after {
      content: "N  ·  E"; position: absolute; top: 16px; right: 18px; color: rgba(228,201,135,.42);
      font: 11px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .15em;
    }
    h2, h3 { font-family: Georgia, "Songti SC", serif; }
    .query-panel h2 { margin: 0 0 5px; font-size: 21px; font-weight: 600; }
    .subtle { margin: 0; color: rgba(247,243,232,.58); font-size: 12px; line-height: 1.55; }
    .form-grid { display: grid; gap: 15px; margin-top: 23px; }
    label { display: grid; gap: 7px; color: var(--brass-light); font-size: 11px; letter-spacing: .08em; }
    input, select {
      width: 100%; color: var(--white); background: rgba(2,16,20,.52); border: 1px solid rgba(228,201,135,.26);
      border-radius: 3px; padding: 12px 13px; outline: none; transition: border-color .18s, box-shadow .18s; font-size: 14px;
    }
    input::placeholder { color: rgba(247,243,232,.32); }
    input:focus, select:focus, button:focus-visible {
      border-color: var(--brass-light); box-shadow: 0 0 0 3px rgba(228,201,135,.13); outline: none;
    }
    .swap-row { display: grid; grid-template-columns: 1fr auto 1fr; align-items: end; gap: 8px; }
    .swap-btn { width: 38px; height: 42px; padding: 0; border: 1px solid rgba(228,201,135,.3); border-radius: 50%; color: var(--brass-light); background: transparent; }
    .swap-btn:hover { background: rgba(228,201,135,.1); }
    .actions { display: flex; gap: 9px; margin-top: 4px; }
    .primary, .ghost {
      border-radius: 3px; padding: 11px 14px; border: 1px solid var(--brass); font-weight: 650;
    }
    .primary { flex: 1; color: #102329; background: var(--brass-light); }
    .primary:hover { background: #efd797; }
    .ghost { color: var(--brass-light); background: transparent; }
    .examples { margin-top: 21px; padding-top: 18px; border-top: 1px solid rgba(228,201,135,.18); }
    .examples > span { color: rgba(247,243,232,.48); font-size: 11px; }
    .chips { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 9px; }
    .chip { border: 1px solid rgba(57,170,164,.35); border-radius: 999px; color: #b8ddd7; background: rgba(57,170,164,.07); padding: 7px 10px; font-size: 11px; }
    .chip:hover { border-color: var(--sea-bright); background: rgba(57,170,164,.14); }

    .main-stage { min-width: 0; }
    .status-line { min-height: 26px; padding: 2px 2px 10px; color: rgba(247,243,232,.65); font-size: 12px; }
    .status-line.error { color: #ffaaa2; }
    .summary {
      display: grid; grid-template-columns: 1.45fr repeat(3, minmax(100px, .62fr));
      background: var(--paper); color: var(--ink); border-radius: 4px 4px 16px 4px; overflow: hidden;
      box-shadow: var(--shadow); border: 1px solid rgba(228,201,135,.75);
    }
    .best-route { padding: 26px 28px; position: relative; background: linear-gradient(135deg, rgba(255,255,255,.22), transparent 55%); }
    .best-route::after { content: "最佳单程"; position: absolute; top: 17px; right: 20px; border: 1px solid rgba(163,58,50,.42); color: var(--loss); transform: rotate(3deg); padding: 4px 7px; font: 700 10px serif; letter-spacing: .12em; }
    .best-label { color: #5a6d69; font-size: 11px; letter-spacing: .14em; }
    .route-name { margin: 9px 0 5px; font: 600 clamp(19px, 2.4vw, 31px)/1.2 Georgia, "Songti SC", serif; }
    .route-good { color: var(--sea); font-weight: 750; }
    .metric { display: flex; flex-direction: column; justify-content: center; padding: 20px; border-left: 1px solid rgba(16,37,42,.14); }
    .metric span { color: #64746e; font-size: 11px; }
    .metric strong { margin-top: 7px; font: 700 clamp(20px, 2vw, 28px)/1 ui-monospace, SFMono-Regular, Menlo, monospace; }
    .metric .positive { color: var(--gain); }
    .metric .negative { color: var(--loss); }
    .metric .flat { color: var(--flat); }

    .roundtrip {
      margin-top: 14px; padding: 16px 20px; display: flex; gap: 14px; align-items: center; color: #d7ece7;
      background: rgba(23,107,109,.18); border: 1px solid rgba(57,170,164,.32); border-radius: 3px;
    }
    .roundtrip[hidden] { display: none; }
    .roundtrip-mark { flex: 0 0 auto; width: 34px; height: 34px; border: 1px solid var(--sea-bright); border-radius: 50%; display: grid; place-items: center; }
    .roundtrip strong { color: #fff; }
    .roundtrip p { margin: 3px 0 0; color: rgba(215,236,231,.68); font-size: 12px; line-height: 1.5; }

    .ledger { margin-top: 15px; color: var(--ink); background: var(--paper); border-radius: 3px; box-shadow: var(--shadow); overflow: hidden; }
    .ledger-head {
      display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 17px 20px;
      border-bottom: 1px solid rgba(16,37,42,.22); background: var(--paper-2);
    }
    .ledger-head h2 { margin: 0; font-size: 19px; }
    .ledger-tools { display: flex; gap: 8px; align-items: center; }
    .ledger-tools label { color: #5b655f; letter-spacing: 0; display: flex; align-items: center; gap: 6px; }
    .ledger-tools select { width: auto; min-width: 106px; color: var(--ink); background: rgba(255,255,255,.38); border-color: rgba(16,37,42,.25); padding: 7px 9px; }
    .table-wrap { overflow: auto; max-height: 650px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
    th { position: sticky; top: 0; z-index: 2; padding: 12px 13px; color: #5c6b65; background: #eadbb9; text-align: left; white-space: nowrap; font-size: 10px; letter-spacing: .08em; }
    td { padding: 12px 13px; border-top: 1px solid var(--paper-line); white-space: nowrap; }
    tbody tr:nth-child(even) { background: rgba(255,255,255,.16); }
    tbody tr:hover { background: rgba(57,170,164,.09); }
    td.num { text-align: right; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .profit { font-weight: 800; }
    .profit.positive { color: var(--gain); }
    .profit.negative { color: var(--loss); }
    .profit.flat { color: var(--flat); }
    .badge { display: inline-block; padding: 3px 6px; border: 1px solid rgba(23,107,109,.35); border-radius: 999px; color: var(--sea); font-size: 10px; }
    .badge.special { border-color: rgba(198,156,84,.8); color: #7c5518; background: rgba(198,156,84,.1); }
    .empty { padding: 70px 25px; text-align: center; color: #69756f; }
    .empty-mark { width: 70px; height: 70px; margin: 0 auto 14px; border: 1px solid rgba(23,107,109,.38); border-radius: 50%; display: grid; place-items: center; color: var(--sea); font: 25px Georgia,serif; }
    .empty h3 { color: var(--ink); margin: 0 0 8px; }
    .footnotes { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 15px; }
    .note { padding: 15px 17px; border: 1px solid rgba(228,201,135,.2); color: rgba(247,243,232,.63); font-size: 11px; line-height: 1.65; }
    .note strong { color: var(--brass-light); }

    .primary-nav { display: flex; gap: 2px; margin-top: 18px; border-bottom: 1px solid rgba(228,201,135,.28); }
    .nav-tab { position: relative; min-width: 140px; padding: 13px 18px 12px; border: 0; color: rgba(247,243,232,.62); background: transparent; font-weight: 700; letter-spacing: .05em; }
    .nav-tab::after { content: ""; position: absolute; inset: auto 16px -1px; height: 2px; background: var(--brass-light); transform: scaleX(0); transition: transform .18s ease; }
    .nav-tab:hover { color: var(--white); background: rgba(228,201,135,.06); }
    .nav-tab[aria-selected="true"] { color: var(--brass-light); }
    .nav-tab[aria-selected="true"]::after { transform: scaleX(1); }
    .page-panel[hidden] { display: none !important; }

    .character-workspace { margin-top: 24px; }
    .roster-intro { display: grid; grid-template-columns: 1fr auto; gap: 22px; align-items: end; margin-bottom: 18px; }
    .roster-intro h2 { margin: 0 0 7px; font-size: clamp(24px, 3vw, 38px); font-weight: 600; }
    .roster-intro p { max-width: 760px; margin: 0; color: rgba(247,243,232,.62); font-size: 13px; line-height: 1.7; }
    .roster-count { padding: 10px 14px; border: 1px solid rgba(228,201,135,.32); color: var(--brass-light); font: 700 13px ui-monospace, SFMono-Regular, Menlo, monospace; }
    .roster-filters { display: grid; grid-template-columns: minmax(220px, 1.5fr) repeat(3, minmax(130px, .8fr)) auto; gap: 10px; padding: 14px; background: rgba(8,29,35,.92); border: 1px solid rgba(228,201,135,.28); }
    .roster-filters label { letter-spacing: .04em; }
    .roster-filters .ghost { align-self: end; height: 43px; }
    .roster-examples { display: flex; align-items: center; flex-wrap: wrap; gap: 7px; padding: 11px 2px 15px; }
    .roster-examples > span { margin-right: 3px; color: rgba(247,243,232,.48); font-size: 11px; }
    .roster-body { display: grid; grid-template-columns: minmax(390px, .9fr) minmax(450px, 1.15fr); gap: 16px; min-height: 610px; }
    .roster-list-shell, .dossier { min-width: 0; border: 1px solid rgba(228,201,135,.5); box-shadow: var(--shadow); }
    .roster-list-shell { background: var(--paper); color: var(--ink); }
    .roster-list-head { display: flex; justify-content: space-between; gap: 12px; padding: 13px 16px; background: var(--paper-2); border-bottom: 1px solid rgba(16,37,42,.2); font-size: 12px; }
    .roster-list { max-height: 720px; overflow: auto; }
    .person-row { width: 100%; display: grid; grid-template-columns: 58px minmax(130px, 1.2fr) minmax(90px, .8fr) minmax(85px, .7fr); gap: 11px; align-items: center; padding: 10px 13px; border: 0; border-bottom: 1px solid var(--paper-line); color: var(--ink); background: transparent; text-align: left; }
    .person-row:hover, .person-row[aria-current="true"] { background: rgba(23,107,109,.1); }
    .person-row[aria-current="true"] { box-shadow: inset 3px 0 var(--sea); }
    .person-row img { width: 45px; height: 54px; object-fit: contain; image-rendering: pixelated; border: 2px solid #87662f; background: #fff; }
    .person-name { display: block; font: 700 15px Georgia, "Songti SC", serif; }
    .person-meta { display: block; margin-top: 4px; color: #64746e; font-size: 10px; }
    .person-port, .person-levels { font-size: 11px; line-height: 1.45; }
    .person-levels { text-align: right; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .roster-empty { padding: 72px 24px; text-align: center; color: #64746e; }

    .dossier { align-self: start; position: sticky; top: 18px; color: var(--ink); background: var(--paper); }
    .dossier-banner { display: grid; grid-template-columns: 168px 1fr; min-height: 188px; background: linear-gradient(135deg, #d5bd86, var(--paper) 48%, #e8dab8); border-bottom: 1px solid rgba(16,37,42,.2); }
    .portrait-plate { position: relative; display: grid; place-items: center; padding: 18px; background: linear-gradient(145deg, #0d2a32, #06191f); border-right: 1px solid rgba(198,156,84,.55); }
    .portrait-plate img { width: 120px; height: 144px; image-rendering: pixelated; object-fit: contain; border: 5px solid #9d7939; outline: 1px solid #e4c987; background: #fff; }
    .portrait-plate span { position: absolute; bottom: 8px; padding: 3px 8px; color: #241b0f; background: var(--brass-light); font: 700 9px ui-monospace, monospace; letter-spacing: .12em; }
    .dossier-title { position: relative; padding: 24px 24px 18px; }
    .dossier-kicker { color: #6d755f; font-size: 10px; letter-spacing: .16em; }
    .dossier-title h2 { margin: 8px 0 9px; font-size: clamp(24px, 3vw, 36px); line-height: 1.05; }
    .identity-line { display: flex; flex-wrap: wrap; gap: 6px; }
    .tag { display: inline-block; padding: 4px 7px; border: 1px solid rgba(23,107,109,.35); color: var(--sea); font-size: 10px; }
    .tag.country { border-color: rgba(163,58,50,.35); color: #7e342f; }
    .name-warning { margin: 10px 0 0; color: #8a3b34; font-size: 11px; }
    .sea-legend { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center; margin: 16px 18px 0; padding: 13px 15px; color: #d7ece7; background: var(--navy-2); border-left: 4px solid var(--sea-bright); }
    .sea-legend small { display: block; color: rgba(215,236,231,.62); font-size: 10px; letter-spacing: .1em; }
    .sea-legend strong { display: block; margin-top: 4px; font: 600 18px Georgia, "Songti SC", serif; }
    .sea-legend .port { color: var(--brass-light); text-align: right; font-size: 12px; }
    .levels-strip { display: grid; grid-template-columns: repeat(4, 1fr); margin: 14px 18px 0; border: 1px solid rgba(16,37,42,.18); }
    .level-cell { padding: 11px 12px; border-right: 1px solid rgba(16,37,42,.15); }
    .level-cell:last-child { border: 0; }
    .level-cell span { display: block; color: #6b766f; font-size: 9px; }
    .level-cell strong { display: block; margin-top: 4px; font: 700 17px ui-monospace, monospace; }
    .dossier-section { padding: 17px 18px 2px; }
    .dossier-section h3 { margin: 0 0 11px; color: #5a625d; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; }
    .attribute-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; }
    .attribute { display: grid; grid-template-columns: 42px 1fr 30px; gap: 8px; align-items: center; font-size: 11px; }
    .attribute-bar { height: 6px; background: rgba(16,37,42,.12); }
    .attribute-bar i { display: block; height: 100%; background: linear-gradient(90deg, var(--sea), var(--brass)); }
    .attribute b { text-align: right; font-family: ui-monospace, monospace; }
    .skill-line { display: flex; flex-wrap: wrap; gap: 6px; min-height: 28px; }
    .skill { padding: 5px 8px; color: #503d1d; background: rgba(198,156,84,.16); border: 1px solid rgba(126,91,32,.32); font-size: 11px; }
    .audit-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px 16px; padding-bottom: 18px; color: #5d6762; font-size: 10px; line-height: 1.5; }
    .audit-grid strong { display: block; color: var(--ink); font: 600 11px ui-monospace, monospace; overflow-wrap: anywhere; }

    .item-workspace { margin-top: 24px; }
    .item-filters { display: grid; grid-template-columns: minmax(240px, 1.5fr) minmax(150px, .7fr) minmax(170px, .8fr) auto; gap: 10px; padding: 14px; background: rgba(8,29,35,.92); border: 1px solid rgba(228,201,135,.28); }
    .item-filters .ghost { align-self: end; height: 43px; }
    .item-body { display: grid; grid-template-columns: minmax(390px, .86fr) minmax(480px, 1.2fr); gap: 16px; min-height: 610px; }
    .item-list-shell, .item-detail { min-width: 0; border: 1px solid rgba(228,201,135,.5); box-shadow: var(--shadow); }
    .item-list-shell { color: var(--ink); background: var(--paper); }
    .item-list { max-height: 720px; overflow: auto; }
    .item-row { width: 100%; display: grid; grid-template-columns: 45px minmax(150px, 1.2fr) minmax(92px, .65fr) minmax(95px, .75fr); gap: 11px; align-items: center; padding: 11px 13px; border: 0; border-bottom: 1px solid var(--paper-line); color: var(--ink); background: transparent; text-align: left; }
    .item-row:hover, .item-row[aria-current="true"] { background: rgba(23,107,109,.1); }
    .item-row[aria-current="true"] { box-shadow: inset 3px 0 var(--sea); }
    .item-mark { width: 36px; height: 36px; display: grid; place-items: center; color: #3f351f; background: #dbc184; border: 1px solid #87662f; font: 700 16px Georgia, "Songti SC", serif; }
    .item-name { display: block; font: 700 15px Georgia, "Songti SC", serif; }
    .item-meta { display: block; margin-top: 4px; color: #64746e; font: 10px ui-monospace, monospace; }
    .item-price, .item-place { font-size: 11px; line-height: 1.45; }
    .item-price { text-align: right; font-family: ui-monospace, monospace; }
    .item-detail { align-self: start; position: sticky; top: 18px; color: var(--ink); background: var(--paper); }
    .item-banner { display: grid; grid-template-columns: 130px 1fr; min-height: 150px; background: linear-gradient(135deg, #d5bd86, var(--paper) 52%, #e8dab8); border-bottom: 1px solid rgba(16,37,42,.2); }
    .item-emblem { display: grid; place-items: center; background: linear-gradient(145deg, #0d2a32, #06191f); border-right: 1px solid rgba(198,156,84,.55); }
    .item-emblem span { width: 72px; height: 72px; display: grid; place-items: center; border: 2px solid var(--brass); border-radius: 50%; color: var(--brass-light); font: 700 28px Georgia, "Songti SC", serif; box-shadow: inset 0 0 0 6px rgba(198,156,84,.08); }
    .item-title { padding: 24px 24px 18px; }
    .item-title h2 { margin: 8px 0 10px; font-size: clamp(25px, 3vw, 37px); line-height: 1.05; }
    .item-stats { display: grid; grid-template-columns: repeat(4, 1fr); margin: 14px 18px 0; border: 1px solid rgba(16,37,42,.18); }
    .item-stat { min-width: 0; padding: 11px 12px; border-right: 1px solid rgba(16,37,42,.15); }
    .item-stat:last-child { border: 0; }
    .item-stat span { display: block; color: #6b766f; font-size: 9px; }
    .item-stat strong { display: block; margin-top: 4px; font: 700 14px ui-monospace, monospace; overflow-wrap: anywhere; }
    .item-section { padding: 17px 18px 0; }
    .item-section:last-child { padding-bottom: 20px; }
    .item-section h3 { margin: 0 0 10px; color: #5a625d; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; }
    .effect-card { padding: 13px 15px; color: #d7ece7; background: var(--navy-2); border-left: 4px solid var(--sea-bright); font-size: 12px; line-height: 1.7; }
    .port-group { margin-top: 10px; }
    .port-group:first-of-type { margin-top: 0; }
    .port-group b { display: block; margin-bottom: 7px; color: #66736d; font-size: 10px; }
    .port-tags { display: flex; flex-wrap: wrap; gap: 6px; }
    .port-tag { padding: 5px 7px; color: #365b59; background: rgba(23,107,109,.08); border: 1px solid rgba(23,107,109,.25); font-size: 10px; }
    .port-tag.hidden { color: #79521b; background: rgba(198,156,84,.12); border-color: rgba(126,91,32,.3); }
    .evidence-card { padding: 11px 13px; color: #626d67; background: rgba(255,255,255,.2); border: 1px solid rgba(16,37,42,.14); font-size: 10px; line-height: 1.65; }

    @media (max-width: 980px) {
      .workspace { grid-template-columns: 1fr; }
      .query-panel { position: relative; top: auto; border-radius: 4px 18px 4px 4px; }
      .form-grid { grid-template-columns: 1fr 1fr; }
      .form-grid .full, .actions { grid-column: 1 / -1; }
      .summary { grid-template-columns: 1fr 1fr 1fr; }
      .best-route { grid-column: 1 / -1; border-bottom: 1px solid rgba(16,37,42,.14); }
      .metric:first-of-type { border-left: 0; }
      .roster-filters { grid-template-columns: 1fr 1fr; }
      .roster-filters .ghost { grid-column: 2; }
      .roster-body { grid-template-columns: 1fr; }
      .dossier { position: relative; top: auto; }
      .roster-list { max-height: 520px; }
      .item-filters { grid-template-columns: 1fr 1fr; }
      .item-filters .ghost { grid-column: 2; }
      .item-body { grid-template-columns: 1fr; }
      .item-detail { position: relative; top: auto; }
      .item-list { max-height: 520px; }
    }
    @media (max-width: 650px) {
      .shell { width: min(100% - 22px, 1480px); padding-top: 17px; }
      .masthead { grid-template-columns: auto 1fr; }
      .mast-note { display: none; }
      .compass { width: 48px; height: 48px; }
      .compass::before { height: 56px; } .compass::after { width: 56px; }
      .form-grid { grid-template-columns: 1fr; }
      .form-grid .full, .actions { grid-column: auto; }
      .swap-row { grid-template-columns: 1fr auto; }
      .swap-row label:last-child { grid-column: 1 / -1; }
      .summary { grid-template-columns: 1fr; }
      .best-route { grid-column: auto; padding: 22px; }
      .metric { border-left: 0; border-top: 1px solid rgba(16,37,42,.14); padding: 14px 22px; flex-direction: row; align-items: center; justify-content: space-between; }
      .metric strong { margin: 0; }
      .roundtrip { align-items: flex-start; }
      .ledger-head { align-items: flex-start; flex-direction: column; }
      .ledger-tools { width: 100%; flex-wrap: wrap; }
      .footnotes { grid-template-columns: 1fr; }
      th, td { padding: 11px 10px; }
      .primary-nav { overflow-x: auto; }
      .nav-tab { min-width: 124px; }
      .roster-intro { grid-template-columns: 1fr; }
      .roster-count { justify-self: start; }
      .roster-filters { grid-template-columns: 1fr; }
      .roster-filters .ghost { grid-column: auto; }
      #character-search { font-size: 16px; }
      .item-filters { grid-template-columns: 1fr; }
      .item-filters .ghost { grid-column: auto; }
      #item-search { font-size: 16px; }
      .person-row { grid-template-columns: 52px minmax(0, 1fr) auto; }
      .person-row img { width: 40px; height: 48px; }
      .person-port { display: none; }
      .dossier-banner { grid-template-columns: 116px 1fr; min-height: 154px; }
      .portrait-plate { padding: 10px; }
      .portrait-plate img { width: 80px; height: 96px; border-width: 4px; }
      .dossier-title { padding: 18px 14px 14px; }
      .levels-strip { grid-template-columns: 1fr 1fr; }
      .level-cell:nth-child(2) { border-right: 0; }
      .level-cell:nth-child(-n+2) { border-bottom: 1px solid rgba(16,37,42,.15); }
      .attribute-grid, .audit-grid { grid-template-columns: 1fr; }
      .item-row { grid-template-columns: 42px minmax(0, 1fr) auto; }
      .item-place { display: none; }
      .item-banner { grid-template-columns: 92px 1fr; }
      .item-emblem span { width: 58px; height: 58px; font-size: 22px; }
      .item-title { padding: 19px 14px 15px; }
      .item-stats { grid-template-columns: 1fr 1fr; }
      .item-stat:nth-child(2) { border-right: 0; }
      .item-stat:nth-child(-n+2) { border-bottom: 1px solid rgba(16,37,42,.15); }
    }
    @media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } * { transition: none !important; } }
  </style>
</head>
<body>
  <div class="shell">
    <header class="masthead">
      <div class="compass" aria-hidden="true"><span>航</span></div>
      <div>
        <p class="eyebrow">Captain's Trade Ledger · ROM DATA</p>
        <h1>航路账房</h1>
      </div>
      <div class="mast-note">大航海时代2 · 4110423 二改<br>110港口 × 80贸易品 · 初始价格推演</div>
    </header>

    <nav class="primary-nav" aria-label="主功能">
      <button class="nav-tab" type="button" data-page="trade-page" aria-selected="true">贸易航路</button>
      <button class="nav-tab" type="button" data-page="character-page" aria-selected="false">人物名册</button>
      <button class="nav-tab" type="button" data-page="item-page" aria-selected="false">道具图鉴</button>
    </nav>

    <main class="workspace page-panel" id="trade-page">
      <aside class="query-panel" aria-labelledby="query-title">
        <h2 id="query-title">绘制贸易航线</h2>
        <p class="subtle">任意填写一项即可查询；组合条件会自动收窄路线。</p>
        <div class="form-grid">
          <div class="swap-row full">
            <label>起点港
              <input id="origin" list="port-list" autocomplete="off" placeholder="例如：卑尔根">
            </label>
            <button class="swap-btn" id="swap" type="button" title="交换起点与目的地" aria-label="交换起点与目的地">⇄</button>
            <label>目的港
              <input id="destination" list="port-list" autocomplete="off" placeholder="可留空，自动找最佳港">
            </label>
          </div>
          <label>贸易品
            <input id="good" list="good-list" autocomplete="off" placeholder="可留空，例如：黄金">
          </label>
          <label>买价档位
            <select id="tier">
              <option value="0">外国港 · 无证无月卡</option>
              <option value="1">本国或中立 · 无证无月卡</option>
              <option value="2">外国港 · 交易月卡</option>
              <option value="3">本国或中立 · 交易月卡</option>
              <option value="4">外国港 · 对应免税证</option>
              <option value="5">本国或中立 · 对应免税证</option>
            </select>
          </label>
          <div class="actions">
            <button class="primary" id="search" type="button">计算航线</button>
            <button class="ghost" id="reset" type="button">清空</button>
          </div>
        </div>
        <div class="examples">
          <span>快速载入</span>
          <div class="chips">
            <button class="chip" data-origin="卑尔根" data-destination="汉堡">卑尔根 → 汉堡</button>
            <button class="chip" data-origin="休达" data-destination="比萨">休达 → 比萨</button>
            <button class="chip" data-origin="莫桑比克" data-good="黄金">莫桑比克 · 黄金</button>
            <button class="chip" data-good="钻石">全世界 · 钻石</button>
          </div>
        </div>
      </aside>

      <section class="main-stage">
        <div id="status" class="status-line" role="status" aria-live="polite">等待输入航线条件。</div>
        <section class="summary" id="summary" aria-label="最佳路线摘要">
          <div class="best-route">
            <div class="best-label">CURRENT BEST ROUTE</div>
            <div class="route-name" id="best-route">输入港口或贸易品</div>
            <div class="route-good" id="best-good">系统将按单位利润自动排序</div>
          </div>
          <div class="metric"><span>买入</span><strong id="best-buy">—</strong></div>
          <div class="metric"><span>卖出</span><strong id="best-sell">—</strong></div>
          <div class="metric"><span>单位利润</span><strong id="best-profit">—</strong></div>
        </section>

        <section class="roundtrip" id="roundtrip" hidden>
          <div class="roundtrip-mark" aria-hidden="true">↻</div>
          <div><strong id="roundtrip-title">往返建议</strong><p id="roundtrip-copy"></p></div>
        </section>

        <section class="ledger" aria-labelledby="ledger-title">
          <div class="ledger-head">
            <h2 id="ledger-title">贸易路线账册</h2>
            <div class="ledger-tools">
              <label>排序
                <select id="sort">
                  <option value="profit">单位利润</option>
                  <option value="roi">收益率</option>
                  <option value="sell">卖出价</option>
                  <option value="route">航线名称</option>
                </select>
              </label>
              <label>显示
                <select id="limit">
                  <option value="10">10条</option>
                  <option value="25" selected>25条</option>
                  <option value="50">50条</option>
                  <option value="all">全部</option>
                </select>
              </label>
            </div>
          </div>
          <div class="table-wrap" id="table-wrap">
            <div class="empty" id="empty">
              <div class="empty-mark">北</div>
              <h3>从一处港口开始</h3>
              <p>输入起点会列出当地全部货物的最佳出售地；也可以只输入贸易品查找全球价差。</p>
            </div>
            <table id="results-table" hidden>
              <thead><tr><th>#</th><th>起点港</th><th>贸易品</th><th>货源</th><th>买入</th><th>目的港</th><th>卖出</th><th>单位利润</th><th>收益率</th></tr></thead>
              <tbody id="results-body"></tbody>
            </table>
          </div>
        </section>

        <div class="footnotes">
          <div class="note"><strong>价格口径</strong><br>全部数值来自当前 ROM 的初始价格表。买价使用左侧所选档位；卖价为目的港交易所初始收购价。</div>
          <div class="note"><strong>航海提示</strong><br>计算未计入航程、库存、海况与敌舰。大量货物集中卖入同一港会显著改变行情，贵重品建议分港出售。</div>
        </div>
      </section>
    </main>

    <main class="character-workspace page-panel" id="character-page" hidden>
      <header class="roster-intro">
        <div>
          <h2>港务局 · 航海士档案</h2>
          <p>名册来自当前 ROM 的 0–164 号人物静态表。初始活动海域只按开局港口或固定舰队母港归类；招募、剧情、换港和舰队任务都会改变实际位置。</p>
        </div>
        <div class="roster-count"><strong id="character-total">165</strong> 名已录入</div>
      </header>

      <section class="roster-filters" aria-label="人物筛选">
        <label>姓名搜索
          <input id="character-search" type="search" autocomplete="off" placeholder="输入姓名或片段，例如：艾泽格">
        </label>
        <label>国家 / 阵营
          <select id="character-country"><option value="">全部阵营</option></select>
        </label>
        <label>身份
          <select id="character-identity"><option value="">全部身份</option></select>
        </label>
        <label>初始活动海域
          <select id="character-region"><option value="">全部海域</option></select>
        </label>
        <button class="ghost" type="button" id="character-reset">清空</button>
      </section>
      <div class="roster-examples">
        <span>快速查档</span>
        <button class="chip person-example" data-name="艾泽格">艾泽格</button>
        <button class="chip person-example" data-name="戴维·琼斯">戴维·琼斯</button>
        <button class="chip person-example" data-name="多明戈">多明戈</button>
        <button class="chip person-example" data-name="吕蓓卡">吕蓓卡</button>
        <button class="chip person-example" data-name="洛克">洛克</button>
      </div>

      <div class="roster-body">
        <section class="roster-list-shell" aria-label="人物查询结果">
          <div class="roster-list-head"><span id="character-status" role="status" aria-live="polite">显示全部 165 人</span><span>航海 / 战斗</span></div>
          <div class="roster-list" id="character-list"></div>
        </section>
        <aside class="dossier" id="character-detail" aria-live="polite"></aside>
      </div>
    </main>

    <main class="item-workspace page-panel" id="item-page" hidden>
      <header class="roster-intro">
        <div>
          <h2>港务局 · 道具图鉴</h2>
          <p>合并当前 ROM 的商店、价格、装备与运行时类型表。可按名称、道具 ID 或港口搜索；没有代码证据的特殊效果会明确标为未核实。</p>
        </div>
        <div class="roster-count"><strong id="item-total">121</strong> 项已录入</div>
      </header>

      <section class="item-filters" aria-label="道具筛选">
        <label>名称 / 港口 / ID
          <input id="item-search" type="search" autocomplete="off" placeholder="例如：时之砂、威尼斯、0x97">
        </label>
        <label>类别
          <select id="item-category"><option value="">全部类别</option></select>
        </label>
        <label>获取方式
          <select id="item-availability"><option value="">全部获取方式</option></select>
        </label>
        <button class="ghost" type="button" id="item-reset">清空</button>
      </section>
      <div class="roster-examples">
        <span>快速查物</span>
        <button class="chip item-example" data-query="时之砂">时之砂</button>
        <button class="chip item-example" data-query="保心丹">保心丹</button>
        <button class="chip item-example" data-query="威尼斯">威尼斯隐藏物品</button>
        <button class="chip item-example" data-query="0x0D">0x0D</button>
      </div>

      <div class="item-body">
        <section class="item-list-shell" aria-label="道具查询结果">
          <div class="roster-list-head"><span id="item-status" role="status" aria-live="polite">显示全部 121 项</span><span>售价 / 获取地</span></div>
          <div class="item-list" id="item-list"></div>
        </section>
        <aside class="item-detail" id="item-detail" aria-live="polite"></aside>
      </div>
    </main>
  </div>

  <datalist id="port-list"></datalist>
  <datalist id="good-list"></datalist>
  <script>
  const DATA = __DATA__;
  const TIER_LABELS = [
    '外国港 · 无证无月卡', '本国或中立 · 无证无月卡',
    '外国港 · 交易月卡', '本国或中立 · 交易月卡',
    '外国港 · 对应免税证', '本国或中立 · 对应免税证'
  ];
  const $ = (id) => document.getElementById(id);
  const els = {
    origin: $('origin'), destination: $('destination'), good: $('good'), tier: $('tier'),
    status: $('status'), sort: $('sort'), limit: $('limit'), table: $('results-table'),
    body: $('results-body'), empty: $('empty'), roundtrip: $('roundtrip')
  };
  let currentRows = [];

  $('port-list').innerHTML = DATA.ports.map(x => `<option value="${x}"></option>`).join('');
  $('good-list').innerHTML = DATA.goods.map(x => `<option value="${x}"></option>`).join('');

  function resolve(value, values, kind) {
    const text = value.trim();
    if (!text) return { id: null };
    const exact = values.indexOf(text);
    if (exact >= 0) return { id: exact };
    const matches = values.map((name, id) => ({name, id})).filter(x => x.name.includes(text));
    if (matches.length === 1) return { id: matches[0].id, normalized: matches[0].name };
    if (!matches.length) return { error: `没有找到${kind}“${text}”` };
    return { error: `${kind}“${text}”有多个匹配：${matches.slice(0, 6).map(x => x.name).join('、')}` };
  }

  function route(origin, destination, offer, tier) {
    const good = offer[0];
    const buy = offer[2 + tier];
    const sell = DATA.sells[destination][good];
    const profit = sell - buy;
    return { origin, destination, good, source: offer[1], buy, sell, profit, roi: buy ? profit / buy * 100 : 0 };
  }

  function bestDestination(origin, offer, tier) {
    let best = null;
    for (let destination = 0; destination < DATA.ports.length; destination++) {
      if (destination === origin) continue;
      const candidate = route(origin, destination, offer, tier);
      if (!best || candidate.profit > best.profit || (candidate.profit === best.profit && candidate.sell > best.sell)) best = candidate;
    }
    return best;
  }

  function calculate() {
    const o = resolve(els.origin.value, DATA.ports, '起点港');
    const d = resolve(els.destination.value, DATA.ports, '目的港');
    const g = resolve(els.good.value, DATA.goods, '贸易品');
    const error = o.error || d.error || g.error;
    if (error) { showError(error); return; }
    const tier = Number(els.tier.value);
    const rows = [];

    if (o.id !== null) {
      for (const offer of DATA.offers[o.id]) {
        if (g.id !== null && offer[0] !== g.id) continue;
        if (d.id !== null) rows.push(route(o.id, d.id, offer, tier));
        else if (g.id !== null) {
          for (let destination = 0; destination < DATA.ports.length; destination++) {
            if (destination !== o.id) rows.push(route(o.id, destination, offer, tier));
          }
        } else rows.push(bestDestination(o.id, offer, tier));
      }
    } else if (d.id !== null) {
      for (let origin = 0; origin < DATA.ports.length; origin++) {
        if (origin === d.id) continue;
        for (const offer of DATA.offers[origin]) {
          if (g.id !== null && offer[0] !== g.id) continue;
          rows.push(route(origin, d.id, offer, tier));
        }
      }
    } else if (g.id !== null) {
      for (let origin = 0; origin < DATA.ports.length; origin++) {
        const offer = DATA.offers[origin].find(x => x[0] === g.id);
        if (!offer) continue;
        for (let destination = 0; destination < DATA.ports.length; destination++) {
          if (destination !== origin) rows.push(route(origin, destination, offer, tier));
        }
      }
    } else {
      currentRows = [];
      els.roundtrip.hidden = true;
      render();
      els.status.className = 'status-line';
      els.status.textContent = '等待输入航线条件。';
      return;
    }

    currentRows = rows;
    els.status.className = 'status-line';
    els.status.textContent = `找到 ${rows.length} 条路线 · 买价档位：${TIER_LABELS[tier]}`;
    updateRoundtrip(o.id, d.id, tier);
    render();
  }

  function showError(message) {
    currentRows = [];
    els.status.className = 'status-line error';
    els.status.textContent = message;
    els.roundtrip.hidden = true;
    render();
  }

  function sortedRows() {
    const rows = [...currentRows];
    const mode = els.sort.value;
    rows.sort((a, b) => {
      if (mode === 'route') return `${DATA.ports[a.origin]}${DATA.ports[a.destination]}${DATA.goods[a.good]}`.localeCompare(`${DATA.ports[b.origin]}${DATA.ports[b.destination]}${DATA.goods[b.good]}`, 'zh-CN');
      return (b[mode] - a[mode]) || (b.profit - a.profit);
    });
    return rows;
  }

  function money(n) { return n.toLocaleString('zh-CN'); }
  function profitClass(n) { return n > 0 ? 'positive' : n < 0 ? 'negative' : 'flat'; }

  function render() {
    const all = sortedRows();
    const limit = els.limit.value === 'all' ? all.length : Number(els.limit.value);
    const rows = all.slice(0, limit);
    els.empty.hidden = !!all.length;
    els.table.hidden = !all.length;
    if (!all.length) {
      $('best-route').textContent = '输入港口或贸易品';
      $('best-good').textContent = '系统将按单位利润自动排序';
      $('best-buy').textContent = $('best-sell').textContent = $('best-profit').textContent = '—';
      $('best-profit').className = '';
      els.body.innerHTML = '';
      return;
    }
    const best = [...all].sort((a,b) => b.profit - a.profit)[0];
    $('best-route').textContent = `${DATA.ports[best.origin]} → ${DATA.ports[best.destination]}`;
    $('best-good').textContent = `${DATA.goods[best.good]} · ${best.source ? '本港特产' : '普通货物'}`;
    $('best-buy').textContent = money(best.buy);
    $('best-sell').textContent = money(best.sell);
    $('best-profit').textContent = `${best.profit >= 0 ? '+' : ''}${money(best.profit)}`;
    $('best-profit').className = profitClass(best.profit);
    els.body.innerHTML = rows.map((r, index) => `
      <tr>
        <td class="num">${index + 1}</td>
        <td>${DATA.ports[r.origin]}</td>
        <td><strong>${DATA.goods[r.good]}</strong></td>
        <td><span class="badge ${r.source ? 'special' : ''}">${r.source ? '本港特产' : '普通货物'}</span></td>
        <td class="num">${money(r.buy)}</td>
        <td>${DATA.ports[r.destination]}</td>
        <td class="num">${money(r.sell)}</td>
        <td class="num profit ${profitClass(r.profit)}">${r.profit >= 0 ? '+' : ''}${money(r.profit)}</td>
        <td class="num profit ${profitClass(r.roi)}">${r.roi >= 0 ? '+' : ''}${r.roi.toFixed(1)}%</td>
      </tr>`).join('');
  }

  function bestForPair(origin, destination, tier) {
    return DATA.offers[origin]
      .map(offer => route(origin, destination, offer, tier))
      .sort((a,b) => b.profit - a.profit)[0];
  }

  function updateRoundtrip(origin, destination, tier) {
    if (origin === null || destination === null || origin === destination) { els.roundtrip.hidden = true; return; }
    const out = bestForPair(origin, destination, tier);
    const back = bestForPair(destination, origin, tier);
    els.roundtrip.hidden = false;
    $('roundtrip-title').textContent = `${DATA.ports[origin]} ⇄ ${DATA.ports[destination]} 往返建议`;
    const outText = out.profit > 0 ? `去程带 ${DATA.goods[out.good]}（+${out.profit}）` : '去程没有盈利货物';
    const backText = back.profit > 0 ? `返程带 ${DATA.goods[back.good]}（+${back.profit}）` : '返程没有盈利货物';
    const combined = Math.max(0, out.profit) + Math.max(0, back.profit);
    $('roundtrip-copy').textContent = `${outText}；${backText}。两方向最佳货物的单位利润合计 ${combined}。`;
  }

  let timer;
  function schedule() { clearTimeout(timer); timer = setTimeout(calculate, 140); }
  [els.origin, els.destination, els.good].forEach(el => el.addEventListener('input', schedule));
  [els.tier, els.sort, els.limit].forEach(el => el.addEventListener('change', el === els.tier ? calculate : render));
  $('search').addEventListener('click', calculate);
  $('reset').addEventListener('click', () => {
    els.origin.value = els.destination.value = els.good.value = '';
    els.tier.value = '0'; els.sort.value = 'profit'; els.limit.value = '25';
    els.roundtrip.hidden = true; calculate(); els.origin.focus();
  });
  $('swap').addEventListener('click', () => {
    [els.origin.value, els.destination.value] = [els.destination.value, els.origin.value]; calculate();
  });
  document.querySelectorAll('.chip').forEach(button => button.addEventListener('click', () => {
    if (button.classList.contains('person-example') || button.classList.contains('item-example')) return;
    els.origin.value = button.dataset.origin || '';
    els.destination.value = button.dataset.destination || '';
    els.good.value = button.dataset.good || '';
    calculate();
  }));

  const characterEls = {
    search: $('character-search'), country: $('character-country'), identity: $('character-identity'),
    region: $('character-region'), list: $('character-list'), detail: $('character-detail'),
    status: $('character-status')
  };
  let selectedCharacterId = 22;

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  }

  function uniqueSorted(values) {
    return [...new Set(values)].sort((a, b) => a.localeCompare(b, 'zh-CN'));
  }

  function populateCharacterFilters() {
    const filters = [
      [characterEls.country, uniqueSorted(DATA.characters.map(x => x.countryGroup))],
      [characterEls.identity, uniqueSorted(DATA.characters.map(x => x.identity))],
      [characterEls.region, uniqueSorted(DATA.characters.map(x => x.initialRegion))]
    ];
    for (const [select, values] of filters) {
      select.insertAdjacentHTML('beforeend', values.map(value => `<option value="${escapeHTML(value)}">${escapeHTML(value)}</option>`).join(''));
    }
  }

  function filteredCharacters() {
    const query = characterEls.search.value.trim().toLocaleLowerCase('zh-CN');
    return DATA.characters.filter(item => {
      const searchable = [item.name, ...(item.aliases || [])].join(' ').toLocaleLowerCase('zh-CN');
      return (!query || searchable.includes(query)) &&
        (!characterEls.country.value || item.countryGroup === characterEls.country.value) &&
        (!characterEls.identity.value || item.identity === characterEls.identity.value) &&
        (!characterEls.region.value || item.initialRegion === characterEls.region.value);
    });
  }

  function renderCharacterList() {
    const rows = filteredCharacters();
    characterEls.status.textContent = rows.length ? `找到 ${rows.length} / ${DATA.characters.length} 人` : '没有匹配人物';
    if (!rows.length) {
      characterEls.list.innerHTML = `<div class="roster-empty"><div class="empty-mark">档</div><h3>没有找到人物</h3><p>试试姓名片段，或清空国家、身份与海域筛选。</p></div>`;
      characterEls.detail.innerHTML = `<div class="roster-empty"><h3>档案暂空</h3><p>没有符合当前条件的人物。</p></div>`;
      return;
    }
    if (!rows.some(item => item.id === selectedCharacterId)) selectedCharacterId = rows[0].id;
    characterEls.list.innerHTML = rows.map(item => `
      <button class="person-row" type="button" data-character-id="${item.id}" aria-current="${item.id === selectedCharacterId}">
        <img src="${item.portrait}" alt="${escapeHTML(item.name)}的 ROM 头像" width="40" height="48">
        <span><span class="person-name">${escapeHTML(item.name)}</span><span class="person-meta">${escapeHTML(item.country)} · ${escapeHTML(item.identity)} · ID ${item.id}</span></span>
        <span class="person-port">${escapeHTML(item.initialPort)}<br>${escapeHTML(item.initialRegion)}</span>
        <span class="person-levels">航 ${item.navigationLevel}<br>战 ${item.combatLevel}</span>
      </button>`).join('');
    characterEls.list.querySelectorAll('[data-character-id]').forEach(button => button.addEventListener('click', () => {
      selectedCharacterId = Number(button.dataset.characterId);
      renderCharacterList();
    }));
    renderCharacterDetail(DATA.characters[selectedCharacterId]);
  }

  function renderCharacterDetail(item) {
    const attributes = Object.entries(item.attributes).map(([name, value]) => `
      <div class="attribute"><span>${name}</span><span class="attribute-bar"><i style="width:${Math.min(100, value)}%"></i></span><b>${value}</b></div>`).join('');
    const skills = item.skills.length ? item.skills.map(skill => `<span class="skill">${skill}</span>`).join('') : '<span class="subtle" style="color:#66736d">无记录技能</span>';
    const fleetEvidence = item.fleet
      ? `舰队 #${item.fleet.id} · 舰长 ID ${item.fleet.captainId} · 类型 ${item.fleet.type} · 阵营位 ${item.fleet.faction}`
      : `状态 0x${item.statusByte.toString(16).toUpperCase().padStart(2, '0')} · 地点 ${item.locationByte}`;
    characterEls.detail.innerHTML = `
      <div class="dossier-banner">
        <div class="portrait-plate"><img src="${item.portrait}" alt="${escapeHTML(item.name)}的 ROM 原生头像"><span>PORTRAIT ${item.portraitId}</span></div>
        <div class="dossier-title">
          <div class="dossier-kicker">CAPTAIN DOSSIER · NO. ${String(item.id).padStart(3, '0')}</div>
          <h2>${escapeHTML(item.name)}</h2>
          <div class="identity-line"><span class="tag country">${escapeHTML(item.country)}</span><span class="tag">${escapeHTML(item.identity)}</span></div>
          ${item.nameNote ? `<p class="name-warning">※ ${escapeHTML(item.nameNote)}</p>` : ''}
        </div>
      </div>
      <div class="sea-legend"><div><small>初始活动海域 · STATIC ESTIMATE</small><strong>${escapeHTML(item.initialRegion)}</strong></div><div class="port">${escapeHTML(item.initialPort)}</div></div>
      <div class="levels-strip">
        <div class="level-cell"><span>航海等级</span><strong>${item.navigationLevel}</strong></div>
        <div class="level-cell"><span>战斗等级</span><strong>${item.combatLevel}</strong></div>
        <div class="level-cell"><span>年龄</span><strong>${item.age}</strong></div>
        <div class="level-cell"><span>忠诚</span><strong>${item.loyalty}</strong></div>
      </div>
      <section class="dossier-section"><h3>能力矩阵</h3><div class="attribute-grid">${attributes}</div></section>
      <section class="dossier-section"><h3>技能</h3><div class="skill-line">${skills}</div></section>
      <section class="dossier-section"><h3>ROM 依据</h3><div class="audit-grid">
        <div>人物 ID<strong>${item.id}</strong></div><div>头像 ID<strong>${item.portraitId}${item.portraitRaw !== item.portraitId ? `（原始字 0x${item.portraitRaw.toString(16).toUpperCase()}）` : ''}</strong></div>
        <div>初始舰队 / 状态<strong>${escapeHTML(fleetEvidence)}</strong></div><div>地点依据<strong>${escapeHTML(item.locationBasis)}</strong></div>
      </div></section>`;
  }

  const itemEls = {
    search: $('item-search'), category: $('item-category'), availability: $('item-availability'),
    list: $('item-list'), detail: $('item-detail'), status: $('item-status')
  };
  let selectedItemId = 0x97;

  function populateItemFilters() {
    const filters = [
      [itemEls.category, uniqueSorted(DATA.items.map(x => x.category))],
      [itemEls.availability, uniqueSorted(DATA.items.flatMap(x => x.availability))]
    ];
    for (const [select, values] of filters) {
      select.insertAdjacentHTML('beforeend', values.map(value => `<option value="${escapeHTML(value)}">${escapeHTML(value)}</option>`).join(''));
    }
  }

  function filteredItems() {
    const query = itemEls.search.value.trim().toLocaleLowerCase('zh-CN');
    const rows = DATA.items.filter(item => {
      const searchable = [
        item.name, ...(item.aliases || []), item.id, item.idHex, item.category,
        ...item.normalPorts, ...item.hiddenPorts, ...item.specialAcquisition,
        ...item.availability, item.effect
      ].join(' ').toLocaleLowerCase('zh-CN');
      return (!query || searchable.includes(query)) &&
        (!itemEls.category.value || item.category === itemEls.category.value) &&
        (!itemEls.availability.value || item.availability.includes(itemEls.availability.value));
    });
    if (!query) return rows;
    const rank = item => {
      const name = item.name.toLocaleLowerCase('zh-CN');
      const aliases = (item.aliases || []).map(value => value.toLocaleLowerCase('zh-CN'));
      const ports = [...item.normalPorts, ...item.hiddenPorts].map(value => value.toLocaleLowerCase('zh-CN'));
      if (name === query) return 0;
      if (aliases.includes(query)) return 1;
      if (item.idHex.toLocaleLowerCase('zh-CN') === query || String(item.id) === query) return 2;
      if (name.includes(query)) return 3;
      if (aliases.some(value => value.includes(query))) return 4;
      if (ports.includes(query)) return 5;
      if (ports.some(value => value.includes(query))) return 6;
      return 7;
    };
    return rows.sort((a, b) => rank(a) - rank(b) || a.id - b.id);
  }

  function itemPrice(item) {
    if (item.priceNote) return item.priceNote;
    return item.price === null ? '无固定商店' : `${money(item.price)} 金`;
  }

  function itemPlaces(item) {
    if (item.normalPorts.length) return item.normalPorts.slice(0, 2).join('、') + (item.normalPorts.length > 2 ? ` 等${item.normalPorts.length}港` : '');
    if (item.hiddenPorts.length) return `${item.hiddenPorts.slice(0, 2).join('、')} · 隐藏`;
    if (item.specialAcquisition.length) return item.specialAcquisition[0];
    return '未发现固定获取地';
  }

  function renderItemList() {
    const rows = filteredItems();
    itemEls.status.textContent = rows.length ? `找到 ${rows.length} / ${DATA.items.length} 项` : '没有匹配道具';
    if (!rows.length) {
      itemEls.list.innerHTML = `<div class="roster-empty"><div class="empty-mark">物</div><h3>没有找到道具</h3><p>试试名称片段、十六进制 ID、港口，或清空筛选。</p></div>`;
      itemEls.detail.innerHTML = `<div class="roster-empty"><h3>图鉴暂空</h3><p>没有符合当前条件的道具。</p></div>`;
      return;
    }
    if (!rows.some(item => item.id === selectedItemId)) selectedItemId = rows[0].id;
    itemEls.list.innerHTML = rows.map(item => `
      <button class="item-row" type="button" data-item-id="${item.id}" aria-current="${item.id === selectedItemId}">
        <span class="item-mark">${escapeHTML(item.name.slice(0, 1))}</span>
        <span><span class="item-name">${escapeHTML(item.name)}</span><span class="item-meta">${item.idHex} · ${escapeHTML(item.category)}</span></span>
        <span class="item-place">${escapeHTML(itemPlaces(item))}</span>
        <span class="item-price">${escapeHTML(itemPrice(item))}</span>
      </button>`).join('');
    itemEls.list.querySelectorAll('[data-item-id]').forEach(button => button.addEventListener('click', () => {
      selectedItemId = Number(button.dataset.itemId);
      renderItemList();
    }));
    renderItemDetail(DATA.items.find(item => item.id === selectedItemId));
  }

  function portTags(ports, extraClass = '') {
    return ports.length
      ? ports.map(port => `<span class="port-tag ${extraClass}">${escapeHTML(port)}</span>`).join('')
      : '<span class="subtle" style="color:#66736d">无</span>';
  }

  function renderItemDetail(item) {
    const combatStat = item.attack ? `攻击 ${item.attack}` : item.defense ? `防御 ${item.defense}` : item.giftValue ? `赠礼 ${item.giftValue}` : '—';
    const special = item.specialAcquisition.length
      ? `<div class="port-group"><b>特殊 / 条件获取</b><div class="port-tags">${portTags(item.specialAcquisition, 'hidden')}</div></div>` : '';
    const hiddenRule = item.hiddenRule
      ? `<div class="port-group"><b>隐藏商店条件</b><div class="evidence-card">${escapeHTML(item.hiddenRule)}</div></div>` : '';
    itemEls.detail.innerHTML = `
      <div class="item-banner">
        <div class="item-emblem"><span>${escapeHTML(item.name.slice(0, 1))}</span></div>
        <div class="item-title">
          <div class="dossier-kicker">ITEM CATALOGUE · ${item.idHex}</div>
          <h2>${escapeHTML(item.name)}</h2>
          <div class="identity-line"><span class="tag country">${escapeHTML(item.category)}</span>${item.availability.map(value => `<span class="tag">${escapeHTML(value)}</span>`).join('')}</div>
        </div>
      </div>
      <div class="item-stats">
        <div class="item-stat"><span>商店标价</span><strong>${escapeHTML(itemPrice(item))}</strong></div>
        <div class="item-stat"><span>装备 / 赠礼值</span><strong>${combatStat}</strong></div>
        <div class="item-stat"><span>运行时类型</span><strong>${item.runtimeTypeHex}</strong></div>
        <div class="item-stat"><span>运行时数值</span><strong>${item.runtimeValue}</strong></div>
      </div>
      <section class="item-section"><h3>代码确认效果</h3><div class="effect-card">${escapeHTML(item.effect)}</div></section>
      <section class="item-section"><h3>获取位置</h3>
        <div class="port-group"><b>普通商店</b><div class="port-tags">${portTags(item.normalPorts)}</div></div>
        <div class="port-group"><b>凌晨隐藏商店</b><div class="port-tags">${portTags(item.hiddenPorts, 'hidden')}</div></div>
        ${special}${hiddenRule}
      </section>
      <section class="item-section"><h3>ROM 依据</h3><div class="evidence-card">道具 ID ${item.id}（${item.idHex}） · 类型 ${item.runtimeTypeHex} · 数值 ${item.runtimeValue}<br>${escapeHTML(item.evidence)}</div></section>`;
  }

  document.querySelectorAll('.nav-tab').forEach(tab => tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(item => item.setAttribute('aria-selected', String(item === tab)));
    document.querySelectorAll('.page-panel').forEach(panel => { panel.hidden = panel.id !== tab.dataset.page; });
    if (tab.dataset.page === 'character-page') renderCharacterList();
    if (tab.dataset.page === 'item-page') renderItemList();
  }));
  [characterEls.search, characterEls.country, characterEls.identity, characterEls.region].forEach(input => {
    input.addEventListener(input === characterEls.search ? 'input' : 'change', renderCharacterList);
  });
  $('character-reset').addEventListener('click', () => {
    characterEls.search.value = characterEls.country.value = characterEls.identity.value = characterEls.region.value = '';
    selectedCharacterId = 22;
    renderCharacterList();
    characterEls.search.focus();
  });
  document.querySelectorAll('.person-example').forEach(button => button.addEventListener('click', () => {
    characterEls.search.value = button.dataset.name;
    characterEls.country.value = characterEls.identity.value = characterEls.region.value = '';
    renderCharacterList();
  }));
  itemEls.search.addEventListener('input', () => {
    const rows = filteredItems();
    if (rows.length) selectedItemId = rows[0].id;
    renderItemList();
  });
  [itemEls.category, itemEls.availability].forEach(input => input.addEventListener('change', renderItemList));
  $('item-reset').addEventListener('click', () => {
    itemEls.search.value = itemEls.category.value = itemEls.availability.value = '';
    selectedItemId = 0x97;
    renderItemList();
    itemEls.search.focus();
  });
  document.querySelectorAll('.item-example').forEach(button => button.addEventListener('click', () => {
    itemEls.search.value = button.dataset.query;
    itemEls.category.value = itemEls.availability.value = '';
    renderItemList();
  }));
  populateCharacterFilters();
  renderCharacterList();
  populateItemFilters();
  renderItemList();
  </script>
</body>
</html>
'''


def main() -> None:
    subprocess.run(
        [sys.executable, str(CHARACTER_SCRIPT), "--portrait-dir", str(PORTRAIT_DIR)],
        check=True,
    )
    subprocess.run([sys.executable, str(ITEM_SCRIPT)], check=True)
    data = load_data()
    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUT_PATH.write_text(TEMPLATE.replace("__DATA__", compact), encoding="utf-8")
    print(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size:,} bytes)")
    print(f"ports={len(data['ports'])} goods={len(data['goods'])} cells={len(data['ports']) * len(data['goods'])}")
    print(f"characters={len(data['characters'])} portraits={len(list(PORTRAIT_DIR.glob('*.png')))} verified_idle=66")
    print(f"items={len(data['items'])} weapons=34 armor=16")


if __name__ == "__main__":
    main()
