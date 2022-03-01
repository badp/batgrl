
from ..colors import ColorPair, AColor
from .behaviors.focus_behavior import FocusBehavior
from .behaviors.grabbable_behavior import GrabbableBehavior
from .behaviors.grab_resize_behavior import GrabResizeBehavior
from .behaviors.themable import Themable
from .graphic_widget import GraphicWidget
from .text_widget import TextWidget
from .widget_base import WidgetBase, Size, Anchor


class _TitleBar(GrabbableBehavior, TextWidget):
    def __init__(self, title="", **kwargs):
        super().__init__(disable_ptf=True, **kwargs)

        self._label = TextWidget(size=(1, len(title)), pos_hint=(None, .5), anchor=Anchor.TOP_CENTER)
        self._label.add_text(title)
        self.add_widget(self._label)

    def grab(self, mouse_event):
        self.parent.pull_to_front()
        super().grab(mouse_event)

    def grab_update(self, mouse_event):
        self.parent.top += self.mouse_dy
        self.parent.left += self.mouse_dx


class _Border(TextWidget):
    def resize(self, size: Size):
        super().resize(size)
        self.canvas[:] = " "
        self.canvas[[0, -1]] = self.canvas[:, [0, 1, -2, -1]] = "█"


class Window(Themable, FocusBehavior, GrabResizeBehavior, WidgetBase):
    """
    A movable, resizable window widget.

    Parameters
    ----------
    title : str, default: ""
        Title of window.
    """
    def __init__(self, title="", **kwargs):
        super().__init__(**kwargs)

        self._border = _Border(is_transparent=True)
        self._titlebar = _TitleBar(title=title, pos=(1, 2))
        self._view = GraphicWidget(pos=(2, 2), is_transparent=False)
        self._border.parent = self._titlebar.parent = self._view.parent = self

        self.children = [self._titlebar, self._view]

        self.update_theme()
        self.resize(self.size)

    def update_theme(self):
        ct = self.color_theme

        view_background = AColor(*ct.primary_bg_light, 255)
        self._view.default_color = view_background
        self._view.texture[:] = view_background

        if self.is_focused:
            bg = self.color_theme.secondary_bg
        else:
            bg = self.color_theme.primary_bg

        border_color = ColorPair.from_colors(bg, bg)
        self._border.default_color_pair = border_color
        self._border.colors[:] = border_color

        title_bar_color_pair = ColorPair.from_colors(ct.secondary_bg, ct.primary_bg_dark)
        self._titlebar.default_color_pair = title_bar_color_pair
        self._titlebar.colors[:] = title_bar_color_pair
        self._titlebar._label.default_color_pair = title_bar_color_pair
        self._titlebar._label.colors[:] = title_bar_color_pair

    def on_focus(self):
        self.update_theme()

    def on_blur(self):
        self.update_theme()

    def resize(self, size: Size):
        h, w = size
        self._size = Size(h, w)

        self._border.resize(size)
        self._titlebar.resize((1, w - 4))
        self._view.resize((h - 3, w - 4))

    def render(self, canvas_view, colors_view, source: tuple[slice, slice]):
        self._border.render_intersection(source, canvas_view, colors_view)
        self._titlebar.render_intersection(source, canvas_view, colors_view)
        self._view.render_intersection(source, canvas_view, colors_view)

    def add_widget(self, widget):
        self._view.add_widget(widget)

    def remove_widget(self, widget):
        self._view.remove_widget(widget)
