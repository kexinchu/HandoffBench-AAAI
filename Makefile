PYTHON ?= python
PAPER_DIR := paper
BUILD_DIR := build/reproducibility

.PHONY: submission env-check artifacts test paper checklist pdf-audit

submission: env-check test artifacts paper checklist pdf-audit

env-check:
	$(PYTHON) scripts/check_environment.py

artifacts: env-check
	PYTHONPATH=src $(PYTHON) scripts/build_submission_artifacts.py --output-dir $(BUILD_DIR)

test: env-check
	PYTHONPATH=src $(PYTHON) -m pytest

paper: artifacts
	cd $(PAPER_DIR) && TEXINPUTS=./AuthorKit27: pdflatex -interaction=nonstopmode -halt-on-error main.tex
	cd $(PAPER_DIR) && BSTINPUTS=./AuthorKit27: bibtex main
	cd $(PAPER_DIR) && TEXINPUTS=./AuthorKit27: pdflatex -interaction=nonstopmode -halt-on-error main.tex
	cd $(PAPER_DIR) && TEXINPUTS=./AuthorKit27: pdflatex -interaction=nonstopmode -halt-on-error main.tex

checklist:
	cd $(PAPER_DIR) && TEXINPUTS=./AuthorKit27: pdflatex -jobname=ReproducibilityChecklist_draft -interaction=nonstopmode -halt-on-error checklist_standalone.tex

pdf-audit: paper
	! rg -n "undefined|Overfull|LaTeX Warning" $(PAPER_DIR)/main.log
	pdfinfo $(PAPER_DIR)/main.pdf | rg "Pages|Page size"
