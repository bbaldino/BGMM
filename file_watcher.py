import os
import logging
from pyinotify.pyinotify import WatchManager, Notifier, ThreadedNotifier, EventsCodes, ProcessEvent

logger = logging.getLogger("bgmm")

mask = EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_CREATE'] | \
       EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_CLOSE_WRITE'] | \
       EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_DELETE']

class EventHandler(ProcessEvent):
    def add_finished_writing_callback(self, finished_writing_callback):
        logger.info("Adding finished writing callback")
        self.finished_writing_callback = finished_writing_callback
    def process_IN_CREATE(self, event):
        logger.info("Create: %s" % os.path.join(event.path, event.name))
    def process_IN_CLOSE_WRITE(self, event):
        logger.info("Finished writing: %s" % os.path.join(event.path, event.name))
        self.finished_writing_callback(os.path.join(event.path, event.name))
    def process_IN_DELETE(self, event):
        logger.info("Deleted %s" % os.path.join(event.path, event.name))

class FileWatcher:
    def __init__(self, email, finished_writing_callback, paths=[]):
        self.email = email
        self.wm = WatchManager()
        self.watches = {}
        self.handler = EventHandler()
        self.handler.add_finished_writing_callback(finished_writing_callback)
        self.notifier = ThreadedNotifier(self.wm, self.handler)
        self.notifier.start()
        logger.info("Created FileWatcher for %s" % self.email)
        for path in paths:
            self.watch(path)

    def watch(self, path):
        logger.info("Will monitor %s for changes for %s" % (path, self.email))
        if path in self.watches:
            logger.info("Already monitoring that path")
            return
        wdd = self.wm.add_watch(path, mask, rec=True, auto_add=True)
        self.watches[path] = wdd[path]
        logger.debug("File watch dict for %s is now %s" % (self.email, self.watches))

    def remove_watch(self, path):
        watch_fd = self.watches.get(path)
        if watch_fd:
            rr = self.wm.rm_watch(watch_fd, rec=True)
            if rr.get(watch_fd):
                logger.info("Successfully stopped watching path %s for %s" % (path, self.email))
            else:
                logger.warning("Error trying to stop watching path %s for %s" % (path, self.email))
            del self.watches[path]
        else:
            logger.warning("Tried to stop watching un-watched path %s for %s" % (path, self.email))

    def stop_watching(self):
        logger.info("Stopping file watch for %s" % self.email)
        self.notifier.stop()

    def get_watched_paths(self):
        return self.watches
        
