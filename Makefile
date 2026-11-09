PYTHON = python3

.PHONY: run analyze visualize clean

run:
	$(PYTHON) analyzer.py

analyze:
	$(PYTHON) analysis.py

visualize:
	$(PYTHON) visualize.py

clean:
	rm -rf __pycache__