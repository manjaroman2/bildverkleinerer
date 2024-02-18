from __future__ import annotations
from typing import *
from enum import Enum
from queue import Queue
from io import StringIO
from sys import platform
from pathlib import Path
from dataclasses import dataclass
from subprocess import PIPE, Popen
from threading import Thread, Lock
from shlex import join as shlex_join
from json import JSONEncoder, dumps as json_dumps, loads as json_loads

from tkinter import (
    Text,
    INSERT,
    HORIZONTAL,
    LEFT,
    SOLID,
    Toplevel,
    StringVar,
    BooleanVar,
    IntVar,
    Tk,
)
from tkinter.ttk import Label, Frame, Entry, Checkbutton, OptionMenu, Scale
from PIL.ImageTk import PhotoImage
from PIL.ImageChops import add as PIL_add, difference as PIL_difference
from PIL.Image import Resampling, open as PIL_open, new as PIL_new, Image

import stdout_helpers


def run_in_thread(
    target, handle_return=None, string_io=None, join=False
) -> Union[None, StringIO]:
    if string_io:
        if not stdout_helpers.proxy_enabled:
            stdout_helpers.enable_proxy()

        _queue = Queue()

        def _wrapper():
            _queue.put_nowait(stdout_helpers.redirect())
            ret = target()
            if handle_return:
                handle_return(ret)
            stdout_helpers.stop_redirect()

        t = Thread(target=_wrapper)
        t.start()
        if join:
            t.join()
        return _queue.get_nowait()

    def _wrapper():
        ret = target()
        if handle_return:
            handle_return(ret)

    t = Thread(target=_wrapper)
    t.start()
    if join:
        t.join()


class ImageFile:
    def __init__(self, path: Path, relpath: Path) -> None:
        self.src_path: Path = path
        self.dest_path: Path = ""
        self.relpath: Path = relpath
        with PIL_open(self.src_path) as img:
            self.res = f"{img.width}x{img.height}"

    def add_text(self, text: Text, pos: str):
        self.startidx = text.index(INSERT)
        text.insert(pos, f"{self.res:11} {self.relpath}\n")
        self.endidx = text.index(INSERT)


class LogLevel(Enum):
    MSG = 1
    ERR = 2


def build_cmd(*cmd):
    if platform == "win32":
        cmd = list(cmd)
        cmd[0] = f"{cmd[0]}.exe"
        return cmd
    else:
        return ["/bin/sh", "-c", f"{shlex_join(cmd)}"]


def run_cmd(*cmd, linehook=None) -> List[str]:
    cmd = build_cmd(*cmd)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=False)
    lines = []
    while True:
        line = p.stdout.readline()
        lines.append(line)
        if not line and p.poll() is not None:
            break
        elif linehook is not None:
            linehook(line)
    return lines


def get_curr_screen_geometry():
    """
    Workaround to get the size of the current screen in a multi-screen setup.

    Returns:
        geometry (str): The standard Tk geometry string.
            [width]x[height]+[left]+[top]
    """
    root = Tk()
    root.update_idletasks()
    root.attributes("-fullscreen", True)
    root.state("iconic")
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    root.destroy()
    return w, h


def center_window(
    win, screen_width, screen_height, width=0, height=0, xoffset=0, yoffset=0
):
    win.update_idletasks()
    width = width if width else win.winfo_width()
    height = height if height else win.winfo_height()
    frm_width = win.winfo_rootx() - win.winfo_x()
    win_width = width + 2 * frm_width
    titlebar_height = win.winfo_rooty() - win.winfo_y()
    win_height = height + titlebar_height + frm_width
    x = screen_width // 2 - win_width // 2
    y = screen_height // 2 - win_height // 2
    win.geometry("{}x{}+{}+{}".format(width, height, x + xoffset, y + yoffset))
    win.deiconify()


def int_entry_create(parent, getter, setter, width) -> Entry:
    sv = StringVar()

    def on_write(*args):
        if sv.get():
            setter(int(sv.get()))

    sv.trace_add("write", on_write)
    entry = Entry(parent, width=width, textvariable=sv)
    entry.bind("<Return>", lambda event: parent.focus())
    if (v := getter()) is not None:
        sv.set(str(v))
    return entry


def bool_checkbox_create(parent, getter, setter, text) -> Checkbutton:
    bv = BooleanVar()
    bv.trace_add("write", lambda *args: setter(bv.get()))
    cb = Checkbutton(parent, text=text, variable=bv)
    cb.bind("<Return>", lambda event: parent.focus())
    if (v := getter()) is not None:
        bv.set(v)
    return cb


class DataClassMeta(type):
    def __new__(cls, name, bases, clsdict):
        new_cls = super().__new__(cls, name, bases, clsdict)
        return dataclass(new_cls)


class Transform(metaclass=DataClassMeta):
    __ID: ClassVar[int] = 0
    __ID_LOCK: ClassVar[Lock] = Lock()

    def __post_init__(self):
        self._id: int = Transform.__get_id__()
        self._next: Transform = None

    def __call__(self, im: Image) -> Image:
        raise NotImplementedError

    def __str__(self) -> str:
        return str(
            dict((k, getattr(self, k, None)) for k in self.__annotations__.keys())
        )

    def widget(self, parent):
        raise NotImplementedError

    @classmethod
    def __get_id__(cls) -> int:
        Transform.__ID_LOCK.acquire(blocking=True)
        id = Transform.__ID
        Transform.__ID += 1
        Transform.__ID_LOCK.release()
        return id


class LinkedList:
    def __init__(self, transforms: List[Transform] = None):
        self.head = None
        if transforms is not None and transforms:
            node = transforms[0]
            self.head = node
            for elem in transforms[1:]:
                node._next = elem
                node = node._next

    def propagate(self, src_path: Path) -> Image:
        im = PIL_open(src_path)
        for transform in self:
            im = transform(im)
        return im

    def __repr__(self) -> str:
        node = self.head
        nodes = []
        while node is not None:
            nodes.append(str(node))
            node = node._next
        nodes.append("None")
        return " -> ".join(nodes)

    def __len__(self):
        node = self.head
        i = 0
        while node is not None:
            i += 1
            node = node._next
        return i

    def index(self, node: Transform):
        i = 0
        for _node in self:
            if _node._id == node._id:
                return i
            i += 1
        raise Exception(f"Node with id {node._id} not found")

    def indices(self, *nodes: List[Transform]):
        _copy = list(nodes)
        r = [0] * len(_copy)
        i = 0
        for _node in self:
            if _todo := len(_copy) > 0:
                for j in range(_todo):
                    node = _copy[j]
                    if _node._id == node._id:
                        r[j] = i
                        _copy.pop(j)
                        break
            else:
                return r
            i += 1
        if len(_copy) == 0:
            return r
        raise Exception(f"Nodes with ids {[n._id for n in _copy]} not found")

    def __iter__(self):
        node = self.head
        while node is not None:
            yield node
            node = node._next

    def add_first(self, node: Transform):
        node._next = self.head
        self.head = node

    def add_last(self, node: Transform):
        if self.head is None:
            self.head = node
            return
        for current_node in self:
            pass
        current_node._next = node

    def add_after(self, node_id, new_node):
        if self.head is None:
            raise Exception("List is empty")
        for node in self:
            if node._id == node_id:
                new_node._next = node._next
                node._next = new_node
                return

        raise Exception(f"Node with id {node_id} not found")

    def add_before(self, node_id, new_node):
        if self.head is None:
            raise Exception("List is empty")
        if self.head._id == node_id:
            return self.add_first(new_node)
        prev_node = self.head
        for node in self:
            if node._id == node_id:
                prev_node._next = new_node
                new_node._next = node
                return
            prev_node = node
        raise Exception(f"Node with id {node_id} not found")

    def replace_node(self, old_node: Transform, new_node: Transform):
        if self.head is None:
            raise Exception("List is empty")
        if self.head._id == old_node._id:
            new_node._next = self.head._next
            self.head._next = None
            self.head = new_node
            return

        prev_node = self.head

        for node in self:
            if node._id == old_node._id:
                new_node._next = node._next
                prev_node._next = new_node
                node._next = None
                return

            prev_node = node
        raise Exception(f"Node with id {old_node._id} not found")

    def move_up(self, node: Transform) -> bool:
        if self.head is None:
            raise Exception("List is empty")
        if self.head._id == node._id:
            return False
        if self.head._next._id == node._id:
            self.head._next = node._next
            node._next = self.head
            self.head = node
            return True
        prev_node = self.head
        for _node in self:
            if _node._next._id == node._id:
                prev_node._next = node
                _node._next = node._next
                node._next = _node
                return True
            prev_node = _node
        raise Exception(f"Could not find Node with id {node._id}")

    def move_down(self, node: Transform) -> Transform:
        node_next = node._next
        return node_next if node_next is not None and self.move_up(node_next) else None

    def remove_node(self, node: Transform):
        if self.head is None:
            raise Exception("List is empty")

        if self.head._id == node._id:
            self.head = self.head._next
            return

        previous_node = self.head
        for _node in self:
            if _node._id == node._id:
                previous_node._next = node._next
                return
            previous_node = _node

        raise Exception(f"Node with id {node._id} not found")


class Resize(Transform):
    longside: int = None
    shortside: int = None
    auto_shortside: bool = None
    resampling: Resampling = Resampling.BILINEAR

    def __call__(self, im: Image) -> Image:
        if self.longside is None:
            return im
        if im.width >= im.height:
            width_new = self.longside
            if self.auto_shortside:
                wpercent = self.longside / float(im.width)
                hsize = int((float(im.height) * float(wpercent)))
                height_new = hsize
            else:
                if self.shortside is None:
                    return im
                height_new = self.shortside
        else:
            height_new = self.longside
            if self.auto_shortside:
                wpercent = self.longside / float(im.height)
                hsize = int((float(im.width) * float(wpercent)))
                width_new = hsize
            else:
                if self.shortside is None:
                    return im
                width_new = self.shortside
        return im.resize((width_new, height_new), self.resampling)

    def widget(self, parent):
        longside_frm = Frame(parent, padding=0)
        longside_frm.grid(row=0, column=0, sticky="w")
        Label(longside_frm, text="long side:").grid(row=0, column=0, sticky="w")
        int_entry_create(
            longside_frm,
            lambda: self.longside,
            lambda v: setattr(self, "longside", v),
            5,
        ).grid(row=0, column=1, sticky="w")
        Label(longside_frm, text="px").grid(row=0, column=2, sticky="w")
        shortside_frm = Frame(parent, padding=0)
        shortside_frm.grid(row=0, column=1, padx=(10, 0), sticky="w")
        # shortside_frm
        _shortside_frm = Frame(shortside_frm, padding=0)
        _shortside_frm.grid(row=0, column=0, padx=(10, 0), sticky="w")
        # _shortside_frm
        Label(_shortside_frm, text="short side:").grid(row=0, column=0, sticky="w")

        int_entry_create(
            _shortside_frm,
            lambda: self.shortside,
            lambda v: setattr(self, "shortside", v),
            5,
        ).grid(row=0, column=1, sticky="w")
        Label(_shortside_frm, text="px").grid(row=0, column=2, sticky="w")

        # _shortside_frm end
        def auto_shortside_setter(newv):
            self.auto_shortside = newv
            if newv:
                _shortside_frm.grid_remove()
            else:
                _shortside_frm.grid()

        bool_checkbox_create(
            shortside_frm,
            lambda: self.auto_shortside,
            auto_shortside_setter,
            "short side=auto",
        ).grid(row=0, column=1, sticky="w", padx=(10, 10))

        OptionMenu(
            parent,
            StringVar(),
            Resampling(self.resampling).name,
            *[x.name for x in Resampling if x.value > -1],
            command=lambda selection: setattr(
                self, "resampling", getattr(Resampling, "selection")
            ),
        ).grid(row=0, column=2)


class Crop(Transform):
    conf: int = None
    border: int = None

    def __call__(self, im: Image) -> Image:
        if self.border is None or self.conf is None:
            return im
        bg = PIL_new(im.mode, im.size, im.getpixel((0, 0)))
        diff = PIL_difference(im, bg)
        diff = PIL_add(diff, diff, 2.0, -self.conf)
        bbox = list(diff.getbbox())
        b = self.border
        bbox = [
            max(0, bbox[0] - b),
            max(0, bbox[1] - b),
            min(im.size[0], bbox[2] + b),
            min(im.size[1], bbox[3] + b),
        ]
        return im.crop(bbox)

    def widget(self, parent):
        Label(parent, text="border:").grid(row=0, column=0, sticky="w")
        int_entry_create(
            parent,
            lambda: self.border,
            lambda v: setattr(self, "border", v),
            5,
        ).grid(row=0, column=1, sticky="w")
        Label(parent, text="px").grid(row=0, column=2, sticky="w")
        Label(parent, text="conf:").grid(row=0, column=3, padx=(10, 0), sticky="w")
        iv = IntVar()
        iv.trace_add("write", lambda *args: setattr(self, "conf", iv.get()))
        scale = Scale(parent, orient=HORIZONTAL, variable=iv, from_=1, to=100)
        if self.conf is not None:
            scale.set(self.conf)
        scale.grid(row=0, column=4, padx=(10, 0), sticky="w")


TRANSFORM_CLS_NAME_TO_CLASS_OBJ: Dict[str, Type[Transform]] = dict(
    (x.__name__, x) for x in Transform.__subclasses__()
)
TRANSFORM_CLS_NAMES = list(TRANSFORM_CLS_NAME_TO_CLASS_OBJ.keys())


class ConfigEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Path):
            return {"__path__": str(o)}
        if isinstance(o, Transform):
            return {
                "__transform__": {
                    "name": o.__class__.__name__,
                    "attrs": dict(
                        (k, getattr(o, k, None)) for k in o.__annotations__.keys()
                    ),
                }
            }
        if isinstance(o, LinkedList):
            return {"__linkedlist__": [x for x in o]}
        return JSONEncoder.default(self, o)


def from_json(o):
    if "__path__" in o:
        return Path(o["__path__"])
    if "__transform__" in o:
        return TRANSFORM_CLS_NAME_TO_CLASS_OBJ[o["__transform__"]["name"]](
            **o["__transform__"]["attrs"]
        )
    if "__linkedlist__" in o:
        return LinkedList(o["__linkedlist__"])
    return o


class Config:
    theme: str = "radiance"
    font_family: str = "Courier New"
    font_size: int = 12
    transforms: LinkedList = LinkedList()

    def __init__(self, file: Path):
        self.__file = file
        if not file.exists():
            file.write_text("{}")
        config = (
            json_loads(file.read_text(), object_hook=from_json)
        )
        for name in dir(self):
            if not self.is_priv(name) and not callable(value := getattr(self, name)):
                config[name] = value
        self.__config = config

    def __getattr__(self, name: Any) -> Union[Any, None]:
        if callable(name) or self.is_priv(name):
            return self.__getattribute__(name)
        config = self.__config
        if name in config:
            return config[name]
        return None 

    def __setattr__(self, name: Any, value: Any) -> None:
        if not self.is_priv(name):
            self.__config[name] = value
        super(Config, self).__setattr__(name, value)

    def __contains__(self, item: Any) -> bool:
        return item in self.__config

    def save(self):
        dump = json_dumps(
            self.__config,
            cls=ConfigEncoder,
            indent=4,
        )
        self.__file.write_text(dump)

    def get_file(self):
        return self.__file

    def is_priv(self, name: str):
        return name.startswith(f"_{Config.__name__}__") or name.startswith("__")


class ToolTip:
    def __init__(self, widget, transforms: LinkedList):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.transforms = transforms

    def update_xy(self, x, y):
        if self.tipwindow:
            self.tipwindow.wm_geometry(
                f"{self.photo_img.width()}x{self.photo_img.height()}+{x}+{y}"
            )
            self.tipwindow.update()

    def showtip(self, img: ImageFile, x, y):
        im = self.transforms.propagate(img.src_path)
        self.photo_img = PhotoImage(im)
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"{self.photo_img.width()}x{self.photo_img.height()}+{x}+{y}")
        img_label = Label(tw, image=self.photo_img)
        label = Label(
            tw,
            text=f"{im.width}x{im.height}",  # str(img.src_path.relative_to(Path.cwd())),
            justify=LEFT,
            background="#ffffe0",
            relief=SOLID,
            borderwidth=1,
            font=("tahoma", "8", "normal"),
        )
        label.grid(row=0, column=0, sticky="nwe")
        img_label.grid(row=1, column=0, sticky="nswe")

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


if __name__ == "__main__":
    config = Config(Path("test.json"))
    a = Resize(config)
    b = Resize(config)
    a.longside = "a"
    print(a.longside, b.longside)
    config.save()
