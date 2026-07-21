# AAAI-27 format audit

Audit date: 2026-07-21.  Scope: the anonymous review manuscript in
`paper/main.tex` and `paper/main.pdf`.

## Verified against the 2027 author kit

- Uses `\documentclass[letterpaper]{article}` and
  `\usepackage[submission]{aaai2027}` from the bundled AAAI-27 author kit.
- Uses `aaai2027.bst`; the source compiles with PDFLaTeX and BibTeX.
- Anonymous title block is `Anonymous Submission` with empty affiliations.
- The submission option suppresses the camera-ready copyright footer.
- The generated PDF is US Letter (612 x 792 pt), two-column, and currently six
  pages including references.
- No `hyperref`, page-number, header/footer, `geometry`, `titlesec`, manual page
  break, or non-AAAI font package is loaded by the manuscript.
- References flow directly after the conclusion.

## Items to resolve before submission

- Resolved on 2026-07-18: local `\tabcolsep` adjustments and the negative
  `\vspace` were removed.  Column widths were corrected without manual spacing;
  the recompiled manuscript has no overfull boxes.
- The present PDF passes the font audit: every font is embedded, all are Type 1,
  and the file is PDF 1.5 and unencrypted.  Repeat this audit on the final PDF,
  including absence of bookmarks/embedded links and cleared identifying metadata.
- The AAAI-27 event page currently links the author kit and gives the main-track
  deadline, but the retrieved page does not itself state a page limit or the
  disposition of the reproducibility checklist.  Do not silently inherit these
  details from AAAI-26.  Recheck the AAAI-27 submission instructions immediately
  before submission and include/submit the checklist exactly as directed.
- Keep technical content within the event-specific limit once confirmatory
  results are inserted; references and any checklist must follow the exact
  AAAI-27 event instructions.
- Keep acknowledgements absent during anonymous review.  Audit repository URLs,
  supplementary files, PDF metadata, self-citations, and model/output paths for
  identity leakage.
- Human annotation and sealing language is now synchronized with the v3.1 seal.
  Replace the explicitly pending confirmatory language and development-only
  performance tables only after the authorized preregistered evaluation.
  Formatting compliance does not make the current six-page manuscript
  scientifically complete.

## Authoritative sources

- AAAI-27 event page and author-kit link:
  https://aaai.org/conference/aaai/aaai-27/
- Bundled anonymous instructions:
  `paper/AuthorKit27/AnonymousSubmission2027.tex`
- Bundled style and bibliography files:
  `paper/AuthorKit27/aaai2027.sty` and
  `paper/AuthorKit27/aaai2027.bst`

The AAAI-26 submission page was consulted only as historical context.  Its
seven-page technical-content limit and checklist procedure are not treated here
as authoritative AAAI-27 requirements unless AAAI-27 publishes the same rules.
