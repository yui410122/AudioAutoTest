from com.dtmilano.android.viewclient import ViewClient

import threading
import datetime
import StringIO as sio
import time

from libs.activitystatemachine import ActivityStateMachine
from libs.logger import Logger

def utf8str(s):
    try:
        return unicode(s).encode("UTF-8")
    except:
        return s

class GoogleMusicApp(ActivityStateMachine):
    COMPONENT = "com.google.android.music/com.android.music.activitymanagement.TopLevelActivity"

    PLAY_CARD_KEY = "com.google.android.music:id/play_card"
    LI_TITLE_KEY = "com.google.android.music:id/li_title"
    LI_SUBTITLE_KEY = "com.google.android.music:id/li_subtitle"
    CONTAINER_KEY = "com.google.android.music:id/drawer_container"
    ART_PAGER_KEY = "com.google.android.music:id/art_pager"
    PLAY_PAUSE_HEADER_KEY = "com.google.android.music:id/play_pause_header"

    CONTROL_PANEL_PROGRESS_KEY = "android:id/progress"
    CONTROL_PANEL_PLAY_PAUSE_KEY = "com.google.android.music:id/pause"
    CONTROL_PANEL_PREV_KEY = "com.google.android.music:id/prev"
    CONTROL_PANEL_NEXT_KEY = "com.google.android.music:id/next"

    class State(object):
        UNKNOWN = "Unknown"
        TOP_ACTIVITY = "TopActivity"
        TRACK_LIST = "TrackList"
        CONTROL_PANEL = "ControlPanel"

        TOP_ACTIVITY_STATE = {
            "name": TOP_ACTIVITY,
            "check": lambda s: \
                "com.google.android.music:id/play_card" in s or \
                "com.google.android.music:id/empty_text" in s
        }
        TRACK_LIST_STATE = {
            "name": TRACK_LIST,
            "check": lambda s: \
                    "com.google.android.music:id/controls_container" in s and \
                not "com.google.android.music:id/play_card" in s
        }
        CONTROL_PANEL_STATE = {
            "name": CONTROL_PANEL,
            "check": lambda s: \
                "com.google.android.music:id/play_controls" in s
        }

        ALL_STATES = [
            TOP_ACTIVITY_STATE,
            TRACK_LIST_STATE,
            CONTROL_PANEL_STATE
        ]

    def __init__(self, device, serialno):
        super(GoogleMusicApp, self).__init__(device, serialno)
        self.extra = {
            "dump": [],
            "dump-lock": threading.Lock()
        }
        self.cache = {}

    def log(self, text):
        Logger.log("GoogleMusicApp", text)

    def dump(self):
        self.extra["dump-lock"].acquire()
        Logger.log("GoogleMusicApp", "dump called")
        Logger.log("GoogleMusicApp", "----------------------------------------------")
        map(lambda x: Logger.log("GoogleMusicApp::dump", "\"{}\"".format(x)), self.extra["dump"])
        Logger.log("GoogleMusicApp", "----------------------------------------------")
        del self.extra["dump"][:]
        self.extra["dump-lock"].release()

    def push_dump(self, text):
        self.extra["dump-lock"].acquire()
        self.extra["dump"].append("[{}] {}".format(datetime.datetime.now(), text))
        self.extra["dump-lock"].release()

    def clear_dump(self):
        self.extra["dump-lock"].acquire()
        del self.extra["dump"][:]
        self.extra["dump-lock"].release()

    def walk_through(self):
        if not self.to_top():
            Logger.log("GoogleMusicApp", "walk_through failed: unable to go to top activity")
            return False

        # Get the playcard titles
        vc = ViewClient(self.device, self.serialno)

        container_key = GoogleMusicApp.CONTAINER_KEY
        container = [v for v in vc.getViewsById().values() if v.getId() == container_key]
        container = container[0] if len(container) > 0 else None
        if container:
            self.cache["screen-info"] = container.getBounds()[1]
            self.push_dump("screen-info: {}".format(self.cache["screen-info"]))

        so = sio.StringIO()
        vc.traverse(stream=so)
        lines = so.getvalue().splitlines()
        play_card_key = GoogleMusicApp.PLAY_CARD_KEY
        playcards_idices = [idx for idx, line in enumerate(lines) if play_card_key in line]
        playcards_idices.append(len(lines))
        playcards_titles = []
        last_idx = playcards_idices[0]

        li_title_key = GoogleMusicApp.LI_TITLE_KEY
        for idx in playcards_idices[1:]:
            li_title_texts = [line for line in lines[last_idx:idx] if li_title_key in line]
            last_idx = idx

            if len(li_title_texts) != 1:
                self.push_dump("li_title_texts has length {}".format(len(li_title_texts)))

            playcards_titles.append(utf8str(li_title_texts[0].split(li_title_key)[-1].strip()))
            self.push_dump("playcards_titles.append('{}')".format(playcards_titles[-1]))

        # Get the track list of each playcard
        views = [v for v in vc.getViewsById().values() if v.getId() == li_title_key and utf8str(v.getText()) in playcards_titles]
        self.cache["playcard"] = dict( \
                map(lambda v: (utf8str(v.getText()), { "position": v.getCenter() }), views)
            )
        map(lambda v: self.push_dump("view: {}".format(utf8str(v))), views)
        map(lambda title: self.push_dump("playcard title: '{}'".format(title)), self.cache["playcard"].keys())

        if len(views) == 0:
            return False

        self.cache["shuffle_key"] = playcards_titles[0]
        self.push_dump("get the shuffle keyword '{}'".format(self.cache["shuffle_key"]))
        self.touch_playcard(self.cache["shuffle_key"])
        time.sleep(1)

        retry_count = 3
        while retry_count > 0:
            vc.dump()
            play_pause_header_key = GoogleMusicApp.PLAY_PAUSE_HEADER_KEY
            play_pause_btn_view = [v for v in vc.getViewsById().values() if v.getId() == play_pause_header_key]
            play_pause_btn_view = play_pause_btn_view[0] if len(play_pause_btn_view) > 0 else None
            if play_pause_btn_view:
                play_desc = utf8str(play_pause_btn_view.getContentDescription())
                self.check_play_status = lambda desc: desc == play_desc
                self.cache["play_pause_btn"] = { "position": play_pause_btn_view.getCenter(), "desc_feat": play_desc }

                art_pager_key = GoogleMusicApp.ART_PAGER_KEY
                art_pager_view = [v for v in vc.getViewsById().values() if v.getId() == art_pager_key]
                art_pager_view = art_pager_view[0] if len(art_pager_view) > 0 else None
                if not art_pager_view:
                    continue
                self.cache["art_pager_view"] = { "position": art_pager_view.getCenter() }

                play_pause_btn_view.touch()
                break
            else:
                self.push_dump("cannot find the play/pause button, retry: {}".format(retry_count))
                retry_count -= 1

        for li_title in self.cache["playcard"].keys():
            if li_title == self.cache["shuffle_key"]:
                continue
            self.push_dump("now fetching information in the playcard '{}'".format(li_title))
            if self.touch_playcard(li_title=li_title):
                time.sleep(1)
                self.cache["playcard"][li_title]["songs"] = self._fetch_songs()
                self.to_top()

        # Get the information of the control panel
        retry_count = 3
        while self.get_state() != GoogleMusicApp.State.CONTROL_PANEL and retry_count > 0:
            self.device.touch(*self.cache["art_pager_view"]["position"])
            retry_count -= 1

        if retry_count == 0 and self.get_state() != GoogleMusicApp.State.CONTROL_PANEL:
            self.to_top()
            time.sleep(5)
            self.touch_playcard(self.cache["shuffle_key"])
            time.sleep(2)
            self.device.touch(*self.cache["play_pause_btn"]["position"])
            time.sleep(2)
            self.device.touch(*self.cache["art_pager_view"]["position"])
            time.sleep(2)
            if self.get_state() != GoogleMusicApp.State.CONTROL_PANEL:
                self.push_dump("cannot get the information of the control panel")
                return False

        def find_view_position(vc, res_id):
            v = [v for v in vc.getViewsById().values() if v.getId() == res_id]
            if len(v) == 0:
                return (-1, -1)
            return v[0].getCenter()

        vc.dump()
        self.cache["control_panel"] = {
            "progress": { "position": find_view_position(vc, GoogleMusicApp.CONTROL_PANEL_PROGRESS_KEY) },
            "prev": { "position": find_view_position(vc, GoogleMusicApp.CONTROL_PANEL_PREV_KEY) },
            "next": { "position": find_view_position(vc, GoogleMusicApp.CONTROL_PANEL_NEXT_KEY) },
            "play_pause": { "position": find_view_position(vc, GoogleMusicApp.CONTROL_PANEL_PLAY_PAUSE_KEY) }
        }
        self.push_dump("successfully walked through, now back to top")
        self.to_top()

        return True

    def is_playing(self):
        vc = ViewClient(self.device, self.serialno)
        play_pause_header_key = GoogleMusicApp.PLAY_PAUSE_HEADER_KEY
        play_pause_btn_view = [v for v in vc.getViewsById().values() if v.getId() == play_pause_header_key]
        play_pause_btn_view = play_pause_btn_view[0] if len(play_pause_btn_view) > 0 else None

        if play_pause_btn_view:
            return self.check_play_status(utf8str(play_pause_btn_view.getContentDescription()))

        ctrl_panel_play_pause_key = GoogleMusicApp.CONTROL_PANEL_PLAY_PAUSE_KEY
        ctrl_panel_play_pause_view = [v for v in vc.getViewsById().values() if v.getId() == ctrl_panel_play_pause_key]
        ctrl_panel_play_pause_view = ctrl_panel_play_pause_view[0] if len(ctrl_panel_play_pause_view) > 0 else None

        if ctrl_panel_play_pause_view:
            return self.check_play_status(utf8str(ctrl_panel_play_pause_view.getContentDescription()))

        return False

    def get_playcards(self):
        if "playcard" in self.cache.keys():
            return self.cache["playcard"]
        return {}

    def _drag_up(self, drag_up_count=1):
        w, h = self.cache["screen-info"]
        for _ in range(drag_up_count):
            self.device.drag((w/2, h/2), (w/2, 0), duration=1000)

    def _fetch_songs(self):
        vc = ViewClient(self.device, self.serialno, autodump=False)
        songs = {}
        drag_up_count = 0
        li_title_key = GoogleMusicApp.LI_TITLE_KEY
        while True:
            song_props = self._fetch_songs_on_current_screen(vc=vc)
            song_props = filter(lambda prop: not prop[0] in songs.keys(), song_props)
            if len(song_props) == 0:
                break
            for name, duration in song_props:
                v = [v for v in vc.getViewsById().values() if v.getId() == li_title_key and utf8str(v.getText()) == name]
                if len(v) != 1:
                    self.push_dump("in _fetch_songs, got multiple songs with the same name '{}'".format(name))
                v = v[0] if len(v) > 0 else None
                songs[name] = {
                    "duration": duration,
                    "drag_up_count": drag_up_count,
                    "position": v.getCenter() if v else (-1, -1)
                }
            self._drag_up()
            drag_up_count += 1

        for name, info in songs.items():
            self.push_dump("{}: {}".format(name, info))

        return songs

    def _fetch_songs_on_current_screen(self, vc):
        vc.dump()
        so = sio.StringIO()
        vc.traverse(stream=so)
        traverse_str = so.getvalue()
        self.push_dump("in _fetch_songs_on_current_screen: got the traverse string\n{}".format(traverse_str))
        lines = traverse_str.splitlines()
        li_title_key = GoogleMusicApp.LI_TITLE_KEY
        li_subtitle_key = GoogleMusicApp.LI_SUBTITLE_KEY
        song_feat_strs = [lines[idx:idx+2] \
            for idx, line in enumerate(lines[:-1]) if li_title_key in line and li_subtitle_key in lines[idx+1]]

        def str2sec(time_str):
            if len(time_str.split(":")) == 2:
                timeformat = "%M:%S"
                zerostr = "0:0"
            elif len(time_str.split(":")) == 3:
                timeformat = "%H:%M:%S"
                zerostr = "0:0:0"
            else:
                return time_str

            t = datetime.datetime.strptime(time_str, timeformat)
            t0 = datetime.datetime.strptime(zerostr, timeformat)
            return (t - t0).total_seconds()

        song_properties = map( \
            lambda feat: ( \
                    utf8str(feat[0].split(li_title_key)[-1].strip()), str2sec(feat[1].split(li_subtitle_key)[-1].strip()) \
                ), song_feat_strs)
        map(lambda prop: self.push_dump("song_prop: {}".format(prop)), song_properties)
        return song_properties

    def touch_playcard(self, li_title):
        if not li_title in self.cache["playcard"].keys():
            self.push_dump("the li_title '{}' does not exist".format(li_title))
            return False

        self.device.touch(*self.cache["playcard"][li_title]["position"])
        return True

    def get_state(self):
        vc = ViewClient(self.device, self.serialno)
        so = sio.StringIO()
        vc.traverse(stream=so)
        states = [state for state in GoogleMusicApp.State.ALL_STATES if state["check"](so.getvalue())]
        if len(states) > 1:
            self.push_dump("get_state returns more than one states: [{}]".format( \
                    ", ".join(map(lambda state: "'{}'".format(state["name"]), states)) \
                ))
        if len(states) > 0:
            return states[0]["name"]

        return GoogleMusicApp.State.UNKNOWN

    def to_top(self):
        self.push_dump("to_top called")

        current_state = self.get_state()
        if current_state == GoogleMusicApp.State.TOP_ACTIVITY:
            self.push_dump("return directly")
            return True

        if current_state == GoogleMusicApp.State.UNKNOWN:
            self.push_dump("unknown state, back to home")
            self.device.press("HOME")
            time.sleep(1)
            self.push_dump("start the google music")
            self.device.startActivity(GoogleMusicApp.COMPONENT)
            time.sleep(5)

        current_state = self.get_state()
        if current_state != GoogleMusicApp.State.TOP_ACTIVITY:
            self.push_dump("the state is '{}', press back key".format(current_state))
            self.device.press("BACK")
            time.sleep(1)
        else:
            return True

        current_state = self.get_state()
        if current_state != GoogleMusicApp.State.TOP_ACTIVITY:
            self.push_dump("the state is '{}', press back key".format(current_state))
            self.device.press("BACK")
            time.sleep(1)
        else:
            return True

        return self.get_state() == GoogleMusicApp.State.TOP_ACTIVITY
