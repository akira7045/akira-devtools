PYTHON ?= python3
TOOLS := apidiff dupfind envcheck jsonl2csv logsum secretscan

.PHONY: test test-each build wheel

test test-each:
	@fail=0; for t in $(TOOLS); do \
		out=$$(cd $$t && $(PYTHON) test_$$t.py 2>&1); rc=$$?; \
		if echo "$$out" | grep -qE '^Ran [0-9]+ tests?'; then \
			if [ $$rc -eq 0 ] && echo "$$out" | grep -qE '^OK'; then \
				echo "ok   $$t (unittest $$(echo "$$out" | grep -E '^Ran ' | tail -1))"; \
			else \
				echo "FAIL $$t (unittest rc=$$rc)"; echo "$$out" | grep -E '^(FAIL|ERROR|Ran|OK|FAILED)' | tail -5; fail=1; \
			fi; \
		else \
			line=$$(echo "$$out" | grep -E '^[0-9]+/[0-9]+ passed' | tail -1); \
			if [ $$rc -eq 0 ] && echo "$$line" | grep -qE '^([0-9]+)/\1 passed'; then \
				echo "ok   $$t ($$line)"; \
			else \
				echo "FAIL $$t (rc=$$rc)"; echo "$$out" | grep -E '^(FAIL|[0-9]+/[0-9]+ passed|Traceback)' | tail -5; [ -n "$$line" ] && echo "     $$line"; fail=1; \
			fi; \
		fi; \
	done; \
	exit $$fail

build wheel:
	cd python && rm -rf build dist *.egg-info src/*.egg-info && $(PYTHON) -m build --wheel .
	@ls -la python/dist/*.whl
