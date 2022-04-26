TESTFINDER = nose2

tests: tests.py
		$(TESTFINDER) --with-coverage