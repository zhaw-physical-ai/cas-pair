# The Jetson

Each group gets an NVIDIA Jetson Orin with a screen, keyboard and mouse. It is a full Ubuntu
workstation, not an appliance - you log in, open a terminal, and work on it directly. It is
also what will be carried on the robot, so what you build has to run there rather than on
your own laptop.

The same machines are used for the Go2 quadrupeds and the SO-101 arms, which is why this
page is about the Jetson itself. What to do with a robot is in that robot's folder.

## What is already on it

| | |
|---|---|
| OS | Ubuntu 24.04, aarch64 |
| `git` | for getting code on and off the machine |
| `uv` | Python environments and packages, faster than pip and easier to throw away |
| VS Code | including the terminal, if you prefer it to a bare shell |
| Docker | working for your user - check with `docker run --rm hello-world` |

**Nothing else.** No ROS, no robot drivers, no workspace. Installing what you need is the
first task, and it is a real one: the choices you make there decide how easy the rest is.

If `docker run` complains about permissions, your user is not in the `docker` group:

```bash
sudo usermod -aG docker $USER      # then log out and back in
```

## Preparing a Jetson

For whoever hands the machines over, not for students. Ubuntu 24.04 on an Orin, freshly
flashed.

```bash
sudo apt update && sudo apt install -y git curl build-essential
```

**Docker**, and make it usable without `sudo`:

```bash
sudo apt install -y docker.io
sudo usermod -aG docker $USER        # log out and back in for this to take effect
docker run --rm hello-world
```

**uv** - Python environments and packages:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# it installs to ~/.local/bin; open a new shell, then:
uv --version
```

**VS Code** - Microsoft publishes an arm64 build in their apt repository:

```bash
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /tmp/ms.gpg
sudo install -D -o root -g root -m 644 /tmp/ms.gpg /etc/apt/keyrings/packages.microsoft.gpg
echo "deb [arch=arm64 signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" \
  | sudo tee /etc/apt/sources.list.d/vscode.list
sudo apt update && sudo apt install -y code
```

**Keyboard**, if the machines have Swiss keyboards. `localectl` refuses on Ubuntu because
`console-setup` owns this file:

```bash
sudo cp /etc/default/keyboard /etc/default/keyboard.bak
sudo sed -i 's/^XKBLAYOUT=.*/XKBLAYOUT="ch"/; s/^XKBVARIANT=.*/XKBVARIANT=""/' /etc/default/keyboard
sudo systemctl restart console-setup
```

**Wifi power save off.** This is worth more than it sounds: on one machine it took the ping
from a laptop from 43 ms average with 27 ms jitter down to 9 ms and 2.8 ms. The radio sleeps
between beacons, and the jitter is what teleoperation feels.

```bash
sudo nmcli con modify <wifi-name> 802-11-wireless.powersave 2
nmcli -g 802-11-wireless.powersave con show <wifi-name>     # must say 'disable'
sudo iw dev wlP1p1s0 set power_save off                     # and now, without reconnecting
```

**Check before handing it over:**

```bash
. /etc/os-release; echo "$PRETTY_NAME"      # Ubuntu 24.04
git --version; uv --version; code --version | head -1
docker run --rm hello-world
localectl status | grep X11
nmcli -g 802-11-wireless.powersave con show <wifi-name>
```

## Finding your way around

```bash
hostname                  # which machine you are on - say it when you ask for help
ip -br addr               # the network interfaces and their addresses
df -h /                   # disk. These have room, but images are large
free -h                   # memory
```

The machine has two network interfaces that matter: **wifi**, for the internet and for
reaching it from elsewhere, and **Ethernet**, which is how it talks to the robot. They are
completely separate - the robot link is a private cable with no router and no internet.

## Working on it

You can sit at the screen, or reach it from your laptop over the network:

```bash
ssh <user>@<hostname>.local
```

Both are fine. The screen is simpler for a first session; SSH is better once you are editing
code, because you can use your own editor.

Anything you want to keep, push to git. These machines are shared and get reimaged.

## Shutting it down

```bash
sudo shutdown -h now
```

Wait until it stops responding before cutting power. The root filesystem is on internal
storage and pulling power during a write can corrupt it, which means reinstalling.

**If the Jetson is powered from the robot rather than its own supply, shut the Jetson down
before switching the robot off** - otherwise turning the robot off is a power cut on a live
machine.

## Two things that will look broken and are not

**A robot answering `ping` is not a robot ready to talk ROS.** Its network comes up within
seconds of power-on; its ROS topics take substantially longer. Until they appear you will see
an almost empty topic list, which reads as a broken setup and is not. Wait, then look again.

**Software that was started before the robot cannot see it.** Anything using DDS binds to the
network interface when it starts and does not recover if that link appears later or flaps -
after plugging in a robot, powering one on, or moving a cable, restart whatever you had
running. It will still look perfectly healthy while reaching nothing.
