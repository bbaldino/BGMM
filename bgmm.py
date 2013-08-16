import os, sys, logging, errno
# Root path
base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local libs dir into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

import file_watcher as fw
from gmusicapi import Musicmanager
import string
from bottle.bottle import route, request, post, run, redirect, static_file
import json
import sqlite3 as sql

mm = Musicmanager()
logger = logging.getLogger("bgmm")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("/tmp/gmu.log")
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

# ----- Web -------
main_page_template = '''
<head>
    <link href="/static/theme.css" rel="stylesheet">
</head>
<div class="navbar">
    <div class="navbar-inner">
        <div class="container">
            <a class="brand" href="/main">BGMM</a>
            <div class="nav-collapse">
                <ul class="nav">
                    <li><a href="/main">Home</a></li>
                    <li><a href="/config">Config</a></li>
                    <li><a href="/logs">Logs</a></li>
                    <li><a href="/status">Status</a></li>
                </ul>
                <ul class="nav pull-right">
                    {0}
                </ul>
            </div> <!-- nav-collapse -->
        </div> <!-- container -->
    </div> <!-- navbar-inner -->
</div> <!-- navbar -->
<div class="content">
    {1}
</div>
<footer id="footer">    
    bgmm version: .1<br/>    
</footer>
'''

def generate_main_page(content):
    global logged_in
    if logged_in:
        login_status_str = "<li>logged in</li><li><a href=\"/logout\">(logout)</a></li>"
    else:
        login_status_str = "<li>Not logged in</li><li><a href=\"/\">(login)</a></li>"
    return main_page_template.format(login_status_str, content)

@route('/')
def root():
    global logged_in
    logger.debug("Logging in!")
    if not mm.login(os.path.join(OAUTH_PATH, OAUTH_FILE)):
        oauth_uri = mm.get_oauth_uri()
        return generate_main_page(("Need to perform oauth, please visit <a href=\"%s\">this url</a> and paste the key you receive here: \
                  <form method=\"POST\" action=\"/submit_oauth_key\"> \
                    <input name=\"oauth_key\" type=\"text\"/> \
                    <input type=\"submit\" /> \
                  </form>" % oauth_uri))
    else:
        logger.debug("Logged in!")
        logged_in = True
        redirect("/main")

@post('/submit_oauth_key')
def oauth_submit():
    oauth_key = request.forms.get('oauth_key')
    if not make_sure_path_exists(OAUTH_PATH):
        logger.error("Error creating oauth cred path: %s" % OAUTH_PATH)
        return
    try:
        mm.set_oauth_code(oauth_key, os.path.join(OAUTH_PATH, OAUTH_FILE))
    except Exception as e:
        return "Error with login: %s" % e
    else:
        if not mm.login(os.path.join(OAUTH_PATH, OAUTH_FILE)):
            return "Error with login, incorrect code?"
        else:
            global logged_in
            logged_in = True
            redirect("/main")

@route('/main')
def main():
    return generate_main_page("Welcome!")

@route('/logout')
def logout():
    mm.logout()
    os.remove(os.path.join(OAUTH_PATH, OAUTH_FILE))
    global logged_in
    logged_in = False
    redirect("/")

@route('/config')
def config():
    watched_paths = fw.get_watched_paths()
    content_str = '''
    <div class="row">
        <div class="span6 offset1">
            <form class="form-horizontal well" name="watchpath_add" method="POST" action="/add_watch_path">
                <div class="control-group">
                    <label class="control-label" for="path">Add a new path:</label>
                    <input type="hidden" name="curr_page" value="/config">
                    <input id="path" class="input-large" name="path" type="text">
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Add Path</button>
                    <button type="reset" class="btn">Cancel</button>
                </div>
            </form>
            <form class="form-horizontal well" name="watchpath_remove" method="POST" action="/remove_watch_path">
                <div class="control-group">
                    <label class="control-label" for "watchpaths">Watched Paths</label>
                    <input type="hidden" name="curr_page" value="/config">
                    <select id="watchpaths" name="watchpaths" multiple="multiple">
                        %s
                    </select>
                </div>
                <div class="form-actions">
                    <button class="btn btn-primary" type="submit">Remove Path</button> 
                </div>
            </form>
        </div>
    </div>
'''
    paths_str = ""
    for path in watched_paths.keys():
        paths_str += "<option value=\"%s\">%s</option>" % (path, path)
    content_str = content_str % paths_str

    return generate_main_page(content_str)

@route('/status')
def status():
    songs = get_all_songs()
    html = '''
    <div class="row">
        <div class="offset1">
            <a href="/scan">Scan existing files</a>
            <a href="/upload">Upload scanned files</a>
        </div>
    </div>
    <div class="row">
        <div class="offset1">
            <table class='table table-bordered table-striped table-hover'>
                <thead>
                    <tr>
                        <th>Path</th>
                        <th>Status</th>
                        <th>Id<th>
                    </tr>
                <thead>
                <tbody>
    '''
    for song_path, song_info in songs.iteritems():
        html = html + "<tr><td>" + song_path + "</td><td>" + song_info['status'] + "</td><td>" + song_info['id'] + "</td></tr>"
    html += "</tbody></table></div></div>"
    return generate_main_page(html)


@route('/logs')
def logs():
    with open("/tmp/gmu.log", "r") as f:
        log_lines_desc = f.readlines()
        log_lines_desc.reverse()
        html = '''
        <div class="row">
            <div class="offset1">
                <table class='table table-bordered table-striped table-hover'>
                    <tbody>
        '''
        for log_line in log_lines_desc:
            html = html + "<tr><td>" + log_line + "</td></tr>"
        html += "</tbody></table></div></div>"
        return generate_main_page(html)

@route('/scan')
def scan():
    scan_existing_files(fw.get_watched_paths().keys())
    redirect('/status')

@route('/upload')
def upload_scanned():
    songs = get_all_songs()
    for song_path in songs.keys():
        if songs[song_path]["status"] == STATUS_SCANNED:
            logger.debug("Uploading song %s" % song_path)
            upload(song_path)
    redirect('/status')

@post('/remove_watch_path')
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
