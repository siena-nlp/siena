import json
import logging
from hashlib import sha256
from pathlib import Path
from typing import Text, Any
import os
import nltk
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from bson.objectid import ObjectId
from nltk.stem.porter import *
from ruamel import yaml
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import PreservedScalarString
import re

from siena.shared.constants import (
    ALLOWED_EXTENSIONS_KNOWLEDGE,
    ALLOWED_EXTENSIONS_NLU,
    COLUMN_NAME_BASE_WORD,
    COLUMN_NAME_COUNT,
    COLUMN_NAME_ENTITY,
    NLTK_WORDNET,
    NLTK_PUNKT,
    SIENA_KNOWLEDGE_BASE_PATH,
    SIENA_IN_PROGRESS_PATH,
    FilePermission,
    Encoding,
    SEP_TAG,
    NEW_LINE_TAG,
    SIENA_ENTITIES_PATH,
    SIENA_CONFIG_PATH,
    UNDEFINED_TAG,
    DEFAULT_NLU_YAML_TAG,
    DEFAULT_NLU_INTENT_TAG,
    DEFAULT_NLU_EXAMPLES_TAG,
    DEFAULT_NLU_YAML_VERSION,
    SIENA_TEMP_KNOWLEDGE_BASE_PATH,
    UPLOAD_FOLDER,
    LOOKUP_DIR,
    WELCOME_NLU_PATH,
    WELCOME_NLU,
    SIENA_CONFIG_INITIAL_TEMPLATE,
    INPROGRESS_INIT,
)

from siena.core.similarity import (
    base_form_convetor,
    generate_ngrams_sent,
    similarity,
)
from siena.utils.io import file_exists
logger = logging.getLogger(__name__)
en_stemmer = PorterStemmer()
nltk.download(NLTK_WORDNET, quiet=True)
nltk.download(NLTK_PUNKT, quiet=True)
yml = YAML()
yml.indent(mapping=2, sequence=4, offset=2)
yml.preserve_quotes = True
yml.explicit_start = False

knowledge = pd.DataFrame(columns=[COLUMN_NAME_BASE_WORD, COLUMN_NAME_ENTITY, COLUMN_NAME_COUNT])
siena_kb = Path(SIENA_KNOWLEDGE_BASE_PATH)
if siena_kb.is_file():
    knowledge = pd.read_csv(SIENA_KNOWLEDGE_BASE_PATH, index_col=0)
    knowledge.drop(knowledge[knowledge[COLUMN_NAME_COUNT] < 1].index, inplace=True)


class JSONEncoder(json.JSONEncoder):
    def default(self, o) -> Text:
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


def allowed_file_nlu(filename: Text) -> bool:
    r"""Checks for yaml file extension validation
    File name - name of the file want to check
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_NLU


def allowed_file_knowledge(filename: Text) -> Any:
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_KNOWLEDGE


def get_sentences(document_id, range_start, range_end) -> bool:
    logger.debug(f"get_sentences was called. (doc id: "
                 f"{document_id} start: {range_start} "
                 f"end: {range_end}")
    return True


def update_sentences_by_user(line_id, text, intent):
    with open(SIENA_IN_PROGRESS_PATH, FilePermission.READ, encoding=Encoding.UTF8) as file:
        try:
            document = file.readlines()
            document[line_id] = intent + SEP_TAG + text + NEW_LINE_TAG
        except Exception as e:
            logger.exception(f"Exception occurred. {e}")
            return False

    with open(SIENA_IN_PROGRESS_PATH, FilePermission.WRITE_PLUS, encoding=Encoding.UTF8) as file:
        try:
            file.writelines(document)
        except Exception as e:
            logger.exception(f"Exception occurred. {e}")
            return False
    return True


def delete_sentences(sentence_id) -> bool:
    logger.debug(f"delete_sentences was called. sentence id: {sentence_id}")
    return True


def read_yml(path_to_file, file_name) -> None:
    with open(SIENA_CONFIG_PATH, FilePermission.WRITE, encoding=Encoding.UTF8) as file:
        try:
            file.write(f"file_name={file_name}\nfile_path={path_to_file}\n")
        except Exception as e:
            logger.exception(f"Exception occurred. {e}")
    data = {}
    with open(path_to_file, FilePermission.READ, encoding=Encoding.UTF8) as stream:
        try:
            data = yaml.safe_load(stream)
            f = open(SIENA_IN_PROGRESS_PATH, FilePermission.WRITE_PLUS)
            f.write("")
            f.close()
        except yaml.YAMLError as e:
            logger.exception(f"Exception occurred. {e}")

    intents = data[DEFAULT_NLU_YAML_TAG]
    for single_intent in intents:
        intent = single_intent[DEFAULT_NLU_INTENT_TAG]
        examples = single_intent[DEFAULT_NLU_EXAMPLES_TAG].split(NEW_LINE_TAG)
        sentences = [i[2:] for i in examples]
        sentences = list(filter(lambda a: a != '', sentences))
        for sentence in sentences:
            line = intent + SEP_TAG + extract_entities(sentence)
            line = line.replace(NEW_LINE_TAG, '')
            with open(SIENA_IN_PROGRESS_PATH, FilePermission.APPEND_PLUS, encoding=Encoding.UTF8) as f:
                f.write(line + NEW_LINE_TAG)


def get_entities_by_project():
    entities = []
    # entity:value<sep>#color
    try:
        with open(SIENA_ENTITIES_PATH, FilePermission.READ, encoding=Encoding.UTF8) as file:
            while line := file.readline().rstrip():
                row = {}
                file_line = line.split(SEP_TAG)
                entity_name, entity_value = file_line[0].split(":")
                row["ENTITY_NAME"] = entity_name
                row["ENTITY_REPLACER"] = entity_value
                row["ENTITY_COLOR"] = file_line[1]
                entities.append(row)
    except Exception as e:
        logger.exception(f"Exception occurred. {e}")
    return entities


def update_knowledge(entity, highlighted_text):
    global knowledge
    base_word = base_form_convetor(highlighted_text)
    new_row = pd.DataFrame([[base_word, entity, 1]],
                           columns=[COLUMN_NAME_BASE_WORD, COLUMN_NAME_ENTITY, COLUMN_NAME_COUNT])
    knowledge = pd.concat([knowledge, new_row])
    knowledge = pd.DataFrame({COLUMN_NAME_COUNT: knowledge.groupby([COLUMN_NAME_BASE_WORD, COLUMN_NAME_ENTITY])[
        COLUMN_NAME_COUNT].sum()}).reset_index()
    knowledge.to_csv(SIENA_KNOWLEDGE_BASE_PATH)
    return True


def remove_entry_from_knowledge(entity, highlighted_text) -> bool:
    r"""Remove entry from knowledge
    entity - name of the file entity
    """
    global knowledge
    base_word = base_form_convetor(highlighted_text)
    locations_of_matching_base_word = knowledge.index[
        (knowledge[COLUMN_NAME_BASE_WORD] == base_word) & (knowledge[COLUMN_NAME_ENTITY] == entity)].tolist()
    for index in locations_of_matching_base_word:
        pointer = index - 1
        if knowledge.iloc[pointer, 2] > 0:
            knowledge.iloc[pointer, 2] = knowledge.iloc[pointer, 2] - 1
    knowledge.drop(knowledge[knowledge[COLUMN_NAME_COUNT] < 1].index, inplace=True)
    knowledge.to_csv(SIENA_KNOWLEDGE_BASE_PATH)
    return True


def get_suggestions(text: str):
    r"""Get suggestions for annotation
    text - text that want suggestions
    """
    text = text.strip()
    global knowledge
    entities = []
    try:
        with open(SIENA_ENTITIES_PATH, FilePermission.READ, encoding=Encoding.UTF8) as file:
            while line := file.readline().rstrip():
                file_line = line.split(SEP_TAG)
                row = file_line[0]  # name of entity
                entities.append(row)

        if len(entities) < 1:
            suggestions = []
            return suggestions
        entities_df = pd.DataFrame([])
        entities_df["default_entities"] = entities
        idx = knowledge.groupby([COLUMN_NAME_BASE_WORD])[COLUMN_NAME_COUNT].transform(max) == knowledge[
            COLUMN_NAME_COUNT]
        knowledge_filtered = knowledge[idx]

        stemmed_text = base_form_convetor(text)
        filtered_base_forms = list(knowledge_filtered[COLUMN_NAME_BASE_WORD])
        similarity_scores_of_base_words = []
        for base_word in filtered_base_forms:
            similarity_scores_of_base_words.append(similarity(stemmed_text, base_word))
        knowledge_filtered['similarity'] = similarity_scores_of_base_words
        # group by entity type
        knowledge_filtered.reset_index(drop=True, inplace=True)
        idx = knowledge_filtered.groupby([COLUMN_NAME_ENTITY])['similarity'].transform(max) == knowledge_filtered[
            'similarity']
        knowledge_filtered = knowledge_filtered[idx]
        knowledge_filtered_merged = pd.merge(
            entities_df,
            knowledge_filtered,
            left_on='default_entities',
            right_on=COLUMN_NAME_ENTITY, how='left'
        )
        knowledge_filtered_merged = knowledge_filtered_merged[["default_entities", "similarity"]]
        knowledge_filtered_merged_nona = knowledge_filtered_merged.dropna()
        knowledge_filtered_merged_na = knowledge_filtered_merged.loc[knowledge_filtered_merged['similarity'].isna()]
        nan_keys = list(knowledge_filtered_merged_na["default_entities"])
        nan_similarity = []
        for word in nan_keys:
            sim = similarity(text, word)
            nan_similarity.append(sim)
        knowledge_filtered_merged_na.loc[:, "similarity"] = nan_similarity

        # sorting
        knowledge_filtered_merged_nona = knowledge_filtered_merged_nona.sort_values('similarity', ascending=False)
        knowledge_filtered_merged_na = knowledge_filtered_merged_na.sort_values('similarity', ascending=False)
        knowledge_filtered_merged = pd.concat(
            [knowledge_filtered_merged_nona, knowledge_filtered_merged_na],
            ignore_index=True
        )
        suggestions = list(knowledge_filtered_merged["default_entities"])
        return suggestions
    except Exception as e:
        logger.exception(f"Exception occurred. {e}")
        return list()


def get_projects(user_id) -> bool:
    logger.debug(f"get_projects was called. user id: {user_id}")
    return True


def init_project(uploads: bool = True, exports: bool = True, cache: bool = True) -> bool:
    r"""Creates mandatory file and folders for SIENA
    None
    """
    if uploads:
        Path("uploads").mkdir(parents=True, exist_ok=True)
    if exports:
        Path("exports").mkdir(parents=True, exist_ok=True)
    if cache:
        Path("siena_cache").mkdir(parents=True, exist_ok=True)

    if not (os.path.isfile(WELCOME_NLU_PATH)):
        with open(WELCOME_NLU_PATH, FilePermission.WRITE, encoding=Encoding.UTF8) as file:
            file.write(WELCOME_NLU)

    if not (os.path.isfile(SIENA_CONFIG_PATH)):
        with open(SIENA_CONFIG_PATH, FilePermission.WRITE, encoding=Encoding.UTF8) as file:
            file.write(SIENA_CONFIG_INITIAL_TEMPLATE)

    fle = Path(SIENA_ENTITIES_PATH)
    fle.touch(exist_ok=True)

    if not (os.path.isfile(SIENA_IN_PROGRESS_PATH)):
        with open(SIENA_IN_PROGRESS_PATH, FilePermission.WRITE, encoding=Encoding.UTF8) as file:
            file.write(INPROGRESS_INIT)

    return True


def auto_annotate(base_form: str, entity: str) -> bool:
    global knowledge
    auto_annotate_count = 0

    # validate base_form
    if base_form not in list(knowledge[COLUMN_NAME_BASE_WORD]):
        return False
    base_form_token = base_form.split(" ")
    n = len(base_form_token)

    # loop start
    with open(SIENA_IN_PROGRESS_PATH, FilePermission.READ, encoding=Encoding.UTF8) as file:
        try:
            in_progress_text = file.readlines()
        except Exception as e:
            logger.exception(f"Exception occurred. {e}")
            return False
    if len(in_progress_text) <= 0:
        return False

    auto_annotated_text = []
    try:
        for line in in_progress_text:
            line_split = line.split(SEP_TAG)
            word_line = " ".join(str(line_split[1]).split())
            intent = " ".join(str(line_split[0]).split())

            soup = BeautifulSoup(word_line, 'html.parser')
            word_line = str(soup)
            div_list = soup.find_all("div", {"name": "highlighted"})
            key_list_ = {}

            for single_div in div_list:
                key_sha256 = sha256(single_div.encode(Encoding.UTF8)).hexdigest()
                key_list_[key_sha256] = str(single_div)
                word_line = word_line.replace(str(single_div), f' {key_sha256} ')

            word_line = " ".join(word_line.split())
            n_grams = generate_ngrams_sent(word_line, n)
            n_grams_len = len(n_grams) - 1
            re_word = ""
            auto_annotate_mapper = {}

            for index, element in enumerate(n_grams):
                if base_form == base_form_convetor(element):
                    auto_annotate_count += 1
                    tag = f"<div class='card-highlighted-text' name='highlighted' data='{entity}'>" \
                          f"{element}<span class='card-highlighted-text-close' style='visibility: hidden;'>" \
                          f"<i class='ms-Icon ms-Icon--ChromeClose ms-fontColor-white'></i></span> </div>"

                    sha_key = sha256(tag.encode(Encoding.UTF8)).hexdigest()
                    auto_annotate_mapper[sha_key] = tag
                    # replace element with sha key
                    element = sha_key
                if index == n_grams_len:
                    # last element
                    re_word = f"{re_word} {element}"
                else:
                    re_word = f"{re_word} {element.split()[0]}"

            # re-constructed word line with hash
            re_word = re_word.strip()
            re_word = " ".join(re_word.split())
            for hash_key, tag in key_list_.items():
                re_word = re_word.replace(hash_key, tag)
            for hash_key, tag in auto_annotate_mapper.items():
                re_word = re_word.replace(hash_key, tag)
            #
            auto_annotated_line = f"{intent}<sep>{re_word}"
            auto_annotated_text.append(auto_annotated_line)

        # update knowledge
        current_count = knowledge[knowledge[COLUMN_NAME_BASE_WORD] == base_form]
        current_count = int(current_count.iloc[0, 2])
        knowledge.loc[knowledge[COLUMN_NAME_BASE_WORD] == base_form, COLUMN_NAME_COUNT] = (
                current_count + auto_annotate_count)
        knowledge.to_csv(SIENA_KNOWLEDGE_BASE_PATH)

        # write to file
        # reset in-progress file
        with open(SIENA_IN_PROGRESS_PATH, FilePermission.WRITE_PLUS, encoding=Encoding.UTF8) as f:
            f.write("")

        # append to file
        for line in auto_annotated_text:
            line = line.replace(NEW_LINE_TAG, '')
            with open(SIENA_IN_PROGRESS_PATH, "a+", encoding=Encoding.UTF8) as f:
                f.write(line + NEW_LINE_TAG)
    except Exception as e:
        logger.error(f"Exception occurred in SIENA actions. More Info: {e}")
        return False
    return True


def create_project(user_id, project_name, project_type):
    logger.debug(f"create_project was called. uid: {user_id} proj name: {project_name} type: {project_type}")
    return True


def get_base_words() -> Any:
    global knowledge
    data = knowledge.drop(knowledge[knowledge[COLUMN_NAME_COUNT] < 1].index)
    data = data[[COLUMN_NAME_BASE_WORD, COLUMN_NAME_ENTITY]].to_dict('records')
    return data


def create_document(project_id, name) -> bool:
    logger.debug(f"create_doc was called. proj id: {project_id} name: {name}")
    return True


def insert_entities_for_project(entities):
    with open(SIENA_ENTITIES_PATH, FilePermission.WRITE, encoding=Encoding.UTF8) as file:
        text = ""
        try:
            for line in entities:
                row = line['ENTITY_NAME'] + \
                      ":" + \
                      line['ENTITY_REPLACER'] + \
                      SEP_TAG + line['ENTITY_COLOR'] + \
                      NEW_LINE_TAG
                if row not in text:
                    text += row
            file.write(text)
        except Exception as e:
            logger.exception(f"Exception occurred. {e}")
            return False
    return True


def get_files():
    data = []
    name = UNDEFINED_TAG
    with open(SIENA_CONFIG_PATH, FilePermission.READ, encoding=Encoding.UTF8) as file:
        while line := file.readline().rstrip():
            key_, value_ = line.split('=')
            if key_ == "file_name":
                name = value_
            else:
                continue
    data.append({'NAME': name})
    return data


def get_file_path():
    path = ""
    with open(SIENA_CONFIG_PATH, FilePermission.READ, encoding=Encoding.UTF8) as file:
        while line := file.readline().rstrip():
            key_, value_ = line.split('=')
            if key_ == "file_path":
                path = value_
            else:
                continue
    return path


def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


def save_data_to_domain_file() -> None:
    # ./domain.yml
    domain_file = "./domain.yml"
    data = {}
    with open(domain_file, FilePermission.READ, encoding=Encoding.UTF8) as stream:
        try:
            data = yaml.safe_load(stream)
        except Exception as e:
            logger.exception(f"Exception occurred. {e}")

    # in data obj => 'entities', 'slots'
    entities_text = ""
    with open(SIENA_ENTITIES_PATH, FilePermission.READ, encoding=Encoding.UTF8) as file:
        try:
            entities_text = file.read()
        except Exception as e:
            logger.exception(f"Exception occurred. {e}")
            pass
    entities_text = entities_text.strip()
    entity_lines = entities_text.split(NEW_LINE_TAG)

    slots = {}
    for line in entity_lines:
        entity_, color_ = line.split(SEP_TAG)
        entity, value_ = entity_.split(":")
        #
        slot_item = {}
        if entity not in slots.keys():
            slots[entity] = {}
            slot_item["type"] = "categorical"
            slot_item["values"] = [value_]
            slots[entity] = slot_item
        else:
            slot_item = slots[entity]
            slot_item["values"].append(value_)
            slots[entity] = slot_item

    data["slots"] = slots
    data["entities"] = list(slots.keys())
    with open(domain_file, FilePermission.WRITE_PLUS, encoding=Encoding.UTF8) as file:
        yml.dump(data, file)
        file.close()


def convert_files():
    try:
        data = {"version": DEFAULT_NLU_YAML_VERSION, "nlu": []}
        processed_yaml = {}
        entities_mapper = {}
        with open(SIENA_ENTITIES_PATH, FilePermission.READ, encoding=Encoding.UTF8) as file:
            try:
                text_data = file.readlines()
                for line in text_data:
                    entity, replacer = line.split(SEP_TAG)[0].split(":")
                    entities_mapper[entity] = replacer

            except Exception as e:
                logger.exception(f"Exception occurred. {e}")
                return False

        with open(SIENA_IN_PROGRESS_PATH, FilePermission.READ, encoding=Encoding.UTF8) as file:
            try:
                in_progress_text = file.readlines()
            except Exception as e:
                logger.exception(f"Exception occurred. {e}")
                return False

        for document_line in in_progress_text:
            intent, text = document_line.split(SEP_TAG)
            text = text.strip()
            intent = intent.strip()
            soup = BeautifulSoup(text, 'html.parser')
            input_tag = soup.find_all("div", {"name": "highlighted"})
            sentence = ""
            if len(input_tag) > 0:
                for tag in input_tag:
                    try:
                        line = str(soup)
                        attribute = tag.get('data')
                        entity_ = str(attribute).split(":")[0]
                        value_ = str(attribute).split(":")[1]
                        content = str(tag.text).strip()
                        # value_ = entities_mapper[attribute]  # replacer
                        # attribute = attribute.replace(f"{value_}:","")
                        data_values = f'"entity":"{entity_}","value":"{value_}"'
                        section = f'[{content}]{{{data_values}}} '
                        line = line.replace(str(tag), section, 1)
                        sentence = line
                    except Exception as e:
                        logger.exception(f"Exception occurred. {e}")
                        continue
            else:
                sentence = text

            sentence = " ".join(sentence.split())
            if intent in processed_yaml.keys():
                processed_yaml[intent] += f"- {sentence}\n"
            else:
                processed_yaml[intent] = f"- {sentence}\n"

        for key_, value_ in processed_yaml.items():
            section = {"intent": key_, "examples": PreservedScalarString(value_)}
            data["nlu"].append(section)

        file_path = get_file_path()

        with open(file_path, FilePermission.WRITE_PLUS, encoding=Encoding.UTF8) as file:
            yml.dump(data, file)
            file.close()

        # update domain file
        save_data_to_domain_file()

        return True
    except Exception as e:
        logger.exception(f"Exception occurred while saving NLU files. {e}")
        return False


def extract_entities(word):
    return_txt = word
    conjunction_points = [m.start() for m in re.finditer("]{", word)]
    for point in conjunction_points:
        annotated_word = ""
        entity = ""
        start = 0
        end = -1
        # find word -> backwards
        backward = list(range(point, -1, -1))
        for position in backward:
            if word[position] == "[":
                annotated_word = word[position + 1:point]
                start = position
                break

        # find entity -> forward
        forward = list(range(point, len(word), +1))
        for position in forward:
            if word[position] == "}":
                entity_obj = word[point + 1:position + 1]
                res = json.loads(entity_obj)
                entity = res["entity"]
                end = position + 1
                break
        template = f'<div class="card-highlighted-text" name="highlighted" data="{entity}">' \
                   f'{annotated_word}<span class="card-highlighted-text-close" style="visibility: ' \
                   f'hidden;"><i class="ms-Icon ms-Icon--ChromeClose ms-fontColor-white"></i></span>' \
                   f'</div>'
        phrase = word[start:end]
        return_txt = return_txt.replace(phrase, template)
    return return_txt

def validate_tempory_knowledge_base() -> bool:
    global knowledge
    try:
        columns = np.array([COLUMN_NAME_BASE_WORD, COLUMN_NAME_ENTITY, COLUMN_NAME_COUNT])
        knowledge_temp = pd.read_csv(SIENA_TEMP_KNOWLEDGE_BASE_PATH, index_col=0)
        if knowledge_temp.shape[0] <= 0:
            # Gives number of rows
            return False

        if knowledge.shape[1] != knowledge_temp.shape[1]:
            # Gives number of columns
            return False

        columns_temp = np.array(knowledge_temp.columns.values.tolist())
        result = list(columns_temp == columns)
        if False in result:
            return False
        else:
            if file_exists(SIENA_KNOWLEDGE_BASE_PATH):
                os.remove(SIENA_KNOWLEDGE_BASE_PATH)

            os.rename(SIENA_TEMP_KNOWLEDGE_BASE_PATH, SIENA_KNOWLEDGE_BASE_PATH)
            knowledge = knowledge_temp
            return True

    except Exception as e:
        logger.exception(f"Exception occurred. {e}")
        return False


def get_knowledge_base_text():
    with open(SIENA_KNOWLEDGE_BASE_PATH, FilePermission.READ, encoding=Encoding.UTF8) as file:
        try:
            knowledge_base = file.readlines()
            return knowledge_base
        except Exception as e:
            logger.exception(f"Exception occurred. {e}")
            return False


def is_valid_nlu_yaml(path_to_file):
    with open(path_to_file, FilePermission.READ, encoding=Encoding.UTF8) as stream:
        try:
            data = yaml.safe_load(stream)
            if type(data) is not dict:
                return False
            if DEFAULT_NLU_YAML_TAG in data.keys():
                if data[DEFAULT_NLU_YAML_TAG] != None:
                    return True
        except yaml.YAMLError as e:
            logger.exception(f"Exception occurred. {e}")
            return False
    return False

def get_valid_nlu_files():
        data = {}
        data["FILES"] = []
        # in bot folder
        for root, dir_names, filenames in os.walk(LOOKUP_DIR):
            for filename in filenames:
                if filename.endswith(('.YAML', '.YML', '.yaml', '.yml')):
                    files = {}
                    abs_path = os.path.join(root, filename)
                    rel_path = abs_path.replace("\\", "/")
                    if not is_valid_nlu_yaml(rel_path):
                        continue
                    files["PATH"] = rel_path
                    files["NAME"] = filename
                    data["FILES"].append(files)
        # in uploads folder
        for root, dir_names, filenames in os.walk(UPLOAD_FOLDER):
            for filename in filenames:
                if filename.endswith(('.YAML', '.YML', '.yaml', '.yml')):
                    files = {}
                    abs_path = os.path.join(root, filename)
                    rel_path = abs_path.replace("\\", "/")
                    if not is_valid_nlu_yaml(rel_path):
                        continue
                    files["PATH"] = rel_path
                    files["NAME"] = filename
                    data["FILES"].append(files)

        return data


def delete_entity(nlu_files:list,entity:str,value:str)->None:
    print("SECTION STARTED")
    phrase_e ='{"entity":"'+entity+'","value":"'+value+'"}'
    phrase = "\[.*]" + phrase_e
    for file in nlu_files:
        file_ = file["PATH"]
        document = ""
        with open(file_, FilePermission.READ, encoding=Encoding.UTF8) as fileio:
            try:
                # read
                document = fileio.read()
            except Exception as e:
                logger.exception(f"Exception occurred. {e}")
        # write
        findings = re.findall(phrase, document)
        for find_ in findings:
            word = find_.replace(phrase_e,"")
            word = word.replace("[","")
            word = word.replace("]","")
            document = document.replace(find_,word)
        with open(file_, FilePermission.WRITE, encoding=Encoding.UTF8) as fileio:
            try:
                fileio.write(document)
            except Exception as e:
                logger.exception(f"Exception occurred. {e}")

    # delete from kb
    global knowledge
    knowledge = knowledge.drop(knowledge[knowledge[COLUMN_NAME_ENTITY] == f"{entity}:{value}"].index)
    knowledge.to_csv(SIENA_KNOWLEDGE_BASE_PATH)
    # delete from entity file
    # read
    data = get_entities_by_project()
    data_ = []
    for line in data:
        if (line["ENTITY_NAME"] == entity) and (line["ENTITY_REPLACER"] == value):
            pass
        else:
            data_.append(line)   
    insert_entities_for_project(data_)
