import os, sys, logging, errno
# Root path
base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local libs dir into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

import file_watcher as fw
from gmusicapi import Musicmanager
import string
from bottle.bottle import route, request, post, run, redirect
import json

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
config = {}
logged_in = False

# ----- Web -------
main_page_template = '''
<style>
body {{
    background-color:#b0c4de;
}}

div.header {{
    font-size:xx-large;
    font-family:monospace;
    font-variant:small-caps;
}}

div.navbar {{
    width: 100%;
    height: 28px;
    #border: 5px solid gray;
    background-color:#A3A3A3;
}}

ul {{
    list-style-type:none;
    margin:0;
    padding:0;
}}

li {{
    float: left;    
}}

a:link,a:visited {{
    display:block;
    width:120px;
    font-weight:bold;
    color:#FFFFFF;
    background-color:#A3A3A3;
    text-align:center;
    padding:4px;
    text-decoration:none;
    text-transform:uppercase;
}}

a:hover,a:active {{
    background-color:#006699;
}}

select {{
    min-width: 100px;
}}

.footer {{
    position:fixed;
    bottom:0;
    left:50%;
    margin-left:-200px; /*negative half the width */    
    width:400px;
    height:100px;
    
    text-align: center;
    vertical-align: middle;
}}

input[type=text] {{
    min-width: 150px;
}}
</style>
<div class="header">
    bgmm
</div>
<div class="navbar">
    <ul>
        <li><a href="/main">Home</a></li>
        <li><a href="/config">Config</a></li>
        <li><a href="/logs">Logs</a></li>
    </ul>
</div>
<div class="content">
    {0}
</div>
<div class="footer">    
    bgmm version: .1<br/>    
</div>
'''

@route('/')
def root():
    if not mm.login(os.path.join(OAUTH_PATH, OAUTH_FILE)):
        oauth_uri = mm.get_oauth_uri()
        return '''Need to perform oauth, please visit <a href="%s">this url</a> and paste the key you receive here:
                  <form method="POST" action="/submit_oauth_key">
                    <input name="oauth_key" type="text"/>
                    <input type="submit" />
                  </form>''' % oauth_uri
    else:
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
            redirect("/main")

@route('/main')
def main():
    return main_page_template.format("Welcome!")

@route('/config')
def config():
    watched_paths = fw.get_watched_paths()
    content_str = '''
<table>
    <tr>
        <td>
            <form name="watchpath_add" method="POST" action="/add_watch_path">
                Add a new path:<br/>
                <input type="hidden" name="curr_page" value="/config">
                <input name="path" type="text">
                <br/>
                <button type="submit">Add Path</button>
            </form>
        </td>
        <td>
            Watched Paths:<br/>
            <form name="watchpath_remove" method="POST" action="/remove_watch_path">
                <input type="hidden" name="curr_page" value="/config">
                <select name="watchpaths" multiple="multiple">
                    %s
                </select>
                <br/>
                <button type="submit">Remove Path</button> 
            </form>
        </td>
    </tr>
</tale>
'''
    paths_str = ""
    for path in watched_paths.keys():
        paths_str += "<option value=\"%s\">%s</option>" % (path, path)
    content_str = content_str % paths_str

    return main_page_template.format(content_str)

@route('/logs')
def logs():
    with open("/tmp/gmu.log", "r") as f:
        log_lines_desc = f.readlines()
        log_lines_desc.reverse()
        return main_page_template.format("<br />".join(log_lines_desc))

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

# ----- End Web -------


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

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            return False

    return True

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
            logger.debug("Writing pidfile to", pidfile)
            f.write(str(os.getpid()))
    # Start watching any previously configured paths
    global config
    read_config()
    if "watched_paths" in config:
        for path in config["watched_paths"]:
            fw.watch(path, finished_writing_callback)


    run(host='0.0.0.0', port=9090, debug=True)


if __name__ == "__main__":
    main()
