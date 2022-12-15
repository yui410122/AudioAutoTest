def pytest_addoption(parser):
    parser.addoption("--apk_path", action="store", default=None)
    parser.addoption("--serialno", action="store", default=None)
    parser.addoption("--skip_version_check", action="store_true")
    parser.addoption("--skip_function_check", action="store_true")
