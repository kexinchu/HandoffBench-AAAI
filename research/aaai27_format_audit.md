# AAAI-27 format audit

Audit updated: 2026-07-22. Scope: the anonymous review manuscript in
`paper/main.tex` and `paper/main.pdf`.

## Verified against the 2027 author kit

- Uses `\documentclass[letterpaper]{article}` and
  `\usepackage[submission]{aaai2027}` from the bundled AAAI-27 author kit.
- Uses `aaai2027.bst`; the source compiles with PDFLaTeX and BibTeX.
- Anonymous title block is `Anonymous Submission` with empty affiliations.
- The submission option suppresses the camera-ready copyright footer.
- The generated PDF is US Letter (612 x 792 pt), two-column, and currently seven
  pages total; technical content ends and references begin on page 6, and page 7
  contains references only.
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
- The AAAI-27 main-track limit is 7 pages of non-reference content and 9 pages
  total, with pages 8--9 reserved exclusively for references. The current PDF
  is within both limits.
- AAAI-27 requires the completed reproducibility checklist to be uploaded
  separately from the main paper. The repository therefore builds
  `paper/ReproducibilityChecklist_draft.pdf` as a standalone two-page file and
  does not append it to `main.pdf`.
- All code, data, and other material necessary for reproducibility must be
  provided at submission time. A promise to release after acceptance does not
  count. Prepare an anonymized Code and Data Supplement by the July 31, 2026
  supplementary deadline; the main paper deadline is July 28, 2026.
- Keep acknowledgements absent during anonymous review.  Audit repository URLs,
  supplementary files, PDF metadata, self-citations, and model/output paths for
  identity leakage.
- Agent-annotation, execution-lineage, and result language is synchronized with
  the post-seal annotation-provenance correction, v3.1 dataset seal, and v3.4.1
  execution seal. The current seven-page PDF includes both preregistered
  confirmatory results and labels development and secondary estimates
  separately. Formatting compliance does not by itself establish scientific
  completeness; repeat the audit after every substantive paper edit.

## Authoritative sources

- AAAI-27 event page and author-kit link:
  https://aaai.org/conference/aaai/aaai-27/
- AAAI-27 main-track call and explicit 7/9-page rule:
  https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/
- AAAI-27 submission instructions, separate checklist, and reproducibility
  material policy:
  https://aaai.org/conference/aaai/aaai-27/submission-instructions/
- Bundled anonymous instructions:
  `paper/AuthorKit27/AnonymousSubmission2027.tex`
- Bundled style and bibliography files:
  `paper/AuthorKit27/aaai2027.sty` and
  `paper/AuthorKit27/aaai2027.bst`

The audit relies on the event-specific AAAI-27 pages updated in May and June
2026, not an inherited prior-year rule.
