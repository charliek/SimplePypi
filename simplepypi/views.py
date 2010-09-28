from flask import Flask, render_template, abort, g, redirect, url_for, Response, request
import os
import os.path
import re
import hashlib
from simplepypi import default_config
from simplepypi import app
from werkzeug import secure_filename
from datetime import datetime
from simplepypi.release_pb2 import Release
import time

class InputException(Exception):
    pass

class PyPi(object):
    def __init__(self, pypi_dir, username, password):
        self.pypi_dir = pypi_dir
        self.username = username
        self.password = password

    def packages(self):
        packages = []
        files = os.listdir(self.pypi_dir)
        for f in files:
            if os.path.isdir(os.path.join(self.pypi_dir, f)):
                packages.append(f)
        return packages

    def valid_package_name(self, package_name):
        return re.search(r'^[0-9a-zA-Z \.\-_]{1,40}$', package_name) and package_name.find('..') == -1

    def valid_file_name(self, filename):
        return re.search(r'^[0-9a-zA-Z \.\-_]{1,40}$', filename) and filename.find('..') == -1

    def md5(self, f):
        md5 = hashlib.md5()
        with open(f, 'rb') as fp:
            data = fp.read()
            md5.update(data)
        return md5.hexdigest()

    def get_binary_path(self, package, file):
        if not self.valid_package_name(package) or not self.valid_file_name(file):
            raise InputException('Invalid package or file name')
        f = os.path.join(self.pypi_dir, package, file)
        if not os.path.isfile(f):
            raise InputException('The file specified was not found')
        return f

    def save_file(self, release, fileobj, auth):
        if auth.username != self.username or auth.password != self.password:
            raise InputException('Invalid username and password')
        if not self.valid_package_name(release.package):
            raise InputException('Invalid Package Name')
        if not self.valid_file_name(release.filename):
            raise InputException('Invalid File Name')
        ftype = None
        for extn in ('.tar.gz', '.zip', '.egg'):
            if release.filename == release.package + '-' + release.version + extn:
                ftype = extn
        if ftype is None:
            raise InputException('Only tar.gz, zip, and egg formats are supported')
        print ftype
        package_dir = os.path.join(self.pypi_dir, release.package)
        if not os.path.isdir(package_dir):
            os.makedirs(package_dir)
        dest = os.path.join(package_dir, release.filename)
        if os.path.isfile(dest):
            raise InputException('Version already exists')
        fileobj.save(dest)
        if self.md5(dest) != release.md5:
            os.remove(dest)
            raise InputException('MD5 sum did not match expected')
        pb_file = os.path.join(package_dir, release.package + '-' + release.version + '.pb')
        with open(pb_file, 'wb') as fp:
            fp.write(release.SerializeToString())
        return True

    def files(self, package):
        if not self.valid_package_name(package):
            raise InputException('Invalid Package Name')
        package_dir = os.path.join(self.pypi_dir, package)
        if not os.path.isdir(package_dir):
            raise InputException('Package Not Found')
        files = []
        dir_list = os.listdir(package_dir)
        for f in dir_list:
            if len(f) > 3 and f.find(package) == 0 and f[-3:] == '.pb':
                release = Release()
                with open(os.path.join(package_dir, f), 'rb') as fp:
                    files.append(release.ParseFromString(fp.read()))
                if release.filename in dir_list:
                    files.append(release)
        return files

# see http://flask.pocoo.org/docs/config/
app.config.from_object(default_config)
app.config.from_envvar('SIMPLEPYPI_SETTINGS', silent=True)
pypi = PyPi(app.config['PYPI_DIRECTORY'], app.config['PYPI_USERNAME'], app.config['PYPI_PASSWORD'])

### START ROUTES ###
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return package_upload()
    else:
        return render_template('index.html', packages=pypi.packages())

@app.route('/pypi/<package>/')
def package_docs(package):
    try:
        files = pypi.files(package)
    except InputException as e:
        abort(404)
    return render_template('package_readme.html', package=package, files=files)

@app.route('/simple/')
def all_packages():
    return render_template('all_packages.html', packages=pypi.packages())

@app.route('/simple/<package>/')
def package_info(package):
    try:
        files = pypi.files(package)
    except InputException as e:
        abort(404)
    return render_template('package_info.html', package=package, files=files)

@app.route('/package/<package>/<file>')
def get_binary_path(package, file):
    try:
        f = pypi.get_binary_path(package, file)
    except InputException as e:
        abort(404)
    with open(f, 'rb') as fp:
        content = fp.read()
    return Response(content, mimetype='application/octet-stream')

def package_upload():
    frm = request.form
    # required values
    name = frm.get('name', None)
    version = frm.get('version', None)
    md5 = frm.get('md5_digest', None)

    # values defaulted to blank
    summary = frm.get('summary', '')
    description = frm.get('description', '')
    action = frm.get(':action', None)
    file = request.files['content']
    filename = secure_filename(file.filename)
    author = frm.get('author', '')
    author_email = frm.get('author_email', '')

    auth = request.authorization
    if auth is None:
        abort(401, "ERROR: No authentication information found")

    if name is None or version is None or md5 is None:
        abort(401, "ERROR: name, version, :action and md5_digest are all required.")
    if action != 'file_upload':
        abort(401, "ERROR: only actions of file_upload is supported")
    release = Release()
    release.package = name
    release.md5 = md5
    release.version = version
    release.filename = filename
    release.createdate = datetime.now().isoformat()
    release.summary = summary
    release.description = description
    release.author = author
    release.author_email = author_email
    try:
        pypi.save_file(release, file, auth)
    except InputException as e:
        abort(401, e.args[0])
    return 'upload complete'
