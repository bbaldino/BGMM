import os, sys, logging, json
from collections import namedtuple
from logging.handlers import RotatingFileHandler
import thread


LOG_LOCATION = "/tmp/bgmm.log"
logger = logging.getLogger("bgmm")
logger.setLevel(logging.DEBUG)
fh = RotatingFileHandler(LOG_LOCATION, maxBytes=1048576, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Root path
base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local libs dir into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

from gmusicapi import Musicmanager
import string
from oauth2client.client import OAuth2WebServerFlow
import oauth2client.file
from bottle import bottle
from bottle.bottle import route, request, post, run, redirect, static_file, template
from beaker.middleware import SessionMiddleware
import requests
from user import User
import util

bottle.TEMPLATE_PATH.insert(0,'/boot/config/plugins/bgmm/bgmm/views')
logged_in = False
SONGS_PER_PAGE = 10

class DirInfo:
    BaseAppDir = "/boot/config/plugins/bgmm/"
    BaseAppDataDir = "/boot/config/appdata/bgmm/"
    
    AppConfig = os.path.join(BaseAppDir, "bgmm_config.cfg")
    OAuthFilename = "oauth.cred"

    @staticmethod
    def get_oauth_file_path(email):
        return os.path.join(DirInfo.BaseAppDataDir, email, DirInfo.OAuthFilename)

    @staticmethod
    def get_user_data_file_path(email):
        return os.path.join(DirInfo.BaseAppDataDir, email, "user_config.cfg")

OAuthInfo = namedtuple('OAuthInfo', 'client_id client_secret scope redirect')
oauth_info = OAuthInfo(
    '70206993729-v1e9qjv0ia5bm56v6l325vmiaj5vm2qb.apps.googleusercontent.com',
    'PhBciko_1b5bTFJ3mHicDyJ1',
    ['https://www.googleapis.com/auth/musicmanager', 'email'],
    'urn:ietf:wg:oauth:2.0:oob'
)

oauth2_flow = OAuth2WebServerFlow(*oauth_info)

users = {}

# ----- Helpers -----

class Song:
    def __init__(self, path, status, id):
        self.path = path
        self.status = status
        self.id = id

def get_email(oauth_token):
    r = requests.get("https://www.googleapis.com/oauth2/v1/userinfo?access_token=" + oauth_token)
    return r.json()["email"]

def check_login(fn):
    def check_logged_in(**kwargs):
        if not logged_in:
            redirect('/login')
        else:
            return fn(**kwargs)
    return check_logged_in

def get_session():
    return bottle.request.environ.get('beaker.session')

def get_email_from_session():
    session = get_session()
    return session.get("email", None)

def get_other_accounts():
    curr_account = get_email_from_session()
    return [user for user in users.keys() if user != curr_account]

def get_session_data():
    email = get_email_from_session()
    other_users = get_other_accounts()
    return {"logged_in": logged_in,
            "email": email,
            "other_users": other_users}

def get_token_from_refresh(refresh_token):
    params = {"refresh_token": refresh_token,
              "client_id": oauth_info.client_id,
              "client_secret": oauth_info.client_secret,
              "grant_type": "refresh_token"
              }
    r = requests.post("https://accounts.google.com/o/oauth2/token", params)
    if "access_token" in r.json():
        return r.json()["access_token"]
    return None

def check_for_existing_tokens():
    # Check for any previously logged-in users and try to use the refresh
    #  tokens to log them in again automatically
    # Only run at process startup
    for root, dirs, files in os.walk(DirInfo.BaseAppDataDir):
        logger.debug("Trying to log in user %s" % os.path.dirname(root))
        if DirInfo.OAuthFilename in files:
            logger.debug("Found credential")
            storage = oauth2client.file.Storage(os.path.join(root, DirInfo.OAuthFilename))
            credentials = storage.get()
            new_access_token = get_token_from_refresh(credentials.refresh_token)
            if new_access_token:
                logger.info("Was able to use refresh_token")
                credentials.access_token = new_access_token
                storage.put(credentials)
                email = get_email(credentials.access_token)
                user = User(email, DirInfo.BaseAppDataDir)
                users[email] = user
                if not user.init(credentials):
                    logger.info("Error logging in user %s" % email)
                else:
                    # This will get re-written over for each user, but for now
                    #  we'll just have the last one we process be who's logged in
                    #  by default
                    global logged_in
                    logged_in = True
                    session = get_session()
                    session["email"] = email
            else:
                logger.info("Unable to use refresh token")

# ----- Web -------

@route('/')
@check_login
def root():
    redirect("/main")

@route('/login')
def login():
    check_for_existing_tokens()
    if logged_in:
        redirect("/main")
    email = get_email_from_session()
    other_users = get_other_accounts()
    oauth_uri = oauth2_flow.step1_get_authorize_url()
    return template('login', session_status=get_session_data(), oauth_uri=oauth_uri)

@post('/submit_oauth_key')
def oauth_submit():
    # Get the oauth_key from the page form
    oauth_key = request.forms.get('oauth_key')
    try:
        credentials = oauth2_flow.step2_exchange(oauth_key)
    except Exception as e:
        return "Error with login: %s" % e
    else:
        # Get the user's email and add it to the session
        email = get_email(credentials.access_token)
        # Store the oauth credentials
        oauth_path = DirInfo.get_oauth_file_path(email)
        util.make_sure_path_exists(os.path.dirname(oauth_path))
        storage = oauth2client.file.Storage(oauth_path)
        storage.put(credentials)

        # Create the user instance and have it login/initialize
        user = User(email, DirInfo.BaseAppDataDir)
        users[email] = user
        if not user.init(credentials):
            return "Error with login, incorrect code?"
        else:
            global logged_in
            logged_in = True
            session = get_session()
            session["email"] = email
            redirect("/main")

@route('/main')
@check_login
def main():
    email = get_email_from_session()
    other_users = get_other_accounts()
    return template('default', content="Welcome!", session_status=get_session_data())

@route('/switch_account/:new_account')
def switch_account(new_account):
    logger.debug("Switching to account %s" % new_account)
    session = get_session()
    session["email"] = new_account
    redirect("/main")

@route('/logout')
def logout():
    email = get_email_from_session()
    logger.debug("logging out, email: %s" % email)
    users[email].logout()
    del users[email]

    try:
        os.remove(DirInfo.get_oauth_file_path(email))
    except OSError as e:
        logger.info("Error logging out: %s" % e)
    global logged_in
    logged_in = False
    redirect("/")

@route('/config')
@check_login
def config():
    email = get_email_from_session()
    user = users[email]
    watched_paths = user.get_watched_paths()
    default_action = user.get_default_action()
    return template('config', session_status=get_session_data(), watched_paths = watched_paths, default_action=default_action)

@route('/status')
@check_login
def status():
    page = int(request.query.page) if request.query.page else 1
    email = get_email_from_session()
    user = users[email]
    songs = user.get_all_songs()
    num_pages = int(len(songs.keys()) / SONGS_PER_PAGE) + 1
    start_song = ((page - 1) * SONGS_PER_PAGE)
    end_song = ((page - 1) * SONGS_PER_PAGE) + SONGS_PER_PAGE
    logger.debug("displaying results for page %s, showing songs %s to %s" % (page, (page * SONGS_PER_PAGE), (page * SONGS_PER_PAGE) + SONGS_PER_PAGE))
    all_songs = sorted(songs.keys())
    page_songs = []
    for song_path in all_songs[start_song : end_song]:
        page_songs.append(Song(song_path, songs[song_path]['status'], songs[song_path]['id']))

    return template('status', session_status=get_session_data(), songs=page_songs, num_pages=num_pages, curr_page=page)

@route('/logs')
def logs():
    email = get_email_from_session()
    with open(LOG_LOCATION, "r") as f:
        log_lines_desc = f.readlines()
        log_lines_desc.reverse()
        return template('logs', session_status=get_session_data(), log_lines=log_lines_desc)

@route('/scan')
@check_login
def scan():
    email = get_email_from_session()
    user = users[email]
    thread.start_new_thread(user.scan_existing_files, ())
    redirect('/status')

@route('/upload')
@check_login
def upload_scanned():
    email = get_email_from_session()
    user = users[email]
    thread.start_new_thread(user.upload_scanned, ())
    redirect('/status')

@post('/remove_watch_path')
@check_login
def remove_watch_path():
    email = get_email_from_session()
    user = users[email]
    curr_page = request.forms.get('curr_page')
    path_strs = ""
    for path in request.forms.getlist('watchpaths'):
        user.remove_watch_path(path)
    redirect(curr_page)

@post('/add_watch_path')
@check_login
def add_watch_path():
    email = get_email_from_session()
    path = request.forms.get('path')
    curr_page = request.forms.get('curr_page')
    users[email].add_watch_path(path)
    redirect(curr_page)

@post('/change_options')
@check_login
def change_options():
    email = get_email_from_session()
    default_action = request.forms.get('default_action')
    logger.info("changing default action to: " + default_action)
    users[email].set_default_action(default_action)
    curr_page = request.forms.get('curr_page')
    redirect(curr_page)


@route('/static/:filename.:ext')
def get_static(filename, ext):
    if ext == "css":
        return static_file(filename + "." + ext, root='/boot/config/plugins/bgmm/bgmm/public/stylesheets')
    if ext == "js":
        return static_file(filename + "." + ext, root="/boot/config/plugins/bgmm/bgmm/public/javascript")
    if ext == "png":
        return static_file(filename + "." + ext, root="/boot/config/plugins/bgmm/bgmm/public/images")

# ----- End Web -------

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
        if not util.make_sure_path_exists(os.path.dirname(pidfile)):
            logger.warning("Error creating pidfile directory %s" % os.path.dirname(pidfile))
            return
        with open(pidfile, "w+") as f:
            logger.debug("Writing pidfile to %s" % pidfile)
            f.write(str(os.getpid()))
    config = util.read_config(DirInfo.AppConfig)

    session_opts = {
        'session.type': 'memory',
        'session.auto': 'true'
    }
    app = SessionMiddleware(bottle.app(), session_opts)

    run(app=app, host='0.0.0.0', port=config['PORT'], debug=True)

if __name__ == "__main__":
    main()
