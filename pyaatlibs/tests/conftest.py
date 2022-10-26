def pytest_addoption(parser):
    parser.addoption("--apk_path", action="store", default=None)
    parser.addoption("--serialno", action="store", default=None)
