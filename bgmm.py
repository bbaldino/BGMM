import os, sys, logging
# Root path
base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local libs dir into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

import file_watcher as fw
from gmusicapi import Musicmanager
import string
from bottle.bottle import route, request, post, run, redirect

mm = Musicmanager()
logger = logging.getLogger("gmu")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("/tmp/gmu.log")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
OAUTH_PATH="/boot/config/appdata/gmu/"
OAUTH_FILE="oauth.cred"

@route('/')
def hello():
    logger.info("ON LANDING PAGE")
    if not mm.login(os.path.join(OAUTH_PATH, OAUTH_FILE)):
        oauth_uri = mm.get_oauth_uri()
        return '''Need to perform oauth, please visit this url and paste the key you receive here: %s
                  <form method="POST" action="/submit_oauth_key">
                    <input name="oauth_key" type="text"/>
                    <input type="submit" />
                  </form>''' % oauth_uri
    else:
        redirect("/main")

@post('/submit_oauth_key')
def oauth_submit():
    oauth_key = request.forms.get('oauth_key')
    try:
        os.makdirs(OAUTH_PATH)
        mm.set_oauth_code(oauth_key, os.path.join(OAUTH_PATH, OAUTH_FILE))
    except:
        return "Error with login"
    else:
        if not mm.login(os.path.join(OAUTH_PATH, OAUTH_FILE)):
            return "Error with login, incorrect code?"
        else:
            redirect("/main")

@route('/main')
def main():
    fw.watch("/mnt/user/Music", finished_writing_callback)
    return "Started watching directory"

def finished_writing_callback(new_file_path):
    filename, file_extension = os.path.splitext(new_file_path)
    logger.debug("finished writing file, file extension:", file_extension)
    if file_extension != ".mp3":
        logger.debug("Skipping non-mp3 file")
        return
    logger.info("Uploading new file: ", new_file_path)
    uploaded, matched, not_uploaded = mm.upload(new_file_path, enable_matching=False) # async me!
    if uploaded:
        logger.info("Uploaded song %s with ID %s" % (new_file_path, uploaded[new_file_path]))
    if matched:
        logger.info("Matched song %s with ID %s" % (new_file_path, matched[new_file_path]))
    if not_uploaded:
        logger.info("Unable to upload song %s because %s" % (new_file_path, not_uploaded[new_file_path]))

def main():
    logger.info("Starting google music uploader")
    pidfile = None
    if sys.argv[1] == "--pidfile":
        if len(sys.argv) < 3:
            logger.error("Missing pidfile path")
            return
        pidfile = sys.argv[2]

    if pidfile:
        try:
            os.makedirs(os.path.dirname(pidfile))
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                pass
            else:
                logger.warning("Error making pidfile directory")
        with open(pidfile, "w+") as f:
            f.write(str(os.getpid()))


    run(host='0.0.0.0', port=9090, debug=True)


if __name__ == "__main__":
    main()
