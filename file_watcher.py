import os
import logging
from pyinotify.pyinotify import WatchManager, Notifier, ThreadedNotifier, EventsCodes, ProcessEvent

wm = WatchManager()
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

notifier = None
watches = {}

def watch(file_path, finished_writing_callback):
    logger.info("Will monitor %s for changes" % file_path)
    if file_path in watches:
        logger.info("Already monitoring")
        return
    handler = EventHandler()
    handler.add_finished_writing_callback(finished_writing_callback)
    global notifier
    notifier = ThreadedNotifier(wm, handler)
    notifier.start()
    wdd = wm.add_watch(file_path, mask, rec=True, auto_add=True)
    watches[file_path] = wdd[file_path]
    logger.debug("filewatch dict is now: %s" % watches)

def remove_watch(file_path):
    watch_fd = watches.get(file_path)
    logger.debug("Got watch_fd %s for path %s" % (watch_fd, file_path))
    if watch_fd:
        rr = wm.rm_watch(watch_fd, rec=True)
        if rr.get(watch_fd):
            logger.info("Successfully stopped watching path %s" % file_path)
        else:
            logger.warning("Error trying to stop watching path %s" % file_path)
        del watches[file_path]
    else:
        logger.warning("Tried to stop watching un-watched path %s" % file_path)

def stop_watching():
    logger.info("Stopping file watch")
    global notifier
    notifier.stop()
    logger.info("Stopped file watch")

def get_watched_paths():
    return watches
