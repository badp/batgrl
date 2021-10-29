import asyncio
from abc import ABC, abstractmethod
from contextlib import contextmanager

from .colors import BLACK_ON_BLACK
from .io import create_io, Mods, KeyPressEvent, PasteEvent, MouseEvent, Key
from .widgets._root import _Root

FLUSH_TIMEOUT        = 0.05  # Seconds before we flush an escape character in the input queue.
RESIZE_POLL_INTERVAL = 0.5   # Seconds between polling for resize events.
RENDER_INTERVAL      = 0     # Seconds between screen renders.


class App(ABC):
    """
    Base for creating terminal applications.

    Parameters
    ----------
    exit_key : KeyPressEvent | None, default: KeyPressEvent.ESCAPE
        Quit the app when this key is pressed.
    default_char : str, default: " "
        Default background character for root widget.
    default_color_pair : ColorPair, default: BLACK_ON_BLACK
        Default background color pair for root widget.
    title : str | None, default: None
        Set terminal title (if supported).
    """
    def __init__(
        self,
        *,
        exit_key=KeyPressEvent.ESCAPE,
        default_char=" ",
        default_color_pair=BLACK_ON_BLACK,
        title=None
    ):
        self.exit_key = exit_key
        self.default_char = default_char
        self.default_color_pair = default_color_pair
        self.title = title

    @abstractmethod
    async def on_start(self):
        """
        Coroutine scheduled when app is run.
        """

    def run(self):
        """
        Run the app.
        """
        try:
            asyncio.run(self._run_async())
        except asyncio.CancelledError:
            pass

    def exit(self):
        for task in asyncio.all_tasks():
            task.cancel()

    async def _run_async(self):
        """
        Build environment, create root, and schedule app-specific tasks.
        """
        with create_environment(self.title) as (env_out, env_in):
            self.root = root = _Root(
                app=self,
                env_out=env_out,
                default_char=self.default_char,
                default_color_pair=self.default_color_pair,
            )
            dispatch_press = root.dispatch_press
            dispatch_click = root.dispatch_click
            dispatch_paste = root.dispatch_paste

            loop = asyncio.get_event_loop()

            def read_from_input():
                """
                Read and process input.
                """
                for key in env_in.read_keys():
                    match key:
                        case self.exit_key:
                            return self.exit()
                        case MouseEvent():
                            dispatch_click(key)
                        case PasteEvent():
                            dispatch_paste(key)
                        case _:
                            dispatch_press(key)

            async def poll_size():
                """
                Poll terminal size every `RESIZE_POLL_INTERVAL` seconds.
                """
                size = env_out.get_size()
                resize = root.resize

                while True:
                    await asyncio.sleep(RESIZE_POLL_INTERVAL)

                    new_size = env_out.get_size()
                    if size != new_size:
                        resize(new_size)
                        size = new_size

            async def auto_render():
                """
                Render screen every `RENDER_INTERVAL` seconds.
                """
                render = root.render

                while True:
                    await asyncio.sleep(RENDER_INTERVAL)
                    render()

            with env_in.raw_mode(), env_in.attach(read_from_input):
                await asyncio.gather(
                    poll_size(),
                    auto_render(),
                    self.on_start(),
                )


@contextmanager
def create_environment(title):
    """
    Setup and return input and output.
    """
    env_in, env_out = create_io()

    env_out.enable_mouse_support()
    env_out.enable_bracketed_paste()
    env_out.enter_alternate_screen()
    if title is not None:
        env_out.set_title(title)
    env_out.flush()

    try:
        yield env_out, env_in

    finally:
        env_out.quit_alternate_screen()
        env_out.reset_attributes()
        env_out.disable_mouse_support()
        env_out.disable_bracketed_paste()
        env_out.show_cursor()
        env_out.flush()
        env_out.restore_console()
