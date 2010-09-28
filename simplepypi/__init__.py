from flask import Flask
app = Flask(__name__)

import simplepypi.default_config
import simplepypi.views

