# The Jetson

Each group gets an NVIDIA Jetson Orin with a screen, keyboard and mouse. It is a full Ubuntu
workstation, not an appliance - you log in, open a terminal, and work on it directly. It is
also what will be carried on the robot, so what you build has to run there rather than on
your own laptop.

The same machines are used for the Go2 quadrupeds and the SO-101 arms, which is why this
page is about the Jetson itself. What to do with a robot is in that robot's folder.

## The machines

| Name            | Who     | Address last seen | Ready           |
| --------------- | ------- | ----------------- | --------------- |
| `orin-nano-1` | teacher | 192.168.0.217     | yes (keeps ROS) |
| `orin-nano-2` | group 1 | 192.168.0.145     | yes             |
| `orin-nano-3` | group 2 | 192.168.0.191     | yes             |
| `orin-nano-4` | group 3 | 192.168.0.111     | yes             |
| `orin-nano-5` | group 4 | 192.168.0.58      | yes             |
| `orin-nano-6` | group 5 | 192.168.0.116     | yes             |

One machine per group for the whole course, so the machine is yours to keep tidy.

**You have to be on the PhysicalAI wifi.** Every address here is private to that network.
From a phone hotspot or any other wifi there is no route to them at all - not a slow one, no
route - so check which network your laptop is on before concluding a machine is down.

Try the name first, and fall back to the address:

```bash
ssh ema-student@orin-nano-1.local          # mDNS, when the machine advertises itself
ssh ema-student@192.168.0.217              # the address from the table
```

The name is the better habit, because the addresses are DHCP leases and change on reboot. But
mDNS is not reliable here - on 28 Sep 2026 only `orin-nano-1` answered to its `.local` name -
so keep the table, and update it when you see a machine on a new address.

If neither works, the machine is off or has not joined the wifi. That one needs its screen and
keyboard: a machine cannot be fixed over a network it is not on.

## What is already on it

|          |                                                                            |
| -------- | -------------------------------------------------------------------------- |
| OS       | Ubuntu 24.04, aarch64                                                      |
| `git`  | for getting code on and off the machine                                    |
| `nano` | a terminal editor, for when a GUI is more trouble than it is worth         |
| `uv`   | Python environments and packages, faster than pip and easier to throw away |
| VS Code  | including the terminal, if you prefer it to a bare shell                   |
| Docker   | working for your user - check with`docker run --rm hello-world`          |

**Nothing else.** No ROS, no robot drivers, no workspace. Installing what you need is the
first task, and it is a real one: the choices you make there decide how easy the rest is.

If `docker run` complains about permissions, your user is not in the `docker` group:

```bash
sudo usermod -aG docker $USER      # then log out and back in
```

## Preparing a Jetson (teacher only)

How the machines were set up. Everything below assumes a freshly flashed Orin running
Ubuntu 24.04, already through NVIDIA's own first-boot steps:
[Unbox and connect the developer kit](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/quick_start.html#unbox-and-connect-the-developer-kit).

```bash
sudo apt update && sudo apt install -y git curl build-essential nano
mkdir -p ~/repos                    # everyone's work lives under here
```

**Docker**, and make it usable without `sudo`:

```bash
sudo apt install -y docker.io
sudo usermod -aG docker $USER        # log out and back in for this to take effect
docker run --rm hello-world
```

**Pick one Docker and stay with it.** Ubuntu's `docker.io` and Docker's own `docker-ce` (what
`get.docker.com` installs) conflict. Running the second on a machine that already has the
first can leave both half-removed: `dpkg -l` shows them as `rc`, the `docker` CLI is still
there, and `docker.service` fails with no `dockerd` behind it. If that happens, reinstall one
of them cleanly rather than trying to repair it:

```bash
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
systemctl is-active docker
```

The NVIDIA container toolkit is only needed if containers must use the GPU. For the Go2 work
they do not - it is CPU and networking. `nvidia-ctk runtime configure` adds `nvidia` as an
available runtime, not the default, so it is harmless either way.

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

**ROS 2 Jazzy - on the teacher machine only.** The student machines get no ROS: installing it
is task 1, and a Jetson that already has it has had that task done for it.

```bash
locale  # check for UTF-8

sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

locale  # verify settings

sudo apt install software-properties-common
sudo add-apt-repository universe

sudo apt update && sudo apt install curl -y
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb

sudo apt update
sudo apt install ros-jazzy-desktop
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
sudo rosdep init
rosdep update
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
git --version; uv --version; code --version | head -1; nano --version | head -1
docker run --rm hello-world
localectl status | grep X11
nmcli -g 802-11-wireless.powersave con show <wifi-name>
ls -d ~/repos
```

## Where to work

Everything you make goes under `~/repos`, in a folder of your own. Same convention as the
SO-101 labs, so one machine serves both:

```bash
mkdir -p ~/repos/cas_26_YOUR_NAME   # e.g. ~/repos/cas_26_johm
cd ~/repos/cas_26_YOUR_NAME
```

These machines are shared - several people use the same login - so that folder is what keeps
your work separate from everyone else's. Clone your repos into it; scripts, workspaces,
notes and experiments all live there, not scattered across the home directory.

```bash
ls ~/repos                          # who else has been on this machine
```

Two habits worth having from the start:

- **Push to git.** These machines are shared and get reimaged between courses. Anything only
  on a Jetson is temporary.
- **Say which machine you were on** when you ask for help. `hostname` tells you.

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

You can sit at the screen, or reach it from your laptop over the network. You need to be on
the same wifi as the machine.

```bash
ssh ema-student@192.168.0.111        # your machine's address, from the table above
```

By name works too, when the machine is advertising itself:

```bash
ssh ema-student@orin-nano-4.local
```

The name is the better habit - addresses are DHCP leases and change on reboot - but it does
not always resolve, so keep the table handy. If neither works, the machine is off or not on
the wifi, and that needs its screen and keyboard: a machine cannot be fixed over a network it
is not on.

Both are fine. The screen is simpler for a first session; SSH is better once you are editing
code, because you can use your own editor and your own terminal.

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
