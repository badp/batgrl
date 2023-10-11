"""
Base for graphic gadgets.
"""
from math import prod
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from ..colors import TRANSPARENT, AColor, ColorPair
from .gadget import (
    Anchor,
    Char,
    Easing,
    Gadget,
    Point,
    PosHint,
    PosHintDict,
    Region,
    Size,
    SizeHint,
    SizeHintDict,
    clamp,
    lerp,
    style_char,
    subscribable,
)
from .texture_tools import Interpolation

__all__ = [
    "Anchor",
    "Char",
    "Easing",
    "Graphics",
    "Interpolation",
    "Point",
    "PosHint",
    "PosHintDict",
    "Region",
    "Size",
    "SizeHint",
    "SizeHintDict",
    "clamp",
    "lerp",
    "style_char",
    "subscribable",
]


class Graphics(Gadget):
    """
    Base for graphic gadgets.

    Graphic gadgets are gadgets that are rendered entirely with the upper half block
    character, "▀". Graphic gadgets' color information is stored in a uint8 RGBA array,
    :attr:`texture`. Note that the height of :attr:`texture` is twice the height of the
    gadget.

    Parameters
    ----------
    default_color : AColor, default: AColor(0, 0, 0, 0)
        Default texture color.
    alpha : float, default: 1.0
        If gadget is transparent, the alpha channel of the underlying texture will be
        multiplied by this value. (0 <= alpha <= 1.0)
    interpolation : Interpolation, default: "linear"
        Interpolation used when gadget is resized.
    size : Size, default: Size(10, 10)
        Size of gadget.
    pos : Point, default: Point(0, 0)
        Position of upper-left corner in parent.
    size_hint : SizeHint | SizeHintDict | None, default: None
        Size as a proportion of parent's height and width.
    pos_hint : PosHint | PosHintDict | None , default: None
        Position as a proportion of parent's height and width.
    is_transparent : bool, default: True
        If true, gadget is rendered with alpha compositing; otherwise, alpha values are
        ignored.
    is_visible : bool, default: True
        Whether gadget is visible. Gadget will still receive input events if not
        visible.
    is_enabled : bool, default: True
        Whether gadget is enabled. A disabled gadget is not painted and doesn't receive
        input events.
    background_char : str | None, default: None
        The background character of the gadget if the gadget is not transparent.
        Character must be single unicode half-width grapheme.
    background_color_pair : ColorPair | None, default: None
        The background color pair of the gadget if the gadget is not transparent.

    Attributes
    ----------
    texture : NDArray[np.uint8]
        uint8 RGBA color array.
    default_color : AColor
        Default texture color.
    alpha : float
        Transparency of gadget if :attr:`is_transparent` is true.
    interpolation : Interpolation
        Interpolation used when gadget is resized.
    size : Size
        Size of gadget.
    height : int
        Height of gadget.
    rows : int
        Alias for :attr:`height`.
    width : int
        Width of gadget.
    columns : int
        Alias for :attr:`width`.
    pos : Point
        Position of upper-left corner.
    top : int
        Y-coordinate of top of gadget.
    y : int
        Y-coordinate of top of gadget.
    left : int
        X-coordinate of left side of gadget.
    x : int
        X-coordinate of left side of gadget.
    bottom : int
        Y-coordinate of bottom of gadget.
    right : int
        X-coordinate of right side of gadget.
    center : Point
        Position of center of gadget.
    absolute_pos : Point
        Absolute position on screen.
    size_hint : SizeHint
        Size as a proportion of parent's height and width.
    pos_hint : PosHint
        Position as a proportion of parent's height and width.
    background_char : str | None
        The background character of the gadget if the gadget is not transparent.
    background_color_pair : ColorPair | None
        Background color pair.
    parent : Gadget | None
        Parent gadget.
    children : list[Gadget]
        Children gadgets.
    is_transparent : bool
        True if gadget is transparent.
    is_visible : bool
        True if gadget is visible.
    is_enabled : bool
        True if gadget is enabled.
    root : Gadget | None
        If gadget is in gadget tree, return the root gadget.
    app : App
        The running app.

    Methods
    -------
    to_png(path: Path):
        Write :attr:`texture` to provided path as a `png` image.
    on_size():
        Called when gadget is resized.
    apply_hints():
        Apply size and pos hints.
    to_local(point: Point):
        Convert point in absolute coordinates to local coordinates.
    collides_point(point: Point):
        True if point collides with an uncovered portion of gadget.
    collides_gadget(other: Gadget):
        True if other is within gadget's bounding box.
    add_gadget(gadget: Gadget):
        Add a child gadget.
    add_gadgets(*gadgets: Gadget):
        Add multiple child gadgets.
    remove_gadget(gadget: Gadget):
        Remove a child gadget.
    pull_to_front():
        Move to end of gadget stack so gadget is drawn last.
    walk_from_root():
        Yield all descendents of the root gadget (preorder traversal).
    walk():
        Yield all descendents of this gadget (preorder traversal).
    walk_reverse():
        Yield all descendents of this gadget (reverse postorder traversal).
    ancestors():
        Yield all ancestors of this gadget.
    subscribe(source: Gadget, attr: str, action: Callable[[], None]):
        Subscribe to a gadget property.
    unsubscribe(source: Gadget, attr: str):
        Unsubscribe to a gadget property.
    on_key(key_event: KeyEvent):
        Handle key press event.
    on_mouse(mouse_event: MouseEvent):
        Handle mouse event.
    on_paste(paste_event: PasteEvent):
        Handle paste event.
    tween(
        duration: float = 1.0,
        easing: Easing = "linear",
        on_start: Callable[[], None] | None = None,
        on_progress: Callable[[], None] | None = None,
        on_complete: Callable[[], None] | None = None,
        **properties,
    ):
        Sequentially update gadget properties over time.
    on_add():
        Called after a gadget is added to gadget tree.
    on_remove():
        Called before gadget is removed from gadget tree.
    prolicide():
        Recursively remove all children.
    destroy():
        Destroy this gadget and all descendents.
    """

    def __init__(
        self,
        *,
        is_transparent: bool = True,
        default_color: AColor = TRANSPARENT,
        alpha: float = 1.0,
        interpolation: Interpolation = "linear",
        size=Size(10, 10),
        pos=Point(0, 0),
        size_hint: SizeHint | SizeHintDict | None = None,
        pos_hint: PosHint | PosHintDict | None = None,
        is_visible: bool = True,
        is_enabled: bool = True,
        background_char: str | None = None,
        background_color_pair: ColorPair | None = None,
    ):
        super().__init__(
            is_transparent=is_transparent,
            size=size,
            pos=pos,
            size_hint=size_hint,
            pos_hint=pos_hint,
            is_visible=is_visible,
            is_enabled=is_enabled,
            background_char=background_char,
            background_color_pair=background_color_pair,
        )

        self.default_color = default_color
        self.interpolation = interpolation
        self.alpha = alpha

        h, w = self.size
        self.texture = np.full(
            (2 * h, w, 4),
            default_color,
            dtype=np.uint8,
        )

    @property
    def alpha(self) -> float:
        """
        Transparency of gadget if :attr:`is_transparent` is true.
        """
        return self._alpha

    @alpha.setter
    @subscribable
    def alpha(self, alpha: float):
        self._alpha = clamp(float(alpha), 0.0, 1.0)

    def on_size(self):
        h, w = self._size

        self.texture = cv2.resize(
            self.texture,
            (w, 2 * h),
            interpolation=Interpolation._to_cv_enum[self.interpolation],
        )

    @property
    def interpolation(self) -> Interpolation:
        """
        Interpolation used when gadget is resized.
        """
        return self._interpolation

    @interpolation.setter
    def interpolation(self, interpolation: Interpolation):
        if interpolation not in Interpolation.__args__:
            raise TypeError(f"{interpolation} is not a valid interpolation type.")
        self._interpolation = interpolation

    def render(self, canvas: NDArray[Char], colors: NDArray[np.uint8]):
        texture = self.texture
        foreground = colors[..., :3]
        background = colors[..., 3:]

        abs_pos = self.absolute_pos
        if self.is_transparent:
            for rect in self.region.rects():
                dst = rect.to_slices()
                src_y, src_x = rect.to_slices(abs_pos)

                mask = canvas["char"][dst] != "▀"
                foreground[dst][mask] = background[dst][mask]

                even_rows = texture[2 * src_y.start : 2 * src_y.stop : 2, src_x]
                odd_rows = texture[2 * src_y.start + 1 : 2 * src_y.stop : 2, src_x]

                even_buffer = np.subtract(
                    even_rows[..., :3], foreground[dst], dtype=float
                )
                odd_buffer = np.subtract(
                    odd_rows[..., :3], background[dst], dtype=float
                )

                norm_alpha = (
                    prod(
                        ancestor.alpha
                        for ancestor in self.ancestors()
                        if isinstance(ancestor, Graphics)
                    )
                    * self.alpha
                    / 255
                )

                even_buffer *= even_rows[..., 3, None]
                even_buffer *= norm_alpha

                odd_buffer *= odd_rows[..., 3, None]
                odd_buffer *= norm_alpha

                np.add(
                    even_buffer, foreground[dst], out=foreground[dst], casting="unsafe"
                )
                np.add(
                    odd_buffer, background[dst], out=background[dst], casting="unsafe"
                )
                canvas[dst] = style_char("▀")
        else:
            for rect in self.region.rects():
                dst = rect.to_slices()
                src_y, src_x = rect.to_slices(abs_pos)
                even_rows = texture[2 * src_y.start : 2 * src_y.stop : 2, src_x]
                odd_rows = texture[2 * src_y.start + 1 : 2 * src_y.stop : 2, src_x]
                foreground[dst] = even_rows[..., :3]
                background[dst] = odd_rows[..., :3]
                canvas[dst] = style_char("▀")

    def to_png(self, path: Path):
        """
        Write :attr:`texture` to provided path as a `png` image.
        """
        BGRA = cv2.cvtColor(self.texture, cv2.COLOR_RGBA2BGRA)
        cv2.imwrite(str(path.absolute()), BGRA)
