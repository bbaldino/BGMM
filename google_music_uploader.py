import os, sys
# Root path
base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local libs dir into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

import file_watcher as fw
from gmusicapi import Musicmanager
import string

mm = Musicmanager()
#mm.perform_oauth()
#sys.exit()

def main():
    print "Logging in"
    print mm.login()
    print "Starting watch"
    fw.watch("/mnt/user/Music", finished_writing_callback)
    i = raw_input()
    fw.stop_watching()
    mm.logout()

def finished_writing_callback(new_file_path):
    filename, file_extension = os.path.splitext(new_file_path)
    print "file extension:", file_extension
    if file_extension != ".mp3":
        print "Skipping non-mp3 file"
        return
    print "Uploading new file: ", new_file_path
    uploaded, matched, not_uploaded = mm.upload(new_file_path, enable_matching=True) # async me!
    #print "Uploaded? %s, Matched? %s, Not Uploaded? %s" % (uploaded, matched, not_uploaded)
    if uploaded:
        print "Uploaded song %s with ID %s" % (new_file_path, uploaded[new_file_path])
    if matched:
        print "Matched song %s with ID %s" % (new_file_path, matched[new_file_path])
    if not_uploaded:
        print "Unable to upload song %s because %s" % (new_file_path, not_uploaded[new_file_path])




if __name__ == "__main__":
    main()
