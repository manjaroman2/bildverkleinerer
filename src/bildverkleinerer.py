build_date="2024-02-18 13:47:44"
from typing import *
from os import cpu_count
from pathlib import Path
from queue import Queue, Empty
from traceback import format_exc
from sys import platform as sys_platform 
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor

from tkinter import Text, INSERT, END, NORMAL, DISABLED, Toplevel, StringVar
from tkinter.ttk import Label, Style, OptionMenu, Frame, Button
from tkinter.filedialog import askdirectory
from tkinter.font import nametofont, Font
from ttkthemes import ThemedTk

from utils import (
    center_window,
    get_curr_screen_geometry,
    LogLevel,
    ImageFile,
    ToolTip,
    TRANSFORM_CLS_NAMES,
    TRANSFORM_CLS_NAME_TO_CLASS_OBJ,
    Transform,
    run_in_thread,
    Config,
)
from common import get_datadir


screen_width, screen_height = get_curr_screen_geometry()
config = Config(get_datadir("bildverkleinerer") / "config.json")
main_root = ThemedTk(theme=config.theme)
nametofont("TkDefaultFont").configure(family=config.font_family, size=config.font_size)
nametofont("TkTextFont").configure(family=config.font_family, size=config.font_size)
nametofont("TkFixedFont").configure(family=config.font_family, size=config.font_size)
font_text_big = Font(name="TkTextFontBigger")
font_text_big.configure(family=config.font_family, size=config.font_size + 4)

# ----- :END:CONFIG -----

# :start:log_root
log_root = Toplevel(main_root)
log_text = Text(log_root, state=DISABLED)
log_text.grid()
log_hidden = True
log_root_center = None


def log_toggle():
    global log_hidden
    log_hidden = not log_hidden
    if log_hidden:
        log_root.withdraw()
    else:
        log_root_center()
        log_root.deiconify()


def print_log(*args, level: LogLevel = LogLevel.MSG):
    log_text.configure(state=NORMAL)
    log_text.insert(END, f"{' '.join(str(x) for x in args)}\n")
    log_text.configure(state=DISABLED)
    log_text.see(END)


log_root.protocol("WM_DELETE_WINDOW", log_toggle)
# :end:log_root

# :start:settings_root
settings_root = Toplevel(main_root)
Label(settings_root, text="theme:").grid(row=0, column=0)


def theme_on_change(selection):
    config.theme = selection
    Style().theme_use(config.theme)
    main_root.update_idletasks()
    main_root.geometry("")
    log_root.update_idletasks()
    log_root.geometry("")
    settings_root.update_idletasks()
    settings_root.geometry("")


settings_theme = OptionMenu(
    settings_root,
    StringVar(value=config.theme),
    config.theme,
    *sorted(main_root.get_themes()),
    command=theme_on_change,
)
# theme.trace_add("write", theme_on_change)
settings_theme.grid(row=0, column=1)
settings_hidden = True
settings_root_center = None


def settings_toggle():
    global settings_hidden
    settings_hidden = not settings_hidden
    if settings_hidden:
        settings_root.withdraw()
    else:
        settings_root_center()
        settings_root.deiconify()


settings_root.protocol("WM_DELETE_WINDOW", settings_toggle)
# :end:settings_root


# :start:main_root_frm
def main_root_delete_win():
    config.save()
    main_root.destroy()


main_root.protocol("WM_DELETE_WINDOW", main_root_delete_win)
main_root_frm = Frame(main_root, padding=10)
main_root_frm.grid()
main_root_frm.grid_columnconfigure(0, weight=1)

images: List[ImageFile] = []
text_images: Text = Text(main_root_frm, wrap="none")
text_images_tooltip_shown: Tuple[ImageFile, int, int] = None
text_images_tooltip = ToolTip(text_images, config.transforms)
text_images.tag_add("hovered", 1.0, 1.0)
text_images.tag_config("hovered", font=font_text_big)


def text_images_motion(event):
    def _wrapper():
        for img in images:
            if text_images.compare(
                f"@{event.x},{event.y}", ">", f"{img.startidx}"
            ) and text_images.compare(f"@{event.x},{event.y}", "<", f"{img.endidx}"):
                return (img, event.x + 20, event.y)

    global text_images_tooltip_shown
    is_over = _wrapper()
    if text_images_tooltip_shown is None:
        if is_over is not None:
            text_images_tooltip_shown = is_over
            img, x, y = text_images_tooltip_shown
            text_images.tag_add("hovered", img.startidx, img.endidx)

            text_images_tooltip.showtip(
                img, text_images.winfo_rootx() + x, text_images.winfo_rooty() + y
            )
    else:
        if is_over is not None:
            if text_images_tooltip_shown[0] != is_over[0]:
                text_images_tooltip.hidetip()
                text_images.tag_remove(
                    "hovered",
                    text_images_tooltip_shown[0].startidx,
                    text_images_tooltip_shown[0].endidx,
                )
                text_images_tooltip_shown = is_over
                img, x, y = text_images_tooltip_shown
                text_images_tooltip.showtip(
                    img, text_images.winfo_rootx() + x, text_images.winfo_rooty() + y
                )
                text_images.tag_add("hovered", img.startidx, img.endidx)
            else:
                text_images_tooltip_shown = is_over
                img, x, y = is_over
                text_images_tooltip.update_xy(
                    text_images.winfo_rootx() + x, text_images.winfo_rooty() + y
                )
        else:
            text_images.tag_remove(
                "hovered",
                text_images_tooltip_shown[0].startidx,
                text_images_tooltip_shown[0].endidx,
            )
            text_images_tooltip_shown = None
            text_images_tooltip.hidetip()


def text_images_populate():
    file_path: Path = config.indir
    i = 0
    images.clear()
    text_images.configure(state=NORMAL)
    text_images.delete(1.0, END)
    text_images.insert(END, f"----- ")
    idx = text_images.index(INSERT)
    text_images.insert(END, f"{i:4} images ----- \n")
    text_images.insert(END, f"{'Resolution':11} File\n")
    for x in file_path.glob("**/*"):
        if x.suffix in (".jpg", ".png", "jpeg"):
            i += 1
            img = ImageFile(x, x.relative_to(file_path))
            img.add_text(text_images, END)
            images.append(img)
    a, b = idx.split(".")
    text_images.delete(idx, f"{a}.{int(b)+4}")
    text_images.insert(idx, f"{i:4}")
    text_images.configure(state=DISABLED)


def _start_conversion():
    text_images.configure(state=NORMAL)
    text_images.delete(images[-1].endidx, END)
    text_images.configure(state=DISABLED)

    outdir = config.outdir

    text_images.tag_add("processing", 1.0, 1.0)
    text_images.tag_config("processing", background="yellow")
    text_images.tag_add("done", 1.0, 1.0)
    text_images.tag_config("done", background="green")

    def _wrapper(img_file):
        gui_queue.put_nowait(
            lambda: text_images.tag_add(
                "processing", img_file.startidx, img_file.endidx
            )
        )
        gui_queue.put_nowait(lambda: text_images.see(img_file.endidx))

        im = config.transforms.propagate(img_file.src_path)
        im.save(outdir / img_file.src_path.name)

        gui_queue.put_nowait(
            lambda: text_images.tag_remove(
                "processing", img_file.startidx, img_file.endidx
            )
        )
        gui_queue.put_nowait(main_root.update)
        gui_queue.put(
            lambda: print_log(
                f"{img_file.src_path.name}:{img_file.res}->{im.width}x{im.width}"
            )
        )

    def _wrapper2():
        with ThreadPoolExecutor(max_workers=cpu_count() - 1) as executor:
            futures = [executor.submit(_wrapper, img_file) for img_file in images]
            for future in as_completed(futures):
                pass

    def handle_return(_):
        def _wrap():
            text_images.tag_remove("processing", 1.0, END)
            text_images.configure(state=NORMAL)
            text_images.delete(images[-1].endidx, END)
            text_images.insert(END, f"\nDone converting {len(images)} files")
            text_images.configure(state=DISABLED)
            text_images.tag_add("done", images[-1].endidx, END)
            text_images.see(END)
            main_root.update()
            main_root.after(5000, lambda: text_images.tag_delete("done"))

        gui_queue.put(_wrap)

    run_in_thread(_wrapper2, handle_return)


def strech_frame(frm, cols):
    for i in range(cols):
        frm.grid_columnconfigure(i, weight=1)
    frm.grid_rowconfigure(0, weight=1)


def rows_create():
    row = 0

    def new_row():
        nonlocal row
        row_frm = Frame(main_root_frm, padding=0)
        row_frm.grid(row=row, column=0, sticky="we")
        row += 1
        return row_frm

    row0_frm = new_row()
    strech_frame(row0_frm, 6)

    def row0_create():
        # row0_frm
        def start_conversion():
            try:
                _start_conversion()
            except Exception as e:
                print_log(format_exc())
                if log_hidden:
                    log_toggle()

        button_start = Button(row0_frm, text="Start", command=start_conversion)
        if config.indir is None or config.outdir is None:
            button_start.configure(state=DISABLED)
        button_start.grid(row=0, column=5, sticky="e")

        def select_indir_dialog():
            if path := askdirectory():
                config.indir = Path(path)
                text_images_populate()
                indir_button.configure(text=str(config.indir))
                if config.outdir is not None:
                    button_start.configure(state=NORMAL)
                main_root.update_idletasks()
                main_root.geometry("")

        def select_outdir_dialog():
            if path := askdirectory():
                config.outdir = Path(path)
                outdir_button.configure(text=str(config.outdir))
                if config.indir is not None:
                    button_start.configure(state=NORMAL)
                main_root.update_idletasks()
                main_root.geometry("")

        indir_button = Button(
            row0_frm, text="Select input directory", command=select_indir_dialog
        )
        indir_button.grid(row=0, column=0, columnspan=2, sticky="w")
        if v := config.indir:
            indir_button.configure(text=str(v))
            text_images_populate()

        Label(row0_frm, text=">>").grid(row=0, column=2, sticky="w")

        outdir_button = Button(
            row0_frm, text="Select output directory", command=select_outdir_dialog
        )
        outdir_button.grid(row=0, column=3, columnspan=2, sticky="w")
        if config.outdir is not None:
            outdir_button.config(text=str(config.outdir))

        # row0_frm end

    row1_frm = new_row()
    strech_frame(row1_frm, 1)

    def row1_create():
        def transform_row_create(parent, transform: Transform = None):
            row_outer_frm = Frame(parent, padding=0, borderwidth=1, relief="solid")
            strech_frame(row_outer_frm, 2)
            row_inner_frm = Frame(row_outer_frm, padding=0)
            row_inner_frm.grid(row=0, column=0, sticky="w")

            def transform_add(selection):
                nonlocal transform
                if transform is not None:
                    if transform.__class__.__name__ == selection:
                        return
                    row_inner_frm.update_idletasks()
                    for widget in row_inner_frm.winfo_children():
                        widget.destroy()
                    new_transform = TRANSFORM_CLS_NAME_TO_CLASS_OBJ[selection]()
                    config.transforms.replace_node(transform, new_transform)
                    transform = new_transform
                    transform.widget(row_inner_frm)
                    transform._outerparent = row_outer_frm
                    return transform
                transform = TRANSFORM_CLS_NAME_TO_CLASS_OBJ[selection]()
                config.transforms.add_last(transform)
                transform.widget(row_inner_frm)
                transform._outerparent = row_outer_frm
                return transform

            if transform is not None:
                transform.widget(row_inner_frm)
                transform._outerparent = row_outer_frm
            else:
                transform = transform_add(TRANSFORM_CLS_NAMES[0])

            print(config.transforms.index(transform))
            row_outer_frm.grid(
                row=config.transforms.index(transform), column=0, sticky="we"
            )
            select_transform_menu = OptionMenu(
                row_outer_frm,
                StringVar(),
                transform.__class__.__name__,
                *TRANSFORM_CLS_NAMES,
                command=transform_add,
            )
            select_transform_menu.grid(row=0, column=1, sticky="e")

            def delete_transform():
                config.transforms.remove_node(transform)
                row_outer_frm.destroy()
                main_root.update_idletasks()
                main_root.geometry("")

            Button(row_outer_frm, text="X", command=delete_transform).grid(
                row=0, column=2
            )

            def move_up(*args):
                if config.transforms.move_up(transform):
                    this_idx = config.transforms.index(transform)
                    transform._outerparent.grid_remove()
                    transform._outerparent.grid(
                        row=this_idx, column=0, sticky="we"
                    )
                    transform._next._outerparent.grid_remove()
                    transform._next._outerparent.grid(
                        row=this_idx + 1, column=0, sticky="we"
                    )

            def move_down(*args):
                if (prev_transform := config.transforms.move_down(transform)) is not None:
                    this_idx = config.transforms.index(transform)
                    transform._outerparent.grid_remove()
                    transform._outerparent.grid(
                        row=this_idx, column=0, sticky="we"
                    )
                    prev_transform._outerparent.grid_remove()
                    prev_transform._outerparent.grid(
                        row=this_idx - 1, column=0, sticky="we"
                    )

            if sys_platform == "win32" or sys_platform == "darwin":
                def mouse_wheel(event):
                    if event.delta > 0:
                        move_up()
                    elif event.delta < 0:
                        move_down()
                row_outer_frm.bind("<MouseWheel>", mouse_wheel)
            else:
                row_outer_frm.bind("<Button-4>", move_up)
                row_outer_frm.bind("<Button-5>", move_down)

        for transform in config.transforms:
            transform_row_create(row1_frm, transform)

        def show_transform_selection():
            # add_transform_btn.grid_remove()
            transform_row_create(row1_frm)
            add_transform_btn.grid(row=len(config.transforms) + 1, column=0)
            main_root.update_idletasks()
            main_root.geometry("")

        add_transform_btn = Button(
            row1_frm, text="Add transform", command=show_transform_selection
        )
        add_transform_btn.grid(row=len(config.transforms) + 1, column=0)

    # row 2 main_root_frm
    def row2_create():
        text_images.config(state=DISABLED)
        text_images.config(borderwidth=2, relief="solid")
        text_images.grid(row=2, column=0)

    # row 3
    def row3_create():
        footer_frm = Frame(main_root_frm, padding=0)
        footer_frm.grid(row=3, column=0, sticky="we")
        strech_frame(footer_frm, 2)
        Label(footer_frm, text=f"build:{build_date}").grid(row=0, column=0, sticky="we")

        Button(footer_frm, text="Settings", command=settings_toggle).grid(
            row=0, column=1, sticky="e"
        )
        Button(footer_frm, text="Log", command=log_toggle).grid(
            row=0, column=2, sticky="e"
        )

    row0_create()
    row1_create()
    row2_create()
    row3_create()


rows_create()
text_images.bind("<Motion>", text_images_motion)

gui_queue = Queue()

main_root.update_idletasks()
root_width = main_root.winfo_width()
root_height = main_root.winfo_height()
log_root.update_idletasks()
log_root_width = log_root.winfo_width()
log_root_height = log_root.winfo_height()
log_root_center = lambda: center_window(
    log_root,
    screen_width,
    screen_height,
    xoffset=int(root_width / 2 + log_root_width / 2),
    yoffset=int(-root_height / 2 + log_root_height / 2),
)
settings_root.update_idletasks()
settings_root_width = settings_root.winfo_width()
settings_root_height = settings_root.winfo_height()
settings_root_center = lambda: center_window(
    settings_root,
    screen_width,
    screen_height,
    xoffset=int(-root_width / 2 - settings_root_width / 2),
    yoffset=int(-root_height / 2 + settings_root_height / 2),
)
center_window(main_root, screen_width, screen_height, width=root_width)
log_root.withdraw()
settings_root.withdraw()


def gui_update(delay=100):
    while True:
        try:
            fn = gui_queue.get_nowait()
        except Empty:
            break
        fn()
    main_root.after(delay, gui_update, (delay,))

main_root.resizable(False, False)

print(str(config.get_file()))
print_log(str(config.get_file()))
gui_update()
main_root.mainloop()
