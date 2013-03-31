import os
from pyinotify.pyinotify import WatchManager, Notifier, ThreadedNotifier, EventsCodes, ProcessEvent

wm = WatchManager()

mask = EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_CREATE'] | \
       EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_CLOSE_WRITE'] | \
       EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_DELETE']

class EventHandler(ProcessEvent):
    def add_finished_writing_callback(self, finished_writing_callback):
        print "Adding finished writing callback"
        self.finished_writing_callback = finished_writing_callback
    def process_IN_CREATE(self, event):
        print "Create: %s" % os.path.join(event.path, event.name)
    def process_IN_CLOSE_WRITE(self, event):
        print "Finished writing: %s" % os.path.join(event.path, event.name)
        self.finished_writing_callback(os.path.join(event.path, event.name))
    def process_IN_DELETE(self, event):
        print "Deleted %s" % os.path.join(event.path, event.name)

notifier = None

def watch(file_path, finished_writing_callback):
    print "Will monitor %s for changes" % file_path
    handler = EventHandler()
    handler.add_finished_writing_callback(finished_writing_callback)
    global notifier
    notifier = ThreadedNotifier(wm, handler)
    notifier.start()
    wdd = wm.add_watch(file_path, mask, rec=True, auto_add=True)

def stop_watching():
    print "stopping!"
    global notifier
    notifier.stop()
    print "stopped!"


'''
while True:
    try:
        notifier = Notifier(wm, EventHandler())
        notifier.process_events()
        if notifier.check_events():
            notifier.read_events()
    except KeyboardInterrupt:
        notifier.stop()
        break
'''
