import os
import string
from flask import *
from bson.json_util import *
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
import copy
csrf = CSRFProtect()
try:
    import functions.actions as functions
except:
    import siena.server.functions.actions as functions
import json
from pathlib import Path
Path("uploads").mkdir(parents=True, exist_ok=True)
Path("exports").mkdir(parents=True, exist_ok=True)
# Get the current working directory 
CURRENT_WORKING_DIRECTORY = os.getcwd()

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

#JSONEncoder().encode(objName)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'yml','yaml'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True,template_folder='WEB-UI')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )
    app.static_folder = 'WEB-UI'

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Index page
    @app.route('/')
    @app.route('/index')
    def start():
        resp = make_response(render_template('start.html'))
        resp.set_cookie('userId', '621867b6321be2d531ef6de4')
        return resp

    @app.route('/siena')
    def siena():
        return render_template('siena.html')

    # Save file
    @app.route('/API/fileUpload',methods=['POST','GET'])
    def save_file():
        if request.method == 'POST':
            # check if the post request has the file part
            if 'file' in request.files:
                file = request.files['file']
                # If the user does not select a file, the browser submits an
                # empty file without a filename.
                if file.filename == '':
                    flash('No selected file')
                    return 'file name not found!', 404
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'],filename)
                    file.save(path)
                    functions.read_yml(path,file.filename)
            else:
                post_data = request.json
                file_path = post_data['FILE_PATH']
                if not file_path:
                    flash('No selected file')
                    return 'file name not found!', 404
                filename = file_path.split("/")[-1]
                functions.read_yml(file_path,filename)
        return jsonify({})

    # API for sentence management
    @app.route('/API/sentence',methods=['GET','PATCH','POST','DELETE'])
    def endpoint_sentences():
        responce = {}
        data = []
        if request.method == 'GET':
            fle = Path('inprogress.SIENA')
            fle.touch(exist_ok=True)
            f = open(fle)
            with open("inprogress.SIENA","r", encoding='utf-8') as file:
                line_id = 0
                while (line := file.readline().rstrip()):
                    row = {}
                    file_line = line.split('<sep>')
                    row["sentence"]=file_line[1]   
                    row["intent"]=file_line[0]
                    row["id"]=line_id
                    line_id+=1
                    data.append(row)
                responce["data"] = data
            return JSONEncoder().encode(responce)
        elif request.method == 'PATCH':
            post_data = request.json
            sentences = post_data['data']
            for sentence in sentences:
                intent = sentence['INTENT']
                entity = sentence['ENTITY']
                mode = ""
                if "MODE" in sentence.keys():
                    mode = sentence['MODE']
                highlighted = sentence['HIGHLIGHTED']
                sentence_id = int(sentence['id'])
                text = sentence['TEXT']
                if mode == "ENTITY_REMOVE":
                    functions.remove_entry_from_knowledge(entity.strip(),highlighted.strip())
                else:
                    if intent != "" and entity != "":
                        functions.update_knowledge(entity.strip(),highlighted.strip())

                functions.update_sentences_by_user(sentence_id,text,intent)
            return jsonify(responce)
        elif request.method == 'DELETE':
            post_data = request.json
            sentences = post_data['data']
            for sentence in sentences:
                sentence_id = ObjectId(sentence['_id'])
                functions.delete_sentences(sentence_id)
            return jsonify(responce)
        else:
            flash('Invalid request')
            return jsonify(responce)

    #  API for entity management
    @app.route('/API/entity',methods=['GET','POST'])
    def endpoint_entity():
        data = {}
        if request.method == 'GET':
            data["ENTITIES"] = functions.get_entities_by_project()
            return jsonify(data)
        elif request.method == 'POST':
            post_data = request.json
            entities = post_data['data']
            functions.insert_entities_for_project(entities)
            data['messege'] = "Updated"
            return data
        else:
            return 'bad request!', 400

    #  API for project management
    @app.route('/API/project',methods=['GET','POST'])
    def endpoint_project():
        data = {}
        if request.method == 'GET':
            user_id = request.cookies.get('userId',None)
            if user_id == None:
                return 'user not found!', 404
            else:
                data["PROJECTS"] = functions.get_projects(user_id)
                return JSONEncoder().encode(data)
        if request.method == 'POST':
            user_id = request.cookies.get('userId',None)
            post_data = request.json
            project_name = post_data['NAME']
            project_type = post_data['TYPE']
            if user_id == None and project_name == None and project_type == None:
                return 'data not found!', 404
            else:
                data["PROJECT_ID"] = functions.create_project(user_id,project_name,project_type)
                return JSONEncoder().encode(data) 
        else:
            return 'bad request!', 400

    #  API for file management
    @app.route('/API/file',methods=['GET','POST'])
    def endpoint_file():
        data = {}
        if request.method == 'GET':
            data["FILES"] = functions.get_files()
            return JSONEncoder().encode(data)
        else:
            return 'bad request!', 400

    @app.route('/API/export',methods=['GET','POST'])
    def endpoint_export():
        data = {}
        if request.method == 'GET':
            data = functions.convert_files()
            return JSONEncoder().encode(data)
        else:
            return 'bad request!', 400
    
    # import knowledge
    @app.route('/knowledge/upload', methods=['POST', 'GET'])
    def upload_knowldge():
        if request.method == 'POST':
            # check if the post request has the file part
            if 'file' in request.files:
                file = request.files['file']
                # If the user does not select a file, the browser submits an
                # empty file without a filename.
                if file.filename == '':
                    flash('No selected file')
                    return 'file name not found!', 404
                if file and functions.allowed_file_knowledge(file.filename):
                    file.save("siena_cache/knowledge_base_.csv")
                    
            else:
                return {"status": "error", "response": "file not found!"}, 400

        else:
            return {"status": "error", "response": "bad request!"}, 400

    # export knowledge
    @app.route('/knowledge/export', methods=['POST', 'GET'])
    def export_knowledge():
        if request.method == 'POST':
            # check if the post request has the file part
            if 'file' in request.files:
                file = request.files['file']
                # If the user does not select a file, the browser submits an
                # empty file without a filename.
                if file.filename == '':
                    flash('No selected file')
                    return 'file name not found!', 404
                if file and functions.allowed_file_knowledge(file.filename):
                    filename = secure_filename(file.filename)
                    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(path)
            else:
                post_data = request.json
                file_path = post_data['FILE_PATH']
                if not file_path:
                    flash('No selected file')
                    return 'file name not found!', 404
                filename = file_path.split("/")[-1]
                read_yml(file_path, filename)
        return {}

    # SIENA knowledge component
    @app.route('/API/knowledge',methods=['POST','GET'])
    def endpoint_algorithms():
        data = {}
        if request.method == 'POST':
            post_data = request.json
            text = post_data["TEXT"]
            data["SUGGESTIONS"] = functions.get_suggestions(text)
            return JSONEncoder().encode(data)
        elif request.method == 'GET':
            data["DATA"] = functions.get_base_words()
            return JSONEncoder().encode(data)
        else:
            return 'bad request!', 400

    # SIENA auto annotate algorithem
    @app.route('/API/autoannotate',methods=['POST'])
    def endpoint_autoannotate():
        data = {}
        if request.method == 'POST':
            post_data = request.json
            base_word = post_data["BASE_WORD"]
            entity = post_data["ENTITY"]
            functions.auto_annotate(base_word,entity)
            return JSONEncoder().encode(data)
        else:
            return 'bad request!', 400

    # file navigation API
    @app.route('/API/navigation/',methods=['GET'])
    def endpoint_navigation():
        global CURRENT_WORKING_DIRECTORY
        data = {}
        if request.method == 'GET':
            data["FILES"] = []
            for root, dirnames, filenames in os.walk(CURRENT_WORKING_DIRECTORY):
                for filename in filenames:
                    if filename.endswith(('.YAML', '.YML', '.yaml', '.yml')):
                        files = {}
                        abs_path = os.path.join(root, filename)
                        rel_path = abs_path.replace(CURRENT_WORKING_DIRECTORY,"")
                        files["PATH"] = rel_path[1:].replace("\\","/")
                        files["NAME"] = filename
                        data["FILES"].append(files)
            return JSONEncoder().encode(data)

        else:
            return 'bad request!', 400

    # Test function
    @app.route('/test',methods=['GET','PATCH','POST'])
    @csrf.exempt
    def test():
        return "Hi"



    return app