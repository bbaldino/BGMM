import os, sys
# Root path
base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local libs dir into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

import user
import unittest
from contextlib import contextmanager

TEST_EMAIL = "test@test.com"
TEST_APP_DATA_DIR = "/tmp/appdata/"


class FakeSql:
    connect_path = None
    execute_statement = None

    @staticmethod
    def connect(path):
        FakeSql.connect_path = path
        return FakeSql()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def cursor(self):
        return self

    def execute(self, statement):
        FakeSql.execute_statement = statement
        return self

class FakeMusicManager:
    create_count = 0
    login_count = 0
    logout_count = 0
    def __init__(self):
        FakeMusicManager.create_count += 1
    
    def login(self, credentials):
        FakeMusicManager.login_count += 1
        return True

    def logout(self):
        FakeMusicManager.logout_count += 1
        pass

class FakeFileWatcher:
    create_count = 0
    email = None
    finished_writing_callback = None
    watched_paths = None
    stop_watching_count = 0
    def __init__(self, email, finished_writing_callback, watched_paths):
        FakeFileWatcher.create_count += 1
        FakeFileWatcher.email = email
        FakeFileWatcher.finished_writing_callback = finished_writing_callback
        FakeFileWatcher.watched_paths = watched_paths

    def stop_watching(self):
        FakeFileWatcher.stop_watching_count += 1

class TestUser(unittest.TestCase):
    def setUp(self):
        user.sql = FakeSql
        user.Musicmanager = FakeMusicManager
        user.FileWatcher = FakeFileWatcher

        self.user = user.User(TEST_EMAIL, TEST_APP_DATA_DIR)

    def testInit(self):
        self.user.init(None)
        # Check database initialization
        self.assertEqual(os.path.join(TEST_APP_DATA_DIR, TEST_EMAIL, user.DB_NAME), FakeSql.connect_path)
        self.assertEqual("CREATE TABLE IF NOT EXISTS songs(path TEXT PRIMARY KEY, id TEXT, status TEXT)", FakeSql.execute_statement)

        # Check that we made an instance of each class
        self.assertEqual(FakeMusicManager.create_count, 1)
        self.assertEqual(FakeMusicManager.login_count, 1)

        self.assertEqual(FakeFileWatcher.create_count, 1)
        self.assertEqual(FakeFileWatcher.email, TEST_EMAIL)
        self.assertEqual(FakeFileWatcher.finished_writing_callback, self.user._finished_writing_callback)
        self.assertEqual(FakeFileWatcher.watched_paths, [])

    def testInitWithPreviouslyWatchedPaths(self):
        pass

    def testLogout(self):
        self.user.init(None)
        self.user.logout()

        self.assertEqual(FakeMusicManager.logout_count, 1)
        self.assertEqual(FakeFileWatcher.stop_watching_count, 1)

    def test_get_watched_paths(self):
        pass

    def test_add_watch_path(self):
        pass

    def test_remove_watch_path(self):
        pass

    def test_scan_existing_files(self):
        pass

    def test_upload_scanned(self):
        pass

    def test_upload(self):
        pass

    def test_get_all_songs(self):
        pass



if __name__ == "__main__":
    unittest.main()
