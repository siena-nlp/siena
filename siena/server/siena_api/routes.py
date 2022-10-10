import logging
import os

from bson.json_util import (
    ObjectId
)
from flask import (
    current_app,
    flash,
    request,
    send_file
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

from siena.server.siena_api import blueprint
from siena.core.actions import (
    JSONEncoder,
    allowed_file_nlu,
    allowed_file_knowledge,
    read_yml,
    remove_entry_from_knowledge,
    update_sentences_by_user,
    update_knowledge,
    create_project,
    convert_files,
    get_files,
    get_suggestions,
    get_base_words,
    auto_annotate,
    delete_sentences,
    get_entities_by_project,
    insert_entities_for_project,
    get_projects,
    validate_tempory_knowledge_base,
    is_valid_nlu_yaml,
    get_valid_nlu_files,
    delete_entity
)
from siena.shared.constants import (
    SIENA_KNOWLEDGE_BASE_PATH,
    LOOKUP_DIR,
    UPLOAD_FOLDER,
    SIENA_IN_PROGRESS_PATH,
)

logger = logging.getLogger(__name__)
csrf = CSRFProtect()


# Save file
@blueprint.route('/fileupload', methods=['POST', 'GET'])
def save_file():
    try:
        logger.debug("File Upload API endpoint was called")
        if request.method == 'POST':
            # check if the post request has the file part
            if 'file' in request.files:
                file = request.files['file']
                # If the user does not select a file, the browser submits an
                # empty file without a filename.
                if file.filename == '':
                    flash('No selected file')
                    return 'file name not found!', 404
                if file and allowed_file_nlu(file.filename):
                    filename = secure_filename(file.filename)
                    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(path)
                    read_yml(path, file.filename)
            else:
                post_data = request.json
                file_path = post_data['FILE_PATH']
                if not file_path:
                    flash('No selected file')
                    return 'file name not found!', 404
                filename = file_path.split("/")[-1]
                read_yml(file_path, filename)
        return {}
    except Exception as e:
        logger.exception(f"Exception occurred in the fileupload endpoint. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400


# API for sentence management
@blueprint.route('/sentence', methods=['GET', 'PATCH', 'POST', 'DELETE'])
def endpoint_sentences():
    try:
        logger.debug("Sentence API endpoint was called")
        response = {}
        data = []
        if request.method == 'GET':
            with open(SIENA_IN_PROGRESS_PATH, "r", encoding='utf-8') as file:
                line_id = 0
                while line := file.readline().rstrip():
                    row = {}
                    file_line = line.split('<sep>')
                    row["sentence"] = file_line[1]
                    row["intent"] = file_line[0]
                    row["id"] = line_id
                    line_id += 1
                    data.append(row)
                response["data"] = data
            return JSONEncoder().encode(response)
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
                    remove_entry_from_knowledge(entity.strip(), highlighted.strip())
                else:
                    if intent != "" and entity != "":
                        update_knowledge(entity.strip(), highlighted.strip())

                update_sentences_by_user(sentence_id, text, intent)
            return response
        elif request.method == 'DELETE':
            post_data = request.json
            sentences = post_data['data']
            for sentence in sentences:
                sentence_id = ObjectId(sentence['_id'])
                delete_sentences(sentence_id)
            return response
        else:
            flash('Invalid request')
            return response
    except Exception as e:
        logger.exception(f"Exception occurred in the sentence endpoint. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400


#  API for entity management
@blueprint.route('/entity', methods=['GET', 'POST','DELETE'])
def endpoint_entity():
    try:
        logger.debug("Entity API endpoint was called")
        data = {}
        if request.method == 'GET':
            data["ENTITIES"] = get_entities_by_project()
            return data
        elif request.method == 'POST':
            post_data = request.json
            entities = post_data['data']
            insert_entities_for_project(entities)
            data['messege'] = "Updated"
            return data
        elif request.method == 'DELETE':
            post_data = request.json
            entity = post_data['data']
            entity_value = post_data['value']
            all_nlu_files = get_valid_nlu_files()["FILES"]
            delete_entity(all_nlu_files,entity,entity_value)
            return {"status": "success"}, 200
            

        else:
            return 'bad request!', 400
    except Exception as e:
        logger.exception(f"Exception occurred in the entity endpoint. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400


#  API for project management
@blueprint.route('/project', methods=['GET', 'POST'])
def endpoint_project():
    try:
        logger.debug("Project API endpoint was called")
        data = {}
        if request.method == 'GET':
            user_id = request.cookies.get('userId', None)
            if not user_id:
                return 'user not found!', 404
            else:
                data["PROJECTS"] = get_projects(user_id)
                return JSONEncoder().encode(data)
        if request.method == 'POST':
            user_id = request.cookies.get('userId', None)
            post_data = request.json
            project_name = post_data['NAME']
            project_type = post_data['TYPE']
            if not user_id and not project_name and not project_type:
                return {"status": "error", "response": "data not found!"}, 404
            else:
                data["PROJECT_ID"] = create_project(user_id, project_name, project_type)
                return JSONEncoder().encode(data)
        else:
            return {"status": "error", "response": "bad request!"}, 400
    except Exception as e:
        logger.exception(f"Exception occurred in the project endpoint. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400


#  API for file management
@blueprint.route('/file', methods=['GET', 'POST'])
def endpoint_file():
    try:
        logger.debug("File API endpoint was called")
        data = {}
        if request.method == 'GET':
            data["FILES"] = get_files()
            return JSONEncoder().encode(data)
        else:
            return {"status": "error", "response": "bad request!"}, 400
    except Exception as e:
        logger.exception(f"Exception occurred in the file endpoint. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400


@blueprint.route('/save', methods=['GET', 'POST'])
def endpoint_save():
    try:
        logger.debug("Save API endpoint was called")
        if request.method == 'GET':
            data = convert_files()
            # JSONEncoder().encode(data)
            if data:
                return {"status": "success"}, 200
            else:
                raise Exception()
        else:
            return {"status": "error", "response": "bad request!"}, 400
    except Exception as e:
        logger.exception(f"Exception occurred in /api/siena/save endpoint. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400


# SIENA knowledge component
@blueprint.route('/knowledge', methods=['POST', 'GET'])
def endpoint_algorithms():
    try:
        logger.debug("Knowledge API endpoint was called")
        data = {}
        if request.method == 'POST':
            post_data = request.json
            text = post_data["TEXT"]
            suggestions = get_suggestions(text)
            if len(suggestions) <1:
                return {"status": "error", "response": "No entities in the entity list"}, 400
            data["SUGGESTIONS"] = suggestions
            return JSONEncoder().encode(data)
        elif request.method == 'GET':
            data["DATA"] = get_base_words()
            return JSONEncoder().encode(data)
        else:
            return {"status": "error", "response": "bad request!"}, 400
    except Exception as e:
        logger.exception(f"Exception occurred in the knowledge endpoint. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400


# import knowledge
@blueprint.route('/knowledge/upload', methods=['POST', 'GET'])
def upload_knowledge():
    try:
        if request.method == 'POST':
            try:
                # check if the post request has the file part
                if 'file' in request.files:
                    file = request.files['file']
                    # If the user does not select a file, the browser submits an
                    # empty file without a filename.
                    if file.filename == '':
                        flash('No selected file')
                        return {"status": "error", "response": "file name not found!"}, 400
                    if file and allowed_file_knowledge(file.filename):
                        file.save("siena_cache/knowledge_base_temp.csv")
                        if validate_tempory_knowledge_base():
                            return {"status": "success", "response": "knowledge saved"}, 200
                        else:
                            return {"status": "error", "response": "error in file format"}, 400
                    else:
                        return {"status": "error", "response": "error in file format"}, 400

                else:
                    return {"status": "error", "response": "invalid file name!"}, 400
            except Exception as e:
                logger.exception(e)

        else:
            return {"status": "error", "response": "bad request!"}, 400
    except Exception as e:
        logger.exception(f"Exception occurred in the uploading knowledge-base endpoint. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400


# export knowledge
@blueprint.route('/knowledge/export', methods=['POST', 'GET'])
def export_knowledge():
    try:
        if os.path.isfile(os.path.join(os.getcwd(), SIENA_KNOWLEDGE_BASE_PATH)):
            return send_file(
                path_or_file=os.path.join(os.getcwd(), SIENA_KNOWLEDGE_BASE_PATH),
                as_attachment=True
            )
        else:
            raise Exception()
    except Exception as e:
        logger.exception(f"Exception occurred while exporting the knowledge-base csv. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400


# SIENA auto annotate algorithm
@blueprint.route('/autoannotate', methods=['POST'])
def endpoint_autoannotate():
    try:
        logger.debug("Auto Annotate API endpoint was called")
        data = {}
        if request.method == 'POST':
            post_data = request.json
            base_word = post_data["BASE_WORD"]
            entity = post_data["ENTITY"]
            is_done = auto_annotate(base_word, entity)
            if is_done:
                return {"status": "success", "response": "auto annotation completed"}, 200
            else:
                return {"status": "error", "response": "auto annotation failed"}, 400
        else:
            return {"status": "error", "response": "bad request!"}, 400
    except Exception as e:
        logger.exception(f"Exception occurred in the autoannotate endpoint. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400


# file navigation API
@blueprint.route('/navigation', methods=['GET'])
def endpoint_navigation():
    try:
        logger.debug("Navigation API endpoint was called")
        global LOOKUP_DIR
        data = {}
        if request.method == 'GET':
            data = get_valid_nlu_files()
            return JSONEncoder().encode(data)
        else:
            return {"status": "error", "response": "bad request!"}, 400
    except Exception as e:
        logger.exception(f"Exception occurred in the navigation endpoint. {e}")
        return {"status": "error", "response": "Error occurred while processing your request"}, 400
