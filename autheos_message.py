#!/usr/bin/env python3
import argparse
import ctypes.util
import os
import re
import sys

def _find_gtk4_layer_shell_library() -> str | None:
    candidates: list[str] = []

    detected = ctypes.util.find_library("gtk4-layer-shell")
    if detected:
        candidates.append(detected)

    candidates.extend(
        [
            "libgtk4-layer-shell.so.0",
            "libgtk4-layer-shell.so",
            "/usr/lib/libgtk4-layer-shell.so.0",
            "/usr/lib/libgtk4-layer-shell.so",
            "/usr/lib64/libgtk4-layer-shell.so.0",
            "/usr/lib64/libgtk4-layer-shell.so",
        ]
    )

    for candidate in candidates:
        if os.path.isabs(candidate):
            if os.path.exists(candidate):
                return candidate
            continue
        return candidate
    return None


def _ensure_layer_shell_preloaded() -> None:
    if __name__ != "__main__":
        return
    if os.environ.get("HYPR_MESSAGE_PRELOAD_DONE") == "1":
        return
    if os.environ.get("HYPR_MESSAGE_DISABLE_PRELOAD") == "1":
        return

    current_preload = os.environ.get("LD_PRELOAD", "")
    if "gtk4-layer-shell" in current_preload:
        return

    library = _find_gtk4_layer_shell_library()
    if not library:
        return

    env = os.environ.copy()
    env["LD_PRELOAD"] = f"{library} {current_preload}".strip()
    env["HYPR_MESSAGE_PRELOAD_DONE"] = "1"
    os.execvpe(sys.executable, [sys.executable, *sys.argv], env)


_ensure_layer_shell_preloaded()

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk

try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell
except (ImportError, ValueError):
    Gtk4LayerShell = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show an animated message centered on a Hyprland screen."
    )
    parser.add_argument("message", help="Text message to display.")
    parser.add_argument(
        "--mode",
        choices=("char", "word"),
        default="char",
        help="Animation mode: character-by-character or word-by-word.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=15.0,
        help="Animation speed in tokens per second.",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=72,
        help="Font size in pixels.",
    )
    parser.add_argument(
        "--color",
        default="#ffffff",
        help="Text color (CSS color format).",
    )
    parser.add_argument(
        "--background",
        default="rgba(0, 0, 0, 0.0)",
        help="Background color (CSS color format).",
    )
    parser.add_argument(
        "--exit-after",
        type=float,
        default=1.0,
        help="Auto-close after N seconds once animation is done (0 disables).",
    )
    parser.add_argument(
        "--reveal-position",
        choices=("left-to-center", "center", "left"),
        default="left-to-center",
        help=(
            "How text appears while animating: "
            "'left-to-center' (default), 'center', or 'left'."
        ),
    )
    parser.add_argument(
        "--all-monitors",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show one message window on each monitor (default: enabled).",
    )
    return parser.parse_args()


def tokenize(message: str, mode: str) -> list[str]:
    if mode == "char":
        return list(message)
    return re.findall(r"\S+\s*", message)


class MessageWindow(Gtk.ApplicationWindow):
    def __init__(
        self,
        app: Gtk.Application,
        args: argparse.Namespace,
        monitor: Gdk.Monitor | None = None,
    ) -> None:
        super().__init__(application=app, title="Hypr Message")
        self.args = args
        self.tokens = tokenize(args.message, args.mode)
        self.index = 0
        self.current_text = ""
        self.exit_scheduled = False
        self.layer_shell_enabled = False

        self.set_decorated(False)
        self.set_resizable(False)

        if monitor is not None and Gtk4LayerShell is not None:
            self.layer_shell_enabled = self._setup_layer_shell(monitor)

        self._install_css()
        self._build_ui()
        self._attach_keys()

    def _setup_layer_shell(self, monitor: Gdk.Monitor) -> bool:
        Gtk4LayerShell.init_for_window(self)
        if not Gtk4LayerShell.is_layer_window(self):
            return False

        geometry = monitor.get_geometry()
        self.set_default_size(geometry.width, geometry.height)
        self.set_size_request(geometry.width, geometry.height)

        Gtk4LayerShell.set_namespace(self, "autheos_message")
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_monitor(self, monitor)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)
        Gtk4LayerShell.set_exclusive_zone(self, 0)
        for edge in (
            Gtk4LayerShell.Edge.LEFT,
            Gtk4LayerShell.Edge.RIGHT,
            Gtk4LayerShell.Edge.TOP,
            Gtk4LayerShell.Edge.BOTTOM,
        ):
            Gtk4LayerShell.set_anchor(self, edge, True)
            Gtk4LayerShell.set_margin(self, edge, 0)
        return True

    def _install_css(self) -> None:
        css = f"""
        window {{
            background: {self.args.background};
        }}
        box, label {{
            background: transparent;
        }}
        label {{
            color: {self.args.color};
            font-size: {self.args.font_size}px;
            font-weight: 700;
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.set_halign(Gtk.Align.FILL)
        root.set_valign(Gtk.Align.FILL)
        root.set_hexpand(True)
        root.set_vexpand(True)
        root.set_margin_top(8)
        root.set_margin_bottom(8)
        root.set_margin_start(12)
        root.set_margin_end(12)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center.set_halign(Gtk.Align.CENTER)
        center.set_valign(Gtk.Align.CENTER)
        center.set_hexpand(True)
        center.set_vexpand(True)

        self.label = Gtk.Label(label="")
        self.label.set_wrap(True)
        self.label.set_valign(Gtk.Align.CENTER)
        self._apply_reveal_position(is_animation_done=False)

        center.append(self.label)
        root.append(center)
        self.set_child(root)

    def _apply_reveal_position(self, is_animation_done: bool) -> None:
        mode = self.args.reveal_position

        if mode == "center":
            self.label.set_halign(Gtk.Align.CENTER)
            self.label.set_xalign(0.5)
            self.label.set_justify(Gtk.Justification.CENTER)
            self.label.set_size_request(-1, -1)
            return

        if mode == "left":
            self.label.set_halign(Gtk.Align.CENTER)
            self.label.set_xalign(0.0)
            self.label.set_justify(Gtk.Justification.LEFT)
            self.label.set_size_request(-1, -1)
            return

        if is_animation_done:
            self.label.set_halign(Gtk.Align.CENTER)
            self.label.set_xalign(0.5)
            self.label.set_justify(Gtk.Justification.CENTER)
            self.label.set_size_request(-1, -1)
            return

        self.label.set_halign(Gtk.Align.CENTER)
        self.label.set_xalign(0.0)
        self.label.set_justify(Gtk.Justification.LEFT)
        self._reserve_final_width()

    def _reserve_final_width(self) -> None:
        layout = self.label.create_pango_layout(self.args.message)
        width, _height = layout.get_pixel_size()
        if width > 0:
            self.label.set_size_request(width, -1)

    def _attach_keys(self) -> None:
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(controller)

    def _on_key_pressed(self, _controller, keyval, _keycode, _state) -> bool:
        if keyval in (Gdk.KEY_Escape, Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            app = self.get_application()
            if app is not None:
                app.quit()
            return True
        return False

    def start_animation(self) -> None:
        if not self.tokens:
            self._apply_reveal_position(is_animation_done=True)
            self._schedule_exit_if_needed()
            return

        interval_ms = max(1, int(1000 / max(self.args.speed, 0.01)))
        GLib.timeout_add(interval_ms, self._tick)

    def _tick(self) -> bool:
        if self.index >= len(self.tokens):
            self._apply_reveal_position(is_animation_done=True)
            self._schedule_exit_if_needed()
            return False

        self.current_text += self.tokens[self.index]
        self.index += 1
        self.label.set_text(self.current_text)

        if self.index >= len(self.tokens):
            self._apply_reveal_position(is_animation_done=True)
            self._schedule_exit_if_needed()
            return False
        return True

    def _schedule_exit_if_needed(self) -> None:
        if self.args.exit_after <= 0 or self.exit_scheduled:
            return
        self.exit_scheduled = True
        GLib.timeout_add(int(self.args.exit_after * 1000), self._exit)

    def _exit(self) -> bool:
        app = self.get_application()
        if app is not None:
            app.quit()
        return False


class MessageApp(Gtk.Application):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(application_id="io.github.autheos.message")
        self.args = args
        self.windows: list[MessageWindow] = []
        self.animation_started = False

    def _build_windows(self) -> None:
        if self.windows:
            return

        if self.args.all_monitors and Gtk4LayerShell is None:
            print(
                "Warning: gtk4-layer-shell not available, falling back to one monitor.",
                file=sys.stderr,
            )

        if self.args.all_monitors and Gtk4LayerShell is not None:
            display = Gdk.Display.get_default()
            if display is not None:
                monitors = display.get_monitors()
                for index in range(monitors.get_n_items()):
                    monitor = monitors.get_item(index)
                    if monitor is None:
                        continue
                    window = MessageWindow(self, self.args, monitor=monitor)
                    if not window.layer_shell_enabled:
                        window.destroy()
                        for old_window in self.windows:
                            old_window.destroy()
                        self.windows.clear()
                        print(
                            "Warning: Layer-shell init failed, falling back to one monitor. "
                            "Try starting with LD_PRELOAD=libgtk4-layer-shell.so.0",
                            file=sys.stderr,
                        )
                        break
                    self.windows.append(window)

        if not self.windows:
            self.windows.append(MessageWindow(self, self.args))

    def do_activate(self) -> None:
        self._build_windows()
        for window in self.windows:
            window.present()
        if self.animation_started:
            return
        for window in self.windows:
            window.start_animation()
        self.animation_started = True


def main() -> int:
    args = parse_args()
    app = MessageApp(args)
    return app.run([sys.argv[0]])


if __name__ == "__main__":
    raise SystemExit(main())
