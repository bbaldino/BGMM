import os, sys, logging, errno
# Root path
base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local libs dir into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

import file_watcher as fw
from gmusicapi import Musicmanager
import string
from oauth2client.client import OAuth2WebServerFlow
from bottle import bottle
from bottle.bottle import route, request, post, run, redirect, static_file, template
import json
import sqlite3 as sql

bottle.TEMPLATE_PATH.insert(0,'/boot/config/plugins/bgmm/bgmm/views')
mm = Musicmanager()
LOG_LOCATION = "/tmp/bgmm.log"
logger = logging.getLogger("bgmm")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(LOG_LOCATION)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

OAUTH_PATH="/boot/config/appdata/gmu/"
OAUTH_FILE="oauth.cred"
CONFIG_FILE="/boot/config/plugins/bgmm/bgmm_config.cfg"
DB_FILE="/boot/config/plugins/bgmm/bgmm.db"
config = {}
logged_in = False
STATUS_SCANNED = "SCANNED"
STATUS_UPLOADED = "UPLOADED"
SONGS_PER_PAGE = 10

# ----- Web -------

class Song:
    def __init__(self, path, status, id):
        self.path = path
        self.status = status
        self.id = id

def check_login(fn):
    def check_logged_in(**kwargs):
        if not logged_in:
            oauth_uri = mm.get_oauth_uri()
            return template('login', session_status={"logged_in": logged_in}, oauth_uri=oauth_uri)
        else:
            return fn(**kwargs)
    return check_logged_in

@route('/')
@check_login
def root():
    redirect("/main")

@post('/submit_oauth_key')
def oauth_submit():
    oauth_key = request.forms.get('oauth_key')
    if not make_sure_path_exists(OAUTH_PATH):
        logger.error("Error creating oauth cred path: %s" % OAUTH_PATH)
        return
    try:
        res = mm.set_oauth_code(oauth_key, os.path.join(OAUTH_PATH, OAUTH_FILE))
        logger.error("RES = %s" % res)
    except Exception as e:
        return "Error with login: %s" % e
    else:
        if not mm.login(os.path.join(OAUTH_PATH, OAUTH_FILE)):
            return "Error with login, incorrect code?"
        else:
            global logged_in
            logged_in = True
            redirect("/main")

@route('/auth')
def auth():
    return "Auth callback!"

@route('/main')
@check_login
def main():
    return template('default', content="Welcome!", session_status={"logged_in": logged_in})

@route('/logout')
def logout():
    mm.logout()
    os.remove(os.path.join(OAUTH_PATH, OAUTH_FILE))
    global logged_in
    logged_in = False
    redirect("/")

@route('/config')
@check_login
def config():
    watched_paths = fw.get_watched_paths()
    return template('config', session_status={"logged_in": logged_in}, watched_paths = watched_paths.keys())

@route('/status')
@check_login
def status():
    page = int(request.query.page) if request.query.page else 1
    songs = get_all_songs()
    num_pages = int(len(songs.keys()) / SONGS_PER_PAGE) + 1
    start_song = ((page - 1) * SONGS_PER_PAGE)
    end_song = ((page - 1) * SONGS_PER_PAGE) + SONGS_PER_PAGE
    logger.debug("displaying results for page %s, showing songs %s to %s" % (page, (page * SONGS_PER_PAGE), (page * SONGS_PER_PAGE) + SONGS_PER_PAGE))
    page_songs = []
    for song_path in songs.keys()[start_song : end_song]:
        page_songs.append(Song(song_path, songs[song_path]['status'], songs[song_path]['id']))

    return template('status', session_status={"logged_in": logged_in}, songs=page_songs, num_pages=num_pages, curr_page=page)

@route('/logs')
def logs():
    with open(LOG_LOCATION, "r") as f:
        log_lines_desc = f.readlines()
        log_lines_desc.reverse()
        return template('logs', session_status={"logged_in": logged_in}, log_lines=log_lines_desc)

@route('/scan')
@check_login
def scan():
    scan_existing_files(fw.get_watched_paths().keys())
    redirect('/status')

@route('/upload')
@check_login
def upload_scanned():
    songs = get_all_songs()
    for song_path in songs.keys():
        if songs[song_path]["status"] == STATUS_SCANNED:
            logger.debug("Uploading song %s" % song_path)
            upload(song_path)
    redirect('/status')

@post('/login')
def login():
    username = request.forms.get('username')
    password = request.forms.get('password')
    logger.info("got username %s and password %s " % (username, password))

@post('/remove_watch_path')
@check_login
def remove_watch_path():
    curr_page = request.forms.get('curr_page')
    path_strs = ""
    for path in request.forms.getlist('watchpaths'):
        fw.remove_watch(path)
    global config
    read_config()
    if "watched_paths" in config:
        for path in request.forms.getlist('watchpaths'):
            config["watched_paths"].remove(path)
    write_config(config)
    redirect(curr_page)

@post('/add_watch_path')
@check_login
def add_watch_path():
    path = request.forms.get('path')
    curr_page = request.forms.get('curr_page')
    fw.watch(path, finished_writing_callback)
    read_config()
    global config
    if "watched_paths" not in config:
        config["watched_paths"] = [path]
    else:
        config["watched_paths"].append(path)
    write_config(config)
    redirect(curr_page)

@route('/static/:filename.:ext')
def get_static(filename, ext):
    logger.debug("Getting static file " + filename + " with extension " + ext)
    if ext == "css":
        return static_file(filename + "." + ext, root='/boot/config/plugins/bgmm/bgmm/public/stylesheets')

# ----- End Web -------


def finished_writing_callback(new_file_path):
    logger.debug("New file %s" % new_file_path)
    filename, file_extension = os.path.splitext(new_file_path)
    if file_extension != ".mp3":
        logger.debug("Skipping non-mp3 file")
        return
    logger.info("Uploading new file: %s" % new_file_path)
    update_path(new_file_path, STATUS_SCANNED)
    upload(new_file_path)

def upload(file_path):
    uploaded, matched, not_uploaded = mm.upload(file_path, enable_matching=False) # async me!
    if uploaded:
        logger.info("Uploaded song %s with ID %s" % (file_path, uploaded[file_path]))
        update_path(file_path, STATUS_UPLOADED, uploaded[file_path])
    if matched:
        logger.info("Matched song %s with ID %s" % (file_path, matched[file_path]))
        update_path(file_path, STATUS_UPLOADED, uploaded[file_path])
    if not_uploaded:
        reason_string = not_uploaded[file_path]
        if "ALREADY_EXISTS" in reason_string:
            song_id = reason_string[reason_string.find("(") + 1 : reason_string.find(")")]
            logger.info("Song already exists with ID %s, updating database" % song_id)
            # The song ID is located within parentheses in the reason string
            update_path(file_path, STATUS_UPLOADED, song_id)
        else:
            logger.info("Unable to upload song %s because %s" % (file_path, reason_string))

def scan_existing_files(watched_paths):
    logger.debug("Scanning existing files in these directories: %s" % watched_paths)
    for watched_path in watched_paths:
        logger.debug("Scanning existing files in %s" % watched_path)
        for root, subFolders, files in os.walk(watched_path):
            logger.debug("root: %s, subfolders: %s, files: %s" % (root, subFolders, files))
            for file in files:
                filename, fileExtension = os.path.splitext(file)
                logger.debug("looking at file %s, filename = %s, file extension = %s" % (file, filename, fileExtension))
                if fileExtension == ".mp3":
                    logger.debug("Found file %s" % file);
                    update_path(os.path.join(root, file), STATUS_SCANNED)
    logger.debug("scanning finished");



def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            return False

    return True

# data store

def update_path(path, status, id=None):
    logger.info("Updating path %s with id %s and status %s" % (path, id, status))
    info = ((path,
             "" if not id else id,
             status)
            )

    con = sql.connect(DB_FILE)
    with con:
        cur = con.cursor()
        cur.execute('''REPLACE INTO songs VALUES(?, ?, ?)''', info)

def get_all_songs():
    songs = {}
    con = sql.connect(DB_FILE)
    with con:
        cur = con.cursor()
        for row in cur.execute('''SELECT * FROM songs'''):
            song_path = row[0]
            song_id = row[1]
            song_status = row[2]
            songs[song_path] = {'id': song_id,
                                'status': song_status}

    return songs

# end data store

def data_init():
    logger.debug("Initializing database")
    con = sql.connect(DB_FILE)
    with con:
        cur = con.cursor()

        cur.execute('''CREATE TABLE IF NOT EXISTS songs(
                        path TEXT PRIMARY KEY,
                        id TEXT,
                        status TEXT)''')

def read_config():
    global config
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

def write_config(config):
    with open(CONFIG_FILE, "w+") as f:
        json.dump(config, f)

def main():
    logger.info("Starting google music uploader")
    pidfile = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "--pidfile":
            if len(sys.argv) < 3:
                logger.error("Missing pidfile path")
                return
            pidfile = sys.argv[2]

    if pidfile:
        if not make_sure_path_exists(os.path.dirname(pidfile)):
            logger.warning("Error creating pidfile directory %s" % os.path.dirname(pidfile))
            return
        with open(pidfile, "w+") as f:
            logger.debug("Writing pidfile to %s" % pidfile)
            f.write(str(os.getpid()))
    # Start watching any previously configured paths
    global config
    read_config()
    if "watched_paths" in config:
        for path in config["watched_paths"]:
            logger.info("Watching path %s" % path)
            fw.watch(path, finished_writing_callback)

    # Initialize db if it doesn't exist
    data_init()


    run(host='0.0.0.0', port=config['PORT'], debug=True)


if __name__ == "__main__":
    main()
