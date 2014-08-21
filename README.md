#Musik

A web-based streaming media library and player. Run Musik on your home server to gain unlimited access to your music collection from anywhere in the world.

##Getting Started

Prerequisites:
- Python 2.7 (although Python 2.6 should work without issue)
- [Pip](http://www.pip-installer.org/en/latest/)
- [Virtualenv](http://pypi.python.org/pypi/virtualenv)
- [Virtualenvwrapper](http://www.doughellmann.com/projects/virtualenvwrapper/) (optional)
- A fork of this repo

Clone the repo

``` bash
git clone git@github.com:[username]/musik.git
cd musik
```

Set up a virtual environment using virtualenv (or virtualenvwrapper)

``` bash
#virtualenv
virtualenv musik-venv --distribute

#virtualenvwrapper
mkvirtualenv musik-venv
```

Activate the virtual environment

``` bash
#virtualenv
source musik-venv/bin/activate

#virtualenvwrapper
workon musik-venv
```

Install dependencies from your distribution's package manager
```bash
# Linux
sudo apt-get update
sudo apt-get install lame ffmpeg2theora vorbis-tools faac faad

# Mac (With Homebrew: http://mxcl.github.com/homebrew/)
brew install lame ffmpeg2theora vorbis-tools faac faad2
```

Most modern distributions will have some or all of these packages installed, so this step may or may not be necessary. Not all are required, but lame and vorbis-tools are recommended at minimum.

Install dependencies with pip

``` bash
pip install -r requirements.txt
```

Run the musik server
``` bash
python musik.py
```
The Musik server starts up by default on port 8080. You can change the port by modifying musik.cfg.
point your browser at [http://localhost:8080/](http://localhost:8080/)

##Contributing

1. Fork this repo
1. Take a look at the issues. What needs to be done?
1. Make a topic branch for what you want to do. Bonus points for referencing an issue (like 2-authentication).
1. Make your changes.
1. Create a Pull Request.
1. Profit!