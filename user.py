import sys, os, logging, json
import sqlite3 as sql
import util
import threading
# Root path
base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local libs dir into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

from gmusicapi import Musicmanager
from file_watcher import FileWatcher
import eyed3

CFG_FILE_NAME = "user_config.cfg"
DB_NAME = "bgmm.db"

logger = logging.getLogger("bgmm")
logger.setLevel(logging.DEBUG)

class FileStatus:
    Scanned = "SCANNED"
    Uploaded = "UPLOADED"
    Error = "ERROR"

class User:
    def __init__(self, email, app_data_dir):
        self.email = email
        self.app_data_dir = app_data_dir
        self.db_lock = threading.Lock()

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
            if path not in config["watched_paths"]:
                config["watched_paths"].append(path)
        self._write_config(config)

    def remove_watch_path(self, path):
        # Remove from the file watcher
        self.fw.remove_watch(path)
        # Remove from the config
        config = self._read_config()
        if "watched_paths" in config:
            if path in config["watched_paths"]:
                config["watched_paths"].remove(path)
        else:
            logger.info("%s trying to remove watch path %s that we weren't watching" % (self.email, path))
        self._write_config(config)

    def set_default_action(self, default_action):
        config = self._read_config()
        config["default_action"] = default_action
        self._write_config(config)

    def get_default_action(self):
        config = self._read_config()
        return config.get("default_action", "scan_only")

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
        with self.db_lock:
            con = sql.connect(os.path.join(self.app_data_dir, self.email, DB_NAME))
            with con:
                cur = con.cursor()
                cur.execute('''CREATE TABLE IF NOT EXISTS songs(path TEXT PRIMARY KEY, id TEXT, status TEXT)''')

    def _update_path(self, path, status, id=None, override=False):
        logger.info("Updating path %s with id %s and status %s" % (path, id, status))
        info = ((path,
                 "" if not id else id,
                 status)
                )

        with self.db_lock:
            con = sql.connect(os.path.join(self.app_data_dir, self.email, DB_NAME))
            with con:
                cur = con.cursor()
                if not override:
                    # Check if the song is already in the data store and, if so, what its status is
                    cur.execute('''SELECT status FROM songs WHERE path=(?)''', (path,))
                    res = cur.fetchone()
                    if res:
                        res = res[0]
                        if res == FileStatus.Uploaded:
                            # If it's already been uploaded, don't override that status with something else
                            return
                cur.execute('''REPLACE INTO songs VALUES(?, ?, ?)''', info)

    def _finished_writing_callback(self, new_file_path):
        logger.debug("New file %s" % new_file_path)
        filename, file_extension = os.path.splitext(new_file_path)
        if file_extension != ".mp3":
            logger.debug("Skipping non-mp3 file")
            return
        self._update_path(new_file_path, FileStatus.Scanned)
        if self.get_default_action() == "auto_upload":
            logger.info("Uploading new file: %s" % new_file_path)
            self.upload(new_file_path)

    @staticmethod
    def _find_gmusic_song(scanned_song_tags, gmusic_songs):
        artist = scanned_song_tags.artist.lower()
        album = scanned_song_tags.album.lower()
        title = scanned_song_tags.title.lower()
        logger.debug("Found scanned song %s - %s - %s" % (artist, album, title))
        # Search for an uploaded song that matches
        for gmusic_song in gmusic_songs:
            up_artist = gmusic_song['artist'].lower()
            up_album = gmusic_song['album'].lower()
            up_title = gmusic_song['title'].lower()
            logger.debug("Looking at song %s - %s - %s" % (up_artist, up_album, up_title))
            if artist == up_artist and album == up_album and title == up_title:
                logger.debug("Found match!")
                return gmusic_song
        return None

    def sync_library(self):
        logger.debug("Syncing")
        uploaded_songs = self.mm.get_all_songs()
        scanned_songs = self.get_all_songs()
        logger.debug("found %d scanned songs" % len(scanned_songs))
        # Go through all songs marked 'scanned' and search for a matching that's already been uploaded.
        #  If we find one, grab the id and mark the song as uploaded
        for song_path in scanned_songs.keys():
            # Since we only have the path, scan its tags to get the meta data
            audioFile = eyed3.load(song_path)
            if audioFile and audioFile.tag:
                local_song = scanned_songs[song_path]
                gmusic_song = User._find_gmusic_song(audioFile.tag, uploaded_songs)
                # Now make sure our static is in sync, possibilities:
                # 1) We show it as uploaded but google doesn't -> mark it as 'scanned', remove our id
                # 2) Google shows it as uploaded but we don't -> mark it as 'uploaded', add the id
                # 3) We both show it as uploaded and the ids match -> do nothing
                # 4) Neither of us think it was uploaded -> do nothing
                # 5) Google has it but we don't at all -> TODO!! (option for download?) we'll need to detect this another way (currently searching only by scanned songs)
                if gmusic_song:
                    # Google shows this song
                    if local_song['status'] == FileStatus.Scanned:
                        # Google shows it as uploaded but we don't.  Mark it as uploaded and update the id
                        logger.debug("'%s - %s - %s' was already uploaded, updating its id to %s" % (gmusic_song['artist'], gmusic_song['album'], gmusic_song['title'], gmusic_song['id']))
                        self._update_path(song_path, FileStatus.Uploaded, gmusic_song['id'], override=True)
                    elif local_song['status'] == FileStatus.Uploaded:
                        # We both show it as uploaded, make sure ids match
                        if local_song['id'] != gmusic_song['id']:
                            logger.debug("Ids differ!  Updating to use google's id")
                            self._update_path(song_path, FileStatus.Uploaded, gmusic_song['id'], override=True)
                        else:
                            logger.debug("Ids match! No update needed")
                else:
                    # No matching song on google found
                    if local_song['status'] == FileStatus.Uploaded:
                        logger.debug("We show the song as uploaded but google doesn't, changing status to scanned and clearing id")
                        self._update_path(song_path, FileStatus.Scanned, override=True)
                    else:
                        logger.debug("Neither side thinks it's uploaded, no update needed")
            else:
                logger.debug("Error loading metadata for song %s" % song_path)

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
                self._update_path(file_path, FileStatus.Error, reason_string)

    def get_all_songs(self):
        songs = {}
        with self.db_lock:
            con = sql.connect(os.path.join(self.app_data_dir, self.email, DB_NAME))
            with con:
                cur = con.cursor()
                for row in cur.execute('''SELECT * FROM songs'''):
                    song_path = row[0]
                    song_id = row[1]
                    song_status = row[2]
                    songs[song_path] = {'id': song_id,
                                        'status': song_status}

        return songs
