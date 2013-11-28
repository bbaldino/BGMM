import os, logging, json
import sqlite3 as sql

from gmusicapi import Musicmanager
from file_watcher import FileWatcher
import util

CFG_FILE_NAME = "user_config.cfg"
DB_NAME = "bgmm.db"

logger = logging.getLogger("bgmm")
logger.setLevel(logging.DEBUG)

class FileStatus:
    Scanned = "SCANNED"
    Uploaded = "UPLOADED"


class User:
    def __init__(self, email, app_data_dir):
        self.email = email
        self.app_data_dir = app_data_dir

    def init(self, oauth_credentials):
        # Initialize the database
        logger.info("%s: Initializing database" % self.email)
        self._data_init()
        # Create the Musicmanager
        logger.info("%s: Logging in to Google music" % self.email)
        self.mm = Musicmanager()
        if not self.mm.login(oauth_credentials):
            logger.info("%s: Error logging in to Google music" % self.email)
            return False
        # Check if we already have any watch paths configured
        config = self._read_config()
        watched_paths = config["watched_paths"] if "watched_paths" in config else []
        logger.info("%s: Found previously watched paths %s" % (self.email, watched_paths))
        # Create the FileWatcher
        logger.info("%s: Creating the FileWatcher" % (self.email))
        self.fw = FileWatcher(self.email, self._finished_writing_callback, watched_paths)
        return True

    def logout(self):
        self.mm.logout()
        self.fw.stop_watching()

    def _read_config(self):
        return util.read_config(os.path.join(self.app_data_dir, self.email, CFG_FILE_NAME))

    def _write_config(self, config):
        util.write_config(config, os.path.join(self.app_data_dir, self.email, CFG_FILE_NAME))

    def get_watched_paths(self):
        logger.debug("reading config from %s" % os.path.join(self.app_data_dir, self.email))
        config = self._read_config()
        logger.debug("read config: %s" % config)
        return config["watched_paths"] if "watched_paths" in config else []

    def add_watch_path(self, path):
        # Add to file watcher
        self.fw.watch(path)
        # Add to the config
        config = self._read_config()
        if "watched_paths" not in config:
            config["watched_paths"] = [path]
        else:
            config["watched_paths"].append(path)
        self._write_config(config)

    def remove_watch_path(self, path):
        # Remove from the file watcher
        self.fw.remove_watch(path)
        # Remove from the config
        config = self._read_config()
        if "watched_paths" in config:
            config["watched_paths"].remove(path)
        else:
            logger.info("%s trying to remove watch path %s that we weren't watching" % (self.email, path))
        self._write_config(config)

    def scan_existing_files(self):
        watched_paths = self.get_watched_paths()
        logger.debug("%s Scanning existing files in these directories: %s" % (self.email, watched_paths))
        for watched_path in watched_paths:
            logger.debug("Scanning existing files in %s" % watched_path)
            for root, subFolders, files in os.walk(watched_path):
                logger.debug("root: %s, subfolders: %s, files: %s" % (root, subFolders, files))
                for file in files:
                    filename, fileExtension = os.path.splitext(file)
                    logger.debug("looking at file %s, filename = %s, file extension = %s" % (file, filename, fileExtension))
                    if fileExtension == ".mp3":
                        logger.debug("Found file %s" % file);
                        self._update_path(os.path.join(root, file), FileStatus.Scanned)
        logger.debug("scanning finished");

    def upload_scanned(self):
        songs = self.get_all_songs() 
        for song_path in songs.keys():
            if songs[song_path]["status"] == FileStatus.Scanned:
                logger.debug("Uploading song %s" % song_path)
                self.upload(song_path)
        return


    def _data_init(self):
        con = sql.connect(os.path.join(self.app_data_dir, DB_NAME))
        with con:
            cur = con.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS songs(
                            path TEXT PRIMARY KEY,
                            id TEXT,
                            status TEXT)''')

    def _update_path(self, path, status, id=None):
        logger.info("Updating path %s with id %s and status %s" % (path, id, status))
        info = ((path,
                 "" if not id else id,
                 status)
                )

        con = sql.connect(os.path.join(self.app_data_dir, DB_NAME))
        with con:
            cur = con.cursor()
            cur.execute('''REPLACE INTO songs VALUES(?, ?, ?)''', info)

    def _finished_writing_callback(new_file_path):
        logger.debug("New file %s" % new_file_path)
        filename, file_extension = os.path.splitext(new_file_path)
        if file_extension != ".mp3":
            logger.debug("Skipping non-mp3 file")
            return
        logger.info("Uploading new file: %s" % new_file_path)
        self._update_path(new_file_path, FileStatus.Scanned)
        self.upload(new_file_path)

    def upload(self, file_path):
        uploaded, matched, not_uploaded = self.mm.upload(file_path, enable_matching=False) # async me!
        if uploaded:
            logger.info("Uploaded song %s with ID %s" % (file_path, uploaded[file_path]))
            self._update_path(file_path, FileStatus.Uploaded, uploaded[file_path])
        if matched:
            logger.info("Matched song %s with ID %s" % (file_path, matched[file_path]))
            self._update_path(file_path, FileStatus.Uploaded, uploaded[file_path])
        if not_uploaded:
            reason_string = not_uploaded[file_path]
            if "ALREADY_EXISTS" in reason_string:
                song_id = reason_string[reason_string.find("(") + 1 : reason_string.find(")")]
                logger.info("Song already exists with ID %s, updating database" % song_id)
                # The song ID is located within parentheses in the reason string
                self._update_path(file_path, FileStatus.Uploaded, song_id)
            else:
                logger.info("Unable to upload song %s because %s" % (file_path, reason_string))

    def get_all_songs(self):
        songs = {}
        con = sql.connect(os.path.join(self.app_data_dir, DB_NAME))
        with con:
            cur = con.cursor()
            for row in cur.execute('''SELECT * FROM songs'''):
                song_path = row[0]
                song_id = row[1]
                song_status = row[2]
                songs[song_path] = {'id': song_id,
                                    'status': song_status}

        return songs
