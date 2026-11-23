# Litra Glow for Omarchy

A light bulb icon in the Omarchy bar for the Logitech Litra Glow. Click it to turn the light on or off. Hover for brightness and color temperature sliders.

Requires Omarchy's Quickshell plugin system. This does not support older Waybar-based Omarchy installations.

## Install

```sh
omarchy plugin add https://github.com/AksharP5/omarchy-litra-glow.git --enable --yes
```

The widget appears on the right by default. To place it immediately right of Razer Battery, if installed:

```sh
omarchy bar move akshar.litra-glow --after akshar.razer-battery
```

## Behavior

- A lit bulb means the light is on, an outlined bulb means it is off. A dimmed bulb means no Litra Glow is connected; hover for details.
- Brightness runs from 20 to 250 lumens. Temperature runs from 2700 K to 6500 K in steps of 100 K.
- The widget reads the light every two seconds, so changes made with the light's own buttons show up in the bar. Plugging the light back in reconnects on its own.
- One helper process serves every monitor. It talks to the light over USB HID and needs no daemon, root, or extra packages beyond Python 3.

Tested with the Litra Glow over USB, ID `046d:c900`. The Litra Beam uses different IDs and is not supported.

## Permissions

systemd 258 and later give the logged-in user access to the Litra Glow through its hardware database, so on a current Arch install it works as is. On an older system, if `omarchy-shell akshar.litra-glow status` reports permission denied, add a udev rule and replug the light:

```sh
echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="c900", TAG+="uaccess"' \
  | sudo tee /etc/udev/rules.d/70-litra-glow.rules
sudo udevadm control --reload
```

## Troubleshooting

```sh
omarchy-shell akshar.litra-glow status
omarchy-shell akshar.litra-glow toggle
omarchy-shell akshar.litra-glow brightness 120
omarchy-shell akshar.litra-glow temperature 4000
```

The light is found by its HID ID in `/sys/class/hidraw`, so its `/dev/hidraw` number may change between boots without breaking anything.

## Development

```sh
python3 -m unittest discover -s tests -v
omarchy plugin validate .
python3 litra.py status
```

Update an installed checkout with `omarchy plugin update akshar.litra-glow`.

MIT licensed. Not affiliated with Logitech.
