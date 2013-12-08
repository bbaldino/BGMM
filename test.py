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
TEST_WATCH_PATH = "/tmp/watch"

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

    @staticmethod
    def reset():
        FakeMusicManager.create_count = 0
        FakeMusicManager.login_count = 0
        FakeMusicManager.logout_count = 0

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
    last_watched_path = None
    last_removed_path = None

    @staticmethod
    def reset():
        FakeFileWatcher.create_count = 0
        FakeFileWatcher.email = None
        FakeFileWatcher.finished_writing_callback = None
        FakeFileWatcher.watched_paths = None
        FakeFileWatcher.stop_watching_count = 0
        FakeFileWatcher.last_watched_path = None
        FakeFileWatcher.last_removed_path = None

    def __init__(self, email, finished_writing_callback, watched_paths):
        FakeFileWatcher.create_count += 1
        FakeFileWatcher.email = email
        FakeFileWatcher.finished_writing_callback = finished_writing_callback
        FakeFileWatcher.watched_paths = watched_paths

    def stop_watching(self):
        FakeFileWatcher.stop_watching_count += 1

    def watch(self, path):
        FakeFileWatcher.last_watched_path = path

    def remove_watch(self, path):
        FakeFileWatcher.last_removed_path = path

class FakeUtil:
    config = {}
    @staticmethod
    def reset():
        FakeUtil.config = {}

    @staticmethod
    def read_config(config_file):
        return FakeUtil.config

    @staticmethod
    def write_config(config, config_file):
        FakeUtil.config = config
        pass

class TestUser(unittest.TestCase):
    def setUp(self):
        try:
            os.remove(os.path.join(TEST_APP_DATA_DIR, TEST_EMAIL, user.DB_NAME))
        except:
            pass
        else:
            print("DB file removed")
        try:
            os.remove(os.path.join(TEST_APP_DATA_DIR, TEST_EMAIL, user.CFG_FILE_NAME))
        except:
            pass
        else:
            print("Config file removed")

        user.sql = FakeSql
        FakeMusicManager.reset()
        FakeFileWatcher.reset()
        FakeUtil.reset()
        user.Musicmanager = FakeMusicManager
        user.FileWatcher = FakeFileWatcher
        user.util = FakeUtil

        self.user = user.User(TEST_EMAIL, TEST_APP_DATA_DIR)

    def test_init(self):
        self.assertTrue(self.user.init(None))
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

    def test_init_with_previously_watched_paths(self):
        pass

    def test_init_with_failed_mm_login(self):
        pass

    def test_logout(self):
        self.user.init(None)
        self.user.logout()

        self.assertEqual(FakeMusicManager.logout_count, 1)
        self.assertEqual(FakeFileWatcher.stop_watching_count, 1)

    def test_get_watched_paths(self):
        self.user.init(None)
        self.assertEqual([], self.user.get_watched_paths())
        FakeUtil.config["watched_paths"] = [TEST_WATCH_PATH]
        self.assertEqual([TEST_WATCH_PATH], self.user.get_watched_paths())

    def test_add_watch_path(self):
        self.user.init(None)
        self.user.add_watch_path(TEST_WATCH_PATH)
        # Path should be added to config file and FileWatcher
        self.assertEqual(TEST_WATCH_PATH, FakeFileWatcher.last_watched_path)
        self.assertEqual([TEST_WATCH_PATH], FakeUtil.config["watched_paths"])

    def test_add_duplicate_watch_path(self):
        self.user.init(None)
        self.user.add_watch_path(TEST_WATCH_PATH)
        self.user.add_watch_path(TEST_WATCH_PATH)
        self.assertEqual([TEST_WATCH_PATH], FakeUtil.config["watched_paths"])

    def test_remove_watch_path(self):
        self.user.init(None)
        self.user.add_watch_path(TEST_WATCH_PATH)
        self.user.remove_watch_path(TEST_WATCH_PATH)
        self.assertEqual([], FakeUtil.config["watched_paths"])

    def test_remove_nonexistant_path(self):
        self.user.init(None)
        self.user.add_watch_path(TEST_WATCH_PATH)
        self.user.remove_watch_path("nonexistant")
        self.assertEqual([TEST_WATCH_PATH], FakeUtil.config["watched_paths"])

    def test_scan_existing_files(self):
        #self.user.init(None)
        #FakeUtil.config["watched_paths"] = TEST_WATCH_PATH
        ## Create a dummy mp3
        #os.makedirs(TEST_WATCH_PATH)
        #open(os.path.join(TEST_WATCH_PATH, "x.mp3"), "a+") 
        #self.user.scan_existing_files()
        #print(FakeSql.execute_statement)
        ##self.assertEqual("REPLACE INTO songs VALUES(" + 

    def test_upload_scanned(self):
        pass

    def test_upload(self):
        pass

    def test_get_all_songs(self):
        pass



if __name__ == "__main__":
    unittest.main()
