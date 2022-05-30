import asyncio
from collections.abc import Callable, Sequence
from functools import wraps
from time import monotonic
from weakref import WeakKeyDictionary

import numpy as np

from .. import easings
from ..clamp import clamp
from ..colors import ColorPair
from ..data_structures import *
from ..io import KeyPressEvent, MouseEvent, PasteEvent
from .widget_data_structures import *

__all__ = (
    "emitter",
    "Anchor",
    "ColorPair",
    "Easing",
    "Point",
    "PosHint",
    "Size",
    "SizeHint",
    "Widget",
)

def emitter(method):
    """
    A decorator for widget property setters that will
    notify subscribers when the property is updated.
    """
    instances = WeakKeyDictionary()

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        method(self, *args, **kwargs)

        if subscribers := instances.get(self):
            for action in subscribers.values():
                action()

    wrapper.instances = instances

    return wrapper


class Widget:
    """
    Base class for creating widgets.

    Parameters
    ----------
    size : Size, default: Size(10, 10)
        Size of widget.
    pos : Point, default: Point(0, 0)
        Position of upper-left corner in parent.
    size_hint : SizeHint, default: SizeHint(None, None)
        Proportion of parent's height and width. Non-None values will have
        precedent over `size`.
    min_height : int | None, default: None
        Minimum height set due to size_hint. Ignored if corresponding size
        hint is None.
    max_height : int | None, default: None
        Maximum height set due to size_hint. Ignored if corresponding size
        hint is None.
    min_width : int | None, default: None
        Minimum width set due to size_hint. Ignored if corresponding size
        hint is None.
    max_width : int | None, default: None
        Maximum width set due to size_hint. Ignored if corresponding size
        hint is None.
    pos_hint : PosHint, default: PosHint(None, None)
        Position as a proportion of parent's height and width. Non-None values
        will have precedent over `pos`.
    anchor : Anchor, default: Anchor.TOP_LEFT
        Specifies which part of the widget is aligned with the `pos_hint`.
    is_transparent : bool, default: False
        If true, background_char and background_color_pair won't be painted.
    is_visible : bool, default: True
        If false, widget won't be painted, but still dispatched.
    is_enabled : bool, default: True
        If false, widget won't be painted or dispatched.
    background_char : str | None, default: None
        The background character of the widget if not `None` and if the widget
        is not transparent.
    background_color_pair : ColorPair | None, default: None
        The background color pair of the widget if not `None` and if the
        widget is not transparent.
    """
    def __init__(
        self,
        *,
        size=Size(10, 10),
        pos=Point(0, 0),
        size_hint: SizeHint=SizeHint(None, None),
        min_width: int | None=None,
        max_width: int | None=None,
        min_height: int | None=None,
        max_height: int | None=None,
        pos_hint: PosHint=PosHint(None, None),
        anchor=Anchor.TOP_LEFT,
        is_transparent: bool=False,
        is_visible: bool=True,
        is_enabled: bool=True,
        background_char: str | None=None,
        background_color_pair: ColorPair | None=None,
    ):
        self.parent: Widget | None = None
        self.children: list[Widget] = [ ]

        self._size = Size(*size)
        self._pos = Point(*pos)

        self._size_hint = size_hint
        self._min_height = min_height
        self._max_height = max_height
        self._min_width = min_width
        self._max_width = max_width

        self._pos_hint = pos_hint
        self._anchor = anchor

        self.background_color_pair = background_color_pair
        self.background_char = background_char

        self.is_transparent = is_transparent
        self.is_visible = is_visible
        self.is_enabled = is_enabled

    @property
    def size(self) -> Size:
        """
        Size of widget.
        """
        return self._size

    @size.setter
    @emitter
    def size(self, size: Size):
        h, w = size
        self._size = Size(clamp(h, 1, None), clamp(w, 1, None))

        self.on_size()

        for child in self.children:
            child.update_geometry()

    @property
    def height(self) -> int:
        """
        Height of widget.
        """
        return self._size[0]

    @height.setter
    def height(self, height: int):
        self.size = height, self.width

    rows = height

    @property
    def width(self) -> int:
        """
        Width of widget.
        """
        return self._size[1]

    @width.setter
    def width(self, width: int):
        self.size = self.height, width

    columns = width

    @property
    def pos(self) -> Point:
        """
        Position relative to parent.
        """
        return self._pos

    @pos.setter
    @emitter
    def pos(self, point: Point):
        self._pos = Point(*point)

    @property
    def top(self) -> int:
        return self._pos[0]

    @top.setter
    def top(self, top: int):
        self.pos = top, self.left

    y = top

    @property
    def left(self) -> int:
        return self._pos[1]

    @left.setter
    def left(self, left: int):
        self.pos = self.top, left

    x = left

    @property
    def bottom(self) -> int:
        """
        Bottom of widget in parent's reference frame.
        """
        return self.top + self.height

    @bottom.setter
    def bottom(self, value: int):
        self.top = value - self.height

    @property
    def right(self) -> int:
        """
        Right side of widget in parent's reference frame.
        """
        return self.left + self.width

    @right.setter
    def right(self, value: int):
        self.left = value - self.width

    @property
    def absolute_pos(self) -> Point:
        """
        Absolute position on screen.
        """
        y, x = self.parent.absolute_pos
        return Point(self.top + y, self.left + x)

    @property
    def center(self) -> Point:
        """
        The center of the widget in local coordinates.
        """
        return Point(self.height // 2, self.width // 2)

    @property
    def size_hint(self) -> SizeHint:
        """
        Widget's size as a proportion of its parent's size.
        """
        return self._size_hint

    @size_hint.setter
    @emitter
    def size_hint(self, size_hint: SizeHint):
        """
        Set widget's size as a proportion of its parent's size.
        Negative size hints will be clamped to 0.
        """
        h, w = size_hint

        self._size_hint = SizeHint(
            h if h is None else max(float(h), 0.0),
            w if w is None else max(float(w), 0.0),
        )

        if self.parent:
            self.update_geometry()

    @property
    def height_hint(self) -> float | None:
        """
        Widget's height as proportion of its parent's height.
        """
        return self._size_hint[0]

    @height_hint.setter
    def height_hint(self, height_hint: float | None):
        self.size_hint = height_hint, self.width_hint

    @property
    def width_hint(self) -> float | None:
        """
        Widget's width as proportion of its parent's width.
        """
        return self._size_hint[1]

    @width_hint.setter
    def width_hint(self, width_hint: float | None):
        self.size_hint = self.height_hint, width_hint

    @property
    def min_height(self) -> int | None:
        """
        The minimum height of widget set due to `size_hint`.
        """
        return self._min_height

    @min_height.setter
    @emitter
    def min_height(self, min_height: int | None):
        self._min_height = min_height
        if self.parent:
            self.update_geometry()

    @property
    def max_height(self) -> int | None:
        """
        The maximum height of widget set due to `size_hint`.
        """
        return self._max_height

    @max_height.setter
    @emitter
    def max_height(self, max_height: int | None):
        self._max_height = max_height
        if self.parent:
            self.update_geometry()

    @property
    def min_width(self) -> int | None:
        """
        The minimum width of widget set due to `size_hint`.
        """
        return self._min_width

    @min_width.setter
    @emitter
    def min_width(self, min_width: int | None):
        self._min_width = min_width
        if self.parent:
            self.update_geometry()

    @property
    def max_width(self) -> int | None:
        """
        The maximum width of widget set due to `size_hint`.
        """
        return self._max_width

    @max_width.setter
    @emitter
    def max_width(self, max_width: int | None):
        self._max_width = max_width
        if self.parent:
            self.update_geometry()

    @property
    def pos_hint(self) -> PosHint:
        """
        Widget's position as a proportion of its parent's size.
        """
        return self._pos_hint

    @pos_hint.setter
    @emitter
    def pos_hint(self, pos_hint: PosHint):
        h, w = pos_hint
        self._pos_hint = PosHint(
            h if h is None else float(h),
            w if w is None else float(w),
        )

        if self.parent:
            self.update_geometry()

    @property
    def y_hint(self) -> float | None:
        """
        Vertical position of widget as a proportion of its parent's height.
        """
        return self._pos_hint[0]

    @y_hint.setter
    def y_hint(self, y_hint: float | None):
        self.pos_hint = y_hint, self.x_hint

    @property
    def x_hint(self) -> float | None:
        """
        Horizontal position of widget as proportion of its parent's width.
        """
        return self._pos_hint[1]

    @x_hint.setter
    def x_hint(self, x_hint: float | None):
        self.pos_hint = self.y_hint, x_hint

    @property
    def anchor(self) -> Anchor:
        return self._anchor

    @anchor.setter
    @emitter
    def anchor(self, anchor: Anchor):
        self._anchor = Anchor(anchor)
        self.update_geometry()

    @property
    def background_char(self) -> str | None:
        return self._background_char

    @background_char.setter
    @emitter
    def background_char(self, background_char: str | None):
        match background_char:
            case None:
                self._background_char = background_char
            case str():
                self._background_char = background_char[:1] or None
            case _:
                raise ValueError("`background_char` must be `None` or a `str`")

    def on_size(self):
        """
        Called when widget is resized.
        """

    def update_geometry(self):
        """
        Update geometry due to a change in parent's size.
        """
        if self.parent is None:
            return

        h, w = self.parent.size

        h_hint, w_hint = self.size_hint
        if h_hint is not None or w_hint is not None:
            if h_hint is None:
                height = self.height
            else:
                height = clamp(round(h_hint * h), self.min_height, self.max_height)

            if w_hint is None:
                width = self.width
            else:
                width = clamp(round(w_hint * w), self.min_width, self.max_width)

            self.size = height, width

        y_hint, x_hint = self.pos_hint
        if y_hint is None and x_hint is None:
            return

        match self.anchor:
            case Anchor.TOP_LEFT:
                offset_top, offset_left = 0, 0
            case Anchor.TOP_RIGHT:
                offset_top, offset_left = 0, self.width
            case Anchor.BOTTOM_LEFT:
                offset_top, offset_left = self.height, 0
            case Anchor.BOTTOM_RIGHT:
                offset_top, offset_left = self.height, self.width
            case Anchor.CENTER:
                offset_top, offset_left = self.center
            case Anchor.TOP_CENTER:
                offset_top, offset_left = 0, self.center.x
            case Anchor.BOTTOM_CENTER:
                offset_top, offset_left = self.height, self.center.x
            case Anchor.LEFT_CENTER:
                offset_top, offset_left = self.center.y, 0
            case Anchor.RIGHT_CENTER:
                offset_top, offset_left = self.center.y, self.width

        if y_hint is not None:
            self.top = int(h * y_hint) - offset_top

        if x_hint is not None:
            self.left = int(w * x_hint) - offset_left

    @property
    def root(self):
        """
        Return the root widget if connected to widget tree.
        """
        return self.parent and self.parent.root

    @property
    def app(self):
        """
        The running app.
        """
        return self.root.app

    def to_local(self, point: Point) -> Point:
        """
        Convert point in absolute coordinates to local coordinates.
        """
        y, x = self.parent.to_local(point)
        return Point(y - self.top, x - self.left)

    def collides_point(self, point: Point) -> bool:
        """
        Return True if point is within widget's visible bounding box.
        """
        # These conditions are separated as they both require
        # recursive calls up the widget tree and we'd like to
        # escape as early as possible.
        if not self.parent.collides_point(point):
            return False

        y, x = self.to_local(point)
        return 0 <= y < self.height and 0 <= x < self.width

    def collides_widget(self, widget) -> bool:
        """
        Return True if some part of widget is within bounding box.
        """
        self_top, self_left = self.absolute_pos
        self_bottom = self_top + self.height
        self_right = self.left + self.width

        other_top, other_left = widget.absolute_pos
        other_bottom = other_top + widget.height
        other_right = other_left + widget.width

        return not (
            self_top >= other_bottom
            or other_top >= self_bottom
            or self_left >= other_right
            or other_left >= self_right
        )

    def add_widget(self, widget: "Widget"):
        """
        Add a child widget.
        """
        self.children.append(widget)
        widget.parent = self
        widget.update_geometry()

    def add_widgets(self, *widgets: "Widget"):
        """
        Add multiple child widgets.
        """
        if len(widgets) == 1 and not isinstance(widgets[0], Widget):
            # Assume item is an iterable of widgets.
            widgets = widgets[0]

        for widget in widgets:
            self.add_widget(widget)

    def remove_widget(self, widget):
        """
        Remove widget.
        """
        self.children.remove(widget)
        widget.parent = None

    def pull_to_front(self):
        """
        Move widget to end of widget stack so that it is drawn last.
        """
        parent = self.parent
        parent.remove_widget(self)
        parent.add_widget(self)

    def walk_from_root(self):
        """
        Yield all descendents of the root widget.
        """
        for child in self.root.children:
            yield child
            yield from child.walk()

    def walk(self):
        """
        Yield all descendents.
        """
        for child in self.children:
            yield child
            yield from child.walk()

    def subscribe(
        self,
        source: "Widget",
        attr: str,
        action: Callable[[], None],
    ):
        """
        Subscribe to a widget property.

        Parameters
        ----------
        source : Widget
            The source of the widget property.
        attr : str
            The name of the widget property.
        action : Callable[[], None]
            Called when the property is updated.
        """
        setter = getattr(type(source), attr).fset
        subscribers = setter.instances.setdefault(source, WeakKeyDictionary())
        subscribers[self] = action

    def unsubscribe(self, source: "Widget", attr: str) -> Callable[[], None] | None:
        """
        Unsubscribe to a widget event and return the callable that was subscribed
        to the event or `None` if subscription isn't found.
        """
        setter = getattr(type(source), attr).fset
        return setter.instances[source].pop(self, None)

    def dispatch_press(self, key_press_event: KeyPressEvent) -> bool | None:
        """
        Dispatch key press until handled. (A key press is handled if a handler returns True.)
        """
        return (
            any(
                widget.dispatch_press(key_press_event)
                for widget in reversed(self.children)
                if widget.is_enabled
            )
            or self.on_press(key_press_event)
        )

    def dispatch_click(self, mouse_event: MouseEvent) -> bool | None:
        """
        Dispatch mouse event until handled. (A mouse event is handled if a handler returns True.)
        """
        return (
            any(
                widget.dispatch_click(mouse_event)
                for widget in reversed(self.children)
                if widget.is_enabled
            )
            or self.on_click(mouse_event)
        )

    def dispatch_double_click(self, mouse_event: MouseEvent) -> bool | None:
        """
        Dispatch double-click mouse event until handled. (A mouse event is handled if a handler
        returns True.)
        """
        return (
            any(
                widget.dispatch_double_click(mouse_event)
                for widget in reversed(self.children)
                if widget.is_enabled
            )
            or self.on_double_click(mouse_event)
        )

    def dispatch_triple_click(self, mouse_event: MouseEvent) -> bool | None:
        """
        Dispatch triple-click mouse event until handled. (A mouse event is handled if a handler
        returns True.)
        """
        return (
            any(
                widget.dispatch_triple_click(mouse_event)
                for widget in reversed(self.children)
                if widget.is_enabled
            )
            or self.on_triple_click(mouse_event)
        )

    def dispatch_paste(self, paste_event: PasteEvent) -> bool | None:
        """
        Dispatch paste event until handled. (A paste event is handled if a handler returns True.)
        """
        return (
            any(
                widget.dispatch_paste(paste_event)
                for widget in reversed(self.children)
                if widget.is_enabled
            )
            or self.on_paste(paste_event)
        )

    def on_press(self, key_press_event: KeyPressEvent) -> bool | None:
        """
        Handle key press event. (Handled key presses should return True else False or None).
        """

    def on_click(self, mouse_event: MouseEvent) -> bool | None:
        """
        Handle mouse event. (Handled mouse events should return True else False or None).
        """

    def on_double_click(self, mouse_event: MouseEvent) -> bool | None:
        """
        Handle double-click mouse event. (Handled mouse events should return True else False or None).
        """

    def on_triple_click(self, mouse_event: MouseEvent) -> bool | None:
        """
        Handle triple-click mouse event. (Handled mouse events should return True else False or None).
        """

    def on_paste(self, paste_event: PasteEvent) -> bool | None:
        """
        Handle paste event. (Handled paste events should return True else False or None).
        """

    def render(self, canvas_view, colors_view, source: tuple[slice, slice]):
        """
        Paint widget and its children.
        """
        if not self.is_transparent:
            if self.background_char is not None:
                canvas_view[:] = self.background_char

            if self.background_color_pair is not None:
                colors_view[:] = self.background_color_pair

        self.render_children(source, canvas_view, colors_view)

    def render_children(self, destination: tuple[slice, slice], canvas_view, colors_view):
        for child in self.children:
            if child.is_visible and child.is_enabled:
                child.render_intersection(destination, canvas_view, colors_view)

    def render_intersection(self, destination: tuple[slice, slice], canvas_view, colors_view):
        """
        Render the intersection of destination with widget.
        """
        vert_slice, hori_slice = destination
        t = vert_slice.start
        h = vert_slice.stop - t
        l = hori_slice.start
        w = hori_slice.stop - l

        wt = self.top - t
        wb = self.bottom - t
        wl = self.left - l
        wr = self.right - l

        if (
            wt >= h
            or wb < 0
            or wl >= w
            or wr < 0
        ):
            # widget doesn't intersect.
            return

        ####################################################################
        # Four cases for top / bottom of widget:                           #
        #     1) widget top is off-screen and widget bottom is off-screen. #
        #               +--------+                                         #
        #            +--| widget |------------+                            #
        #            |  |        |   dest     |                            #
        #            +--|        |------------+                            #
        #               +--------+                                         #
        #     2) widget top is off-screen and widget bottom is on-screen.  #
        #               +--------+                                         #
        #            +--| widget |------------+                            #
        #            |  +--------+   dest     |                            #
        #            +------------------------+                            #
        #                                                                  #
        #     3) widget top is on-screen and widget bottom is off-screen.  #
        #            +------------------------+                            #
        #            |  +--------+   dest     |                            #
        #            +--| widget |------------+                            #
        #               +--------+                                         #
        #                                                                  #
        #     4) widget top is on-screen and widget bottom is on-screen.   #
        #            +------------------------+                            #
        #            |  +--------+            |                            #
        #            |  | widget |   dest     |                            #
        #            |  +--------+            |                            #
        #            +------------------------+                            #
        #                                                                  #
        # Similarly, by symmetry, four cases for left / right of widget.   #
        ####################################################################

        # st, dt, sb, db, sl, dl, sr, dr stand for source_top, destination_top, source_bottom,
        # destination_bottom, source_left, destination_left, source_right, destination_right.
        if wt < 0:
            st = -wt
            dt = 0

            if wb >= h:
                sb = h + st
                db = h
            else:
                sb = self.height
                db = wb
        else:
            st =  0
            dt = wt

            if wb >= h:
                sb = h - dt
                db = h
            else:
                sb = self.height
                db = wb

        if wl < 0:
            sl = -wl
            dl = 0

            if wr >= w:
                sr = w + sl
                dr = w
            else:
                sr = self.width
                dr = wr
        else:
            sl = 0
            dl = wl

            if wr >= w:
                sr = w - dl
                dr = w
            else:
                sr = self.width
                dr = wr

        dest_slice = np.s_[dt: db, dl: dr]
        self.render(canvas_view[dest_slice], colors_view[dest_slice], np.s_[st: sb, sl: sr])

    async def tween(
        self,
        *,
        duration: float=1.0,
        easing: Easing=Easing.LINEAR,
        on_start: Callable | None=None,
        on_progress: Callable | None=None,
        on_complete: Callable | None=None,
        **properties: dict[str, int | float | Sequence[int] | Sequence[float | None]],
    ):
        """
        Coroutine that sequentially updates widget properties over a duration (in seconds).
        Tweening (short for inbetweening) is the process of generating images between
        keyframes in animation.

        Parameters
        ----------
        duration : float, default: 1.0
            The duration of the tween in seconds.
        easing : Easing, default: Easing.LINEAR
            The easing used for tweening.
        on_start : Callable | None, default: None
            Called when tween starts.
        on_progress : Callable | None, default: None
            Called when tween updates.
        on_complete : Callable | None, default: None
            Called when tween completes.
        **properties : dict[str, int | float | Sequence[int] | Sequence[float | None]]
            Widget properties' target values. E.g., to smoothly tween a widget's position
            to (5, 10) over 2.5 seconds, specify the `pos` property as a keyword-argument:
            `await widget.tween(pos=(5, 10), duration=2.5, easing=Easing.OUT_BOUNCE)`

        Warnings
        --------
        Running several tweens on the same properties concurrently will probably result in unexpected
        behavior. `tween` won't work for ndarray types such as `canvas`, `colors`, or `texture`.
        If tweening size or pos hints, make sure the relevant hints aren't `None` to start.
        """
        end_time = monotonic() + duration
        start_values = tuple(getattr(self, attr) for attr in properties)
        easing_function = getattr(easings, easing)

        if on_start:
            on_start()

        while (current_time := monotonic()) < end_time:
            p = easing_function(1 - (end_time - current_time) / duration)

            for start_value, (prop, target) in zip(start_values, properties.items()):
                match start_value:
                    case (int(), *_):  # Sequence[int]
                        value = tuple((
                            round(easings.lerp(i, j, p))
                            for i, j in zip(start_value, target)
                        ))
                    case int():
                        value = round(easings.lerp(start_value, target, p))
                    case (float() | None, *_):  # Sequence[float | None]
                        value = tuple((
                            None if i is None else easings.lerp(i, j, p)
                            for i, j in zip(start_value, target)
                        ))
                    case float():
                        value = easings.lerp(start_value, target, p)

                setattr(self, prop, value)

            if on_progress:
                on_progress()

            await asyncio.sleep(0)

        for prop, target in properties.items():
            setattr(self, prop, target)

        if on_complete:
            on_complete()
