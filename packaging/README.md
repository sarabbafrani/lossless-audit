# Desktop launcher

`lossless-audit.desktop` assumes `lossless-audit-gui` is on your `PATH`
(it is after `pip install .`). To install it for your user:

```sh
install -Dm644 packaging/lossless-audit.desktop \
  ~/.local/share/applications/lossless-audit.desktop
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

To run it straight from a checkout instead, change `Exec` to:

```
Exec=sh -c "cd /path/to/lossless-audit && exec python3 -m losslessaudit.webapp"
```

(`Exec` runs a single command, so the `cd` needs a shell around it.)
