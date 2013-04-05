import os, sys
# Root path
base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local libs dir into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

import file_watcher as fw
from gmusicapi import Musicmanager
import string
from bottle.bottle import route, request, post, run, redirect

mm = Musicmanager()

@route('/')
def hello():
    if not mm.login():
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
        mm.set_oauth_code(oauth_key)
    except:
        return "Error with login"
    else:
        if not mm.login():
            return "Error with login, incorrect code?"
        else:
            redirect("/main")

@route('/main')
def main():
    fw.watch("/mnt/user/Music", finished_writing_callback)
    return "Started watching directory"

def finished_writing_callback(new_file_path):
    filename, file_extension = os.path.splitext(new_file_path)
    print("file extension:", file_extension)
    if file_extension != ".mp3":
        print("Skipping non-mp3 file")
        return
    print("Uploading new file: ", new_file_path)
    uploaded, matched, not_uploaded = mm.upload(new_file_path, enable_matching=True) # async me!
    #print "Uploaded? %s, Matched? %s, Not Uploaded? %s" % (uploaded, matched, not_uploaded)
    if uploaded:
        print("Uploaded song %s with ID %s" % (new_file_path, uploaded[new_file_path]))
    if matched:
        print("Matched song %s with ID %s" % (new_file_path, matched[new_file_path]))
    if not_uploaded:
        print("Unable to upload song %s because %s" % (new_file_path, not_uploaded[new_file_path]))

run(host='0.0.0.0', port=9090, debug=True)

'''
def main():
    print("Logging in")
    while True:
        try:
            print(mm.login())
        except AttributeError as e:
            print("Need to perform oauth before trying to log in")
            url = mm.get_oauth_uri()
            print(url)
            code = raw_input("code:")
            mm.set_oauth_code(code)
        else:
            break
    print("Starting watch")
    fw.watch("/mnt/user/Music", finished_writing_callback)
    i = raw_input()
    fw.stop_watching()
    mm.logout()

def finished_writing_callback(new_file_path):
    filename, file_extension = os.path.splitext(new_file_path)
    print("file extension:", file_extension)
    if file_extension != ".mp3":
        print("Skipping non-mp3 file")
        return
    print("Uploading new file: ", new_file_path)
    uploaded, matched, not_uploaded = mm.upload(new_file_path, enable_matching=True) # async me!
    #print "Uploaded? %s, Matched? %s, Not Uploaded? %s" % (uploaded, matched, not_uploaded)
    if uploaded:
        print("Uploaded song %s with ID %s" % (new_file_path, uploaded[new_file_path]))
    if matched:
        print("Matched song %s with ID %s" % (new_file_path, matched[new_file_path]))
    if not_uploaded:
        print("Unable to upload song %s because %s" % (new_file_path, not_uploaded[new_file_path]))




if __name__ == "__main__":
    main()
'''
