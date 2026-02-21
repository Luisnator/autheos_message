# autheos_message

Simple message app (typewriter animation).

## Requirements

- `python` (3.10+)
- `python-gobject`
- `gtk4`
- `gtk4-layer-shell` (for reliable multi-monitor overlays)

On Arch Linux:

```bash
sudo pacman -S python python-gobject gtk4 gtk4-layer-shell
```

For package building:

```bash
sudo pacman -S --needed base-devel
```

## Run

```bash
python autheos_message "Das ist ein Test" --mode char --speed 20
```

Word-by-word mode:

```bash
python autheos_message "Das ist ein Test" --mode word --speed 3
```

Auto-close 2 seconds after the animation:

```bash
python autheos_message "Das ist ein Test" --mode char --speed 25 --exit-after 2
```

## Options

- `message` (positional): text to show
- `--mode`: `char` or `word` (default: `char`)
- `--speed`: tokens per second (default: `15`)
- `--font-size`: text size in px (default: `72`)
- `--color`: CSS color (default: `#ffffff`)
- `--background`: CSS background color (default: transparent)
- `--exit-after`: seconds after animation to quit (default: `1.0`, set `0` to disable)
- `--reveal-position`: `left-to-center` (default), `center`, or `left`
- `--all-monitors` / `--no-all-monitors`: show on all monitors (default: all, uses `gtk4-layer-shell`)

If your system still prints `Failed to initialize layer surface`, try:

```bash
LD_PRELOAD=libgtk4-layer-shell.so.0 python autheos_message "Das ist ein Test"
```

Examples:

```bash
# default: appears from left, ends centered
python autheos_message "HDas ist ein Test" --reveal-position left-to-center

# always centered while typing
python autheos_message "Das ist ein Test" --reveal-position center

# always left-aligned while typing and when done
python autheos_message "Das ist ein Test" --reveal-position left

# only show on the current monitor
python autheos_message "Das ist ein Test" --no-all-monitors
```

## Hyprland Rules (recommended)

The app id/class is `io.github.autheos.message`. Add this to your `hyprland.conf`:

```ini
windowrule = match:class io.github.autheos.message,border_size 0
windowrule = match:class io.github.autheos.message, rounding  0
windowrule = match:class io.github.autheos.message, no_blur on
windowrule = match:class io.github.autheos.message, no_shadow on
windowrule = match:class io.github.autheos.message, animation {enabled = false}
```

## Build Arch Package

```bash
./scripts/build-arch-package.sh
```

Optional version overrides:

```bash
./scripts/build-arch-package.sh --pkgver 0.1.0 --pkgrel 1
```

Artifacts are written to `dist/`.
