#!/usr/bin/env python3
"""Extrae el "Guild History" de perfiles de albiondb.net/player.

Uso:
    pip install playwright && playwright install chromium
    python scrape_guild_history.py urls.txt salida.csv

urls.txt: una URL de perfil por línea (o un nombre de jugador si pasas --base).
SIN PROBAR contra la web real: los selectores pueden necesitar ajuste.
Usa --debug para guardar el HTML de cada perfil y ajustar.
"""
import argparse
import csv
import sys
import time

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# JS que localiza el encabezado "Guild History" y devuelve las filas que le siguen.
EXTRACT_JS = """
() => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const head = [...document.querySelectorAll('h1,h2,h3,h4,h5,div,span,p,th')]
    .find(e => /^guild history$/i.test(norm(e.textContent)));
  if (!head) return null;
  // Sube hasta un contenedor que tenga una tabla o lista.
  let box = head;
  for (let i = 0; i < 5 && box; i++, box = box.parentElement) {
    const rows = box.querySelectorAll('tr, li');
    if (rows.length) {
      return [...rows].map(r =>
        [...r.querySelectorAll('td,th,span,a')].length
          ? [...r.querySelectorAll('td,th')].map(c => norm(c.textContent))
          : [norm(r.textContent)]
      ).map(cells => cells.length ? cells : [norm(r.textContent)]);
    }
  }
  return [];
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("salida")
    ap.add_argument("--base", default="", help="prefijo si el archivo trae solo nombres/IDs")
    ap.add_argument("--delay", type=float, default=2.0, help="segundos entre perfiles")
    ap.add_argument("--debug", action="store_true", help="guarda HTML de cada perfil")
    a = ap.parse_args()

    targets = [l.strip() for l in open(a.entrada, encoding="utf-8") if l.strip()]
    with sync_playwright() as p, open(a.salida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["jugador", "fila"])
        browser = p.chromium.launch()
        page = browser.new_page()
        for i, t in enumerate(targets, 1):
            url = t if t.startswith("http") else a.base + t
            try:
                page.goto(url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(1500)
                rows = page.evaluate(EXTRACT_JS)
                if a.debug:
                    open(f"debug_{i}.html", "w", encoding="utf-8").write(page.content())
                if not rows:
                    w.writerow([t, "SIN_DATOS"])
                    print(f"[{i}/{len(targets)}] {t}: sin datos", file=sys.stderr)
                else:
                    for r in rows:
                        w.writerow([t] + r)
                    print(f"[{i}/{len(targets)}] {t}: {len(rows)} filas", file=sys.stderr)
            except PWTimeout:
                w.writerow([t, "TIMEOUT"])
                print(f"[{i}/{len(targets)}] {t}: timeout", file=sys.stderr)
            f.flush()
            time.sleep(a.delay)
        browser.close()


if __name__ == "__main__":
    main()
