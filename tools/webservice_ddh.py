import os
from flask import Flask, request, send_file, send_from_directory

# create Flask application
app = Flask(__name__)


@app.errorhandler(404)
def not_found(ev):
    e = ''
    e += '<html><head><title>DDH auto-deploy</title></head><body>'''
    e += '<p>{}</p>'.format(ev)
    e += '</body></html>'
    return e


@app.route('/')
def index():
    s = ''
    s += '<html><head><title>DDH auto-deploy</title></head><body>'''
    s += '<p>provide project + ship to get their configuration files</p>'
    s += '</body></html>'
    return s


# example how to do args
# @app.route('/hi/<name>')
# def say_hi(name):
#     # http://127.0.0.1:5000/hi/joaquim?eo=3&ui=5
#     eo = request.args.get('eo')
#     ui = request.args.get('ui')
#     return 'Hello, %s! %s %s' % (name, eo, ui)


@app.route("/<path:project>/<path:vessel_name>")
def get_vessel_files(project, vessel_name):
    # @ browser: as_attachment = 0 shows, = 1 gets
    zip_file = vessel_name
    if not str(vessel_name).endswith('.zip'):
        zip_file = '{}.zip'.format(vessel_name)
    return send_from_directory(project, zip_file, as_attachment=True)


# to create / upload / get the files:
#   $ zip -r --password <password> <output_file.zip> <folder_w_files>
#   $ scp -i <path_to_file.pem> login@<IP>:<destination_project_folder>
#   $ curl http://<IP>:<port>/<project>/<vessel_file.zip> --output info.zip
if __name__ == "__main__":
    app.debug = True

    # these are NOT equivalent, first one is localhost
    # app.run()
    app.run(host='0.0.0.0')
