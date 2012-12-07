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
sudo apt-get install libgstreamer-0.10 gstreamer0.10-plugins-good gstreamer0.10-plugins-bad gstreamer0.10-plugins-ugly python-gst0.10

# Mac (With Homebrew: http://mxcl.github.com/homebrew/)
brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-ugly gst-python
```

Most modern distributions will already have these packages installed, so this step may or may not be necessary.

Install dependencies with pip

``` bash
pip install -r requirements.txt
```

Run the musik server
``` bash
python musik.py
```
The Musik server starts up by default on port 8080
point your browser at [http://localhost:8080/](http://localhost:8080/)

Optionally you can set a PORT environment variable

``` bash
export PORT=5000
python musik.py
```
##VirtualEnv and GStreamer
While virtualenv is really nice for maintaining a clean workspace, it doesn't play nicely with dependencies that can't be resolved via pip. As mentioned above, Musik has two such dependencies:
- `libgstreamer-0.10`: GStreamer multimedia framework
- `python-gst0.10`: GStreamer Python bindings

If you created your virtualenv with the `--no-site-packages` flag, you may be unable to access the GStreamer bindings from within your workspace.

To test this, activate your virtualenv, then open a Python interpreter and type `import gst`. If you get an error message that looks like the following, then you've got this problem:
```bash
musikpolice@dev ~ $ workon musik
(musik)musikpolice@dev ~ $ python
Python 2.7.2+ (default, Oct  4 2011, 20:03:08)
[GCC 4.6.1] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import gst
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ImportError: No module named gst
>>>
```

The current work-around for this issue is to develop without virtualenv, relying on it only to maintain the requirements.txt file.

Others have suggested that symlinking to the necessary libraries from within the virtualenv will solve the problem, but as of yet, I haven't found the necessary combination of symlinks to make it work. The following StackOverflow issues may provide more information for those inclined to investigate further:
- [Virtualenv on Ubuntu with no site-packages](http://stackoverflow.com/questions/249283/virtualenv-on-ubuntu-with-no-site-packages)
- [Python: virtualenv - gtk-2.0](http://stackoverflow.com/questions/3580520/python-virtualenv-gtk-2-0)
- [Python package installed globally, but not in a virtualenv (PyGTK)](http://stackoverflow.com/questions/12830662/python-package-installed-globally-but-not-in-a-virtualenv-pygtk?lq=1)

##Using Foreman (Optional)

Foreman is a command-line tool for running Procfile-backed apps. It allows you to run your app easily with environment variables that do not affect the rest of your system.

Install Foreman, it comes pre-packaged with the [Heroku Toolbelt](https://toolbelt.heroku.com/).

Create a ```.env``` file in your project directory

``` bash
cd musik
touch .env
```

Add any environment variables you wish to your ```.env``` file, here is an example file.

```
PORT=5555
SOME_VAR=blah-blah-blah
```

Start up the Musik server using foreman

``` bash
foreman start
```

Stop the Musik server when running in foreman by hitting ```ctrl-c```

##Contributing

1. Fork this repo
1. Take a look at the issues. What needs to be done?
1. Make a topic branch for what you want to do. Bonus points for referencing an issue (like 2-authentication).
1. Make your changes.
1. Create a Pull Request.
1. Profit!
