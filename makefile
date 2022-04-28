TESTFINDER = nose2

tests: tests.py
		$(TESTFINDER) --with-coverage

run app: app.py
		python3 app.py