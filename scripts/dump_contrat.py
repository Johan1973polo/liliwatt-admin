#!/usr/bin/env python3
"""
dump_contrat.py — Outil de reconnaissance PDF pour l'extracteur de contrats.

Usage : python3 scripts/dump_contrat.py chemin/vers/contrat.pdf

Affiche :
  - Le texte brut de chaque page (pages 1-7)
  - Les tableaux détectés par pdfplumber sur la page 3
"""

import sys
import pdfplumber


def separator(label: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {label}")
    print("=" * 70)


def dump_page_text(pdf, page_num: int) -> None:
    """Affiche le texte brut d'une page (1-indexé)."""
    idx = page_num - 1
    if idx >= len(pdf.pages):
        print(f"  [Page {page_num} inexistante — le PDF a {len(pdf.pages)} pages]")
        return
    page = pdf.pages[idx]
    text = page.extract_text() or ""
    separator(f"PAGE {page_num} — texte brut ({len(text)} caractères)")
    if text.strip():
        print(text)
    else:
        print("  [Aucun texte extractible sur cette page]")


def dump_page_tables(pdf, page_num: int) -> None:
    """Affiche les tableaux pdfplumber d'une page (1-indexé)."""
    idx = page_num - 1
    if idx >= len(pdf.pages):
        return
    page = pdf.pages[idx]
    tables = page.extract_tables()
    separator(f"PAGE {page_num} — tableaux pdfplumber ({len(tables)} tableau(x))")
    if not tables:
        print("  [Aucun tableau détecté]")
        return
    for t_idx, table in enumerate(tables):
        print(f"\n  --- Tableau {t_idx + 1} ({len(table)} ligne(s)) ---")
        for row_idx, row in enumerate(table):
            cells = [f"[{c!r}]" if c else "[vide]" for c in row]
            print(f"  L{row_idx:02d}: {' | '.join(cells)}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/dump_contrat.py chemin/vers/contrat.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"\nFichier  : {pdf_path}")
        print(f"Pages    : {total_pages}")

        # Texte brut — pages 1 à 7 (ou moins si PDF plus court)
        pages_to_dump = range(1, min(8, total_pages + 1))
        for p in pages_to_dump:
            dump_page_text(pdf, p)

        # Tableaux — page 3 uniquement
        dump_page_tables(pdf, 3)

        # Tableaux — page 4 (souvent date de fin)
        dump_page_tables(pdf, 4)


if __name__ == "__main__":
    main()
