from html import entities
import string
from hashlib import sha256
from time import time
from ruamel.yaml import YAML
from ruamel import yaml
from ruamel.yaml.scalarstring import PreservedScalarString as pss
import re
import os
try:
    import DB.connection as db_conn
except:
    import siena.server.DB.connection as db_conn

from bson.objectid import ObjectId
from bson.timestamp import Timestamp
import json
import datetime as dt
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import math
import nltk
nltk.download('wordnet')
nltk.download('punkt')
# from sinling import SinhalaStemmer
# si_stemmer = SinhalaStemmer()
# from sinling import SinhalaTokenizer
# si_tokenizer = SinhalaTokenizer()
from nltk.stem.porter import *
en_stemmer = PorterStemmer()

knowledge = pd.DataFrame(columns=["base_word","entity_name","count"])
if "knowledge_base.csv" in os.listdir("./"):
    knowledge = pd.read_csv("knowledge_base.csv",index_col=0)

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

yml = YAML()
yml.indent(mapping=2, sequence=4, offset=2)
yml.preserve_quotes = True
yml.explicit_start = False


def get_sentences(document_id,rangeStart,rangeEnd):
    document_id = ObjectId(document_id)
    SENTENCE = db_conn.get_connection().SENTENCE.find(
        {
            "$and":[ {"DOCUMENT_ID": document_id}, {"SENTENCE_NUMBER":{"$lte":rangeEnd}},{"SENTENCE_NUMBER":{"$gte":rangeStart}}]
        }
    )
    return list(SENTENCE)

def update_sentences_by_user(line_id, text,intent):
    document = []
    with open("inprogress.SIENA", "r", encoding='utf-8') as file:
        try:
            document = file.readlines()
            document[line_id] = intent + "<sep>" + text + '\n'
        except Exception as e:
            print(e)
            return False
    
    with open("inprogress.SIENA", "w", encoding='utf-8') as file:
        try:
            file.writelines(document)
        except Exception as e:
            print(e)
            return False
    return True

def delete_sentences(sentence_id):
    SENTENCE = db_conn.get_connection().SENTENCE
    query = { "_id": ObjectId(sentence_id) }
    SENTENCE.delete_one(query)
    return True

def read_yml(path_to_file,file_name):
    with open("config.SIENA", "w", encoding='utf-8') as file:
        try:
            file.write(f"file_name={file_name}\nfile_path={path_to_file}\n")
        except Exception as exc:
            print(exc)
    data = {}
    with open(path_to_file, "r", encoding='utf-8') as stream:
        try:
            data = yaml.safe_load(stream)
            f = open("inprogress.SIENA", "w")
            f.write("")
            f.close()
        except yaml.YAMLError as exc:
            print(exc)

    intents = data["nlu"]
    for single_intent in intents:
        intent = single_intent['intent']
        examples = single_intent['examples'].split('\n')
        sentences = [i[2:] for i in examples]
        sentences = list(filter(lambda a: a != '', sentences))
        for sentence in sentences:
            # for ch in ['(',')','[',']','{','}']:
            #     if ch in sentence:
            #         sentence=sentence.replace(ch,"")
            line = intent + "<sep>" + extract_entities(sentence)
            line = line.replace('\n','')
            with open("inprogress.SIENA", "a", encoding="utf-8") as f:
                f.write(line+"\n")


def get_entities_by_project():
    ENTITIES = []
    try:
        with open("entities.SIENA", encoding='utf-8') as file:
            line_id = 1
            while (line := file.readline().rstrip()):
                row = {}
                file_line = line.split('<sep>')
                row["ENTITY_NAME"]=file_line[0]
                row["ENTITY_REPLACER"]=file_line[1]
                row["ENTITY_COLOR"]=file_line[2]
                ENTITIES.append(row)
    except Exception as e:
        print(e)
        pass
    return ENTITIES

def update_knowledge(entity,highlighted_text):
    global knowledge
    base_word = base_form_convetor(highlighted_text)
    new_row = pd.DataFrame([[base_word,entity,1]], columns=["base_word","entity_name","count"])
    knowledge = pd.concat([knowledge, new_row])
    knowledge = pd.DataFrame({'count' : knowledge.groupby( ["base_word","entity_name"] )["count"].sum()}).reset_index()
    knowledge.to_csv("./knowledge_base.csv")
    return True

def remove_entry_from_knowledge(entity,highlighted_text):
    global knowledge
    base_word = base_form_convetor(highlighted_text)
    locations_of_matching_base_word = knowledge.index[(knowledge['base_word'] == base_word) & (knowledge['entity_name'] == entity)].tolist()
    for index in locations_of_matching_base_word:
        if knowledge.iloc[index,2] > 0:
            knowledge.iloc[index,2] = knowledge.iloc[index,2] - 1
    knowledge.to_csv("./knowledge_base.csv")
    return True

def get_suggestions(text):
    text = text.strip()
    global knowledge
    ENTITIES = []
    try:
        with open("entities.SIENA", encoding='utf-8') as file:
            while (line := file.readline().rstrip()):
                row = {}
                file_line = line.split('<sep>')
                row=file_line[0] #name of entity
                ENTITIES.append(row)  
    except Exception as e:
        print(e)
        pass 
    ENTITIES_DF = pd.DataFrame([])
    ENTITIES_DF["default_entities"] = ENTITIES
    idx = knowledge.groupby(['base_word'])['count'].transform(max) == knowledge['count']
    knowledge_filterd = knowledge[idx]

    stemmed_text = base_form_convetor(text)
    filterd_base_forms = list(knowledge_filterd["base_word"])
    similarity_scores_of_base_words=[]
    for base_word in filterd_base_forms:
        similarity_scores_of_base_words.append(similarity(stemmed_text,base_word))
    knowledge_filterd['similarity'] = similarity_scores_of_base_words
    # group by entity type
    knowledge_filterd.reset_index(drop=True, inplace=True)
    idx = knowledge_filterd.groupby(['entity_name'])['similarity'].transform(max) == knowledge_filterd['similarity']
    knowledge_filterd = knowledge_filterd[idx]
    knowledge_filterd_merged = pd.merge(ENTITIES_DF,knowledge_filterd,left_on='default_entities',right_on='entity_name',how='left')
    knowledge_filterd_merged = knowledge_filterd_merged.fillna(0)
    knowledge_filterd_merged = knowledge_filterd_merged.sort_values('similarity',ascending=False)
    suggestions = list(knowledge_filterd_merged["default_entities"])
    return suggestions

def get_projects(userId):
    data = []
    cursor = db_conn.get_connection().PROJECT.find({"USER_ID": ObjectId(userId)})
    data = list(cursor)
    for index in range(len(data)):
        data[index]['CREATED_AT'] = str(data[index]['CREATED_AT'])

    return data

def auto_annotate(base_form,entity):
    base_form_token = base_form.split(" ")
    n=len(base_form_token)
    # loop start
    inprogress_text = []
    with open("inprogress.SIENA", "r", encoding='utf-8') as file:
        try:
            inprogress_text = file.readlines()
        except Exception as e:
            print(e)
            return False
    if len(inprogress_text) <= 0:
        return False
    
    auto_annotated_text = []

    for line in inprogress_text:
        line_splitted = line.split('<sep>')
        wordline =  " ".join(str(line_splitted[1]).split())
        intent = " ".join(str(line_splitted[0]).split())
        
        soup = BeautifulSoup(wordline, 'html.parser')
        wordline = str(soup)
        div_list = soup.find_all("div",{"name" : "highlighted"})
        key_list = {}
        for single_div in div_list:
            key_sha256 = sha256(single_div.encode('utf-8')).hexdigest()
            key_list[key_sha256] = str(single_div)
            wordline = wordline.replace(str(single_div),f' {key_sha256} ')

        wordline = " ".join(wordline.split())
        n_grams = generate_ngrams_sent(wordline,n)
        n_grams_len = len(n_grams)-1
        re_word = ""
        auto_annotate_mapper = {}
        for index, element in enumerate(n_grams):
            if base_form == base_form_convetor(element):
                tag = f"<div class='card-highlighted-text' name='highlighted' data='{entity}'>{element}<span class='card-highlighted-text-close' style='visibility: hidden;'><i class='ms-Icon ms-Icon--ChromeClose ms-fontColor-white'></i></span> </div>"
                sha_key = sha256(tag.encode('utf-8')).hexdigest()
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
        for hash_key,tag in key_list.items():
            re_word = re_word.replace(hash_key,tag)
        for hash_key , tag in auto_annotate_mapper.items():
            re_word = re_word.replace(hash_key,tag)
        # 
        auto_annotated_line = f"{intent}<sep>{re_word}"
        auto_annotated_text.append(auto_annotated_line)

    # write to file
    # reset inprogress file
    with open("inprogress.SIENA", "w", encoding="utf-8") as f:
        f.write("")
    # append to file
    for line in auto_annotated_text:
        line = line.replace('\n','')
        with open("inprogress.SIENA", "a", encoding="utf-8") as f:
            f.write(line+"\n")
    return True

def create_project(user_id,project_name,project_type):
    data = {}
    data["USER_ID"]= ObjectId(user_id)
    data["NAME"]=project_name
    data["TYPE"]=project_type
    data["CREATED_AT"]= Timestamp(int(dt.datetime.today().timestamp()), 1)
    _id = ""
    try:
        _id =db_conn.get_connection().PROJECT.insert_one(data)
    except Exception:
        return False
    return _id.inserted_id

def get_base_words():
    global knowledge
    data = knowledge[['base_word','entity_name']].to_dict('records')
    return data

def create_document(project_id,name):
    data = {}
    data["USER_ID"]= ObjectId(project_id)
    data["NAME"]=name
    try:
        _id =db_conn.get_connection().PROJECT.insert_one(data)
    except Exception:
        return False
    return _id.inserted_id


def insert_entities_for_project(entities):
    with open("entities.SIENA", "w", encoding='utf-8') as file:
        text = ""
        try:
            for line in entities:
                text+=line['ENTITY_NAME']+"<sep>"+line['ENTITY_REPLACER']+"<sep>"+line['ENTITY_COLOR']+"\n"
            file.write(text)
        except Exception as e:
            print("ERROR=",e)
            return False
    return True

def get_files():
    data = []
    name = "undefined"
    with open("config.SIENA", encoding='utf-8') as file:
        while (line := file.readline().rstrip()):
            key,value = line.split('=')
            if key == "file_name":
                name = value
            else:
                continue
    data.append({'NAME':name})
    return data

def get_file_path():
    path = ""
    with open("config.SIENA", encoding='utf-8') as file:
        while (line := file.readline().rstrip()):
            key,value = line.split('=')
            if key == "file_path":
                path = value
            else:
                continue
    return path

def str_presenter(dumper, data):
  if len(data.splitlines()) > 1:  # check for multiline string
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
  return dumper.represent_scalar('tag:yaml.org,2002:str', data)

def convert_files():
    data = {}
    data["version"] = "2.0"
    data["nlu"] = []
    processed_yaml = {}
    file_name = get_files()[0]['NAME']
    inprogress_text = []
    entities_mapper = {}
    with open("entities.SIENA", "r", encoding='utf-8') as file:
        try:
            text_data = file.readlines()
            for line in text_data:
                entity , replacer , color = line.split('<sep>')
                entities_mapper[entity] = replacer

        except Exception as e:
            print(e)
            return False
    
    with open("inprogress.SIENA", "r", encoding='utf-8') as file:
        try:
            inprogress_text = file.readlines()
        except Exception as e:
            print(e)
            return False

    formatted_text = []

    for document_line in inprogress_text:
        intent , text = document_line.split('<sep>')
        text = text.strip()
        intent = intent.strip()
        soup = BeautifulSoup(text, 'html.parser')
        input_tag = soup.find_all("div",{"name" : "highlighted"})
        sentence = ""
        if len(input_tag) > 0:
            for tag in input_tag:
                try:
                    line = str(soup)
                    attribute = tag.get('data')
                    content = str(tag.text).strip()
                    value = entities_mapper[attribute] #replacer
                    data_values = f'"entity":"{attribute}","value":"{value}"'
                    section = f'[{content}]{{{data_values}}} '
                    line = line.replace(str(tag), section, 1)
                    sentence = line
                except:
                    continue
        else:
            sentence = text

        sentence = " ".join(sentence.split())
        # sentence = pss(sentence)
        # if intent in processed_yaml.keys():
        #     processed_yaml[intent].append(sentence)
        # else:
        #     processed_yaml[intent] = [sentence]
        if intent in processed_yaml.keys():
            processed_yaml[intent] += f"- {sentence}\n"
        else:
            processed_yaml[intent] = f"- {sentence}\n"

    for key,value in processed_yaml.items():
        section = {}
        section["intent"] = key
        section["examples"] = pss(value)
        data["nlu"].append(section)

    file_path = get_file_path()

    with open(file_path, "w+", encoding='utf-8') as file:
        yml.dump(data, file)
        file.close()
        

    # changing file again
    # yaml_lines = []
    # with open(file_path, "r", encoding='utf-8') as file:
    #     try:
    #         yaml_lines = file.readlines()
    #     except Exception as e:
    #         print(e)
    #         return False

    # yaml_lines_copy = list(yaml_lines)
    # i = 0
    # for line in yaml_lines:
    #     if "examples:" in line:
    #         line = line.replace("\n","")
    #         yaml_lines_copy[i] = f"{line} |\n"
    #     i += 1

    # # rewrite changes
    # with open(file_path, "w",encoding='utf-8') as fp:
    #     for item in yaml_lines_copy:
    #         fp.write("%s" % item)


    return True

ALLOWED_EXTENSIONS_KNOWLEDGE = {'csv', 'CSV'}

def allowed_file_knowledge(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_KNOWLEDGE


def extract_entities(word):
    return_txt = word
    conjunction_points = [m.start() for m in re.finditer("]{", word)]
    conjunction_points
    for point in conjunction_points:
        annotated_word = ""
        entity = ""
        start = 0
        end = -1
        # find word -> backwards
        backward = list(range(point,-1,-1))
        for position in backward:
            if word[position] == "[":
                annotated_word = word[position+1:point]
                start = position
                break

        # find entity -> forward 
        forward = list(range(point,len(word),+1))
        for position in forward:
            if word[position] == "}":
                res = {}
                entity_obj = word[point+1:position+1]
                res = json.loads(entity_obj)
                entity = res["entity"]
                end = position+1
                break
        template = f'<div class="card-highlighted-text" name="highlighted" data="{entity}">{annotated_word}<span class="card-highlighted-text-close" style="visibility: hidden;"><i class="ms-Icon ms-Icon--ChromeClose ms-fontColor-white"></i></span></div>'
        phrase = word[start:end]
        return_txt = return_txt.replace(phrase,template)
    return return_txt


"""
-- Algorithms --
1. SIENA reverse stemming
2.
3.
"""
vowels_mapper = {
'':'',
'අ':'අ',
'ආ':'ආ',
'ඇ':'ඇ',
'ඈ':'ඈ',
'ඉ':'ඉ',
'ඊ':'ඊ',
'උ':'උ',
'ඌ':'ඌ',
'ර්උ':'ර්උ',
'ර්ඌ':'ර්ඌ',
'ඖ':'ඖ',
'එ':'එ',
'ඒ':'ඒ',
'ඓ':'ඓ',
'ඔ':'ඔ',
'ඕ':'ඕ',
'අං':'අං',
'අඃ':'අඃ',
'ර්':'ර්',
'ර':'ර්අ',
'ය':'ය්අ',
'ක්':'ක්',
'ක':'ක්අ',
'කා':'ක්ආ',
'කැ':'ක්ඇ',
'කෑ':'ක්ඈ',
'කි':'ක්ඉ',
'කී':'ක්ඊ',
'කු':'ක්උ',
'කූ':'ක්ඌ',
'කෘ':'ක්ර්උ',
'කෲ':'ක්ර්ඌ',
'කෟ':'ක්ඖ',
'කෳ':'ක්ඖ',
'කෙ':'ක්එ',
'කේ':'ක්ඒ',
'කෛ':'ක්ඓ',
'කො':'ක්ඔ',
'කෝ':'ක්ඕ',
'කෞ':'ක්ඖ',
'කං':'ක්අං',
'කඃ':'ක්අඃ',
'ර්‍ක':'ර්ක්',
'ක්‍ර':'ක්ර',
'ක්‍ය':'ක්ය',
'ඛ්':'ඛ්',
'ඛ':'ඛ්අ',
'ඛා':'ඛ්ආ',
'ඛැ':'ඛ්ඇ',
'ඛෑ':'ඛ්ඈ',
'ඛි':'ඛ්ඉ',
'ඛී':'ඛ්ඊ',
'ඛු':'ඛ්උ',
'ඛූ':'ඛ්ඌ',
'ඛෘ':'ඛ්ර්උ',
'ඛෲ':'ඛ්ර්ඌ',
'ඛෟ':'ඛ්ඖ',
'ඛෳ':'ඛ්ඖ',
'ඛෙ':'ඛ්එ',
'ඛේ':'ඛ්ඒ',
'ඛෛ':'ඛ්ඓ',
'ඛො':'ඛ්ඔ',
'ඛෝ':'ඛ්ඕ',
'ඛෞ':'ඛ්ඖ',
'ඛං':'ඛ්අං',
'ඛඃ':'ඛ්අඃ',
'ර්‍ඛ':'ර්ඛ්',
'ඛ්‍ර':'ඛ්ර',
'ඛ්‍ය':'ඛ්ය',
'ග්':'ග්',
'ග':'ග්අ',
'ගා':'ග්ආ',
'ගැ':'ග්ඇ',
'ගෑ':'ග්ඈ',
'ගි':'ග්ඉ',
'ගී':'ග්ඊ',
'ගු':'ග්උ',
'ගූ':'ග්ඌ',
'ගෘ':'ග්ර්උ',
'ගෲ':'ග්ර්ඌ',
'ගෟ':'ග්ඖ',
'ගෳ':'ග්ඖ',
'ගෙ':'ග්එ',
'ගේ':'ග්ඒ',
'ගෛ':'ග්ඓ',
'ගො':'ග්ඔ',
'ගෝ':'ග්ඕ',
'ගෞ':'ග්ඖ',
'ගං':'ග්අං',
'ගඃ':'ග්අඃ',
'ර්‍ග':'ර්ග්',
'ග්‍ර':'ග්ර',
'ග්‍ය':'ග්ය',
'ඝ්':'ඝ්',
'ඝ':'ඝ්අ',
'ඝා':'ඝ්ආ',
'ඝැ':'ඝ්ඇ',
'ඝෑ':'ඝ්ඈ',
'ඝි':'ඝ්ඉ',
'ඝී':'ඝ්ඊ',
'ඝු':'ඝ්උ',
'ඝූ':'ඝ්ඌ',
'ඝෘ':'ඝ්ර්උ',
'ඝෲ':'ඝ්ර්ඌ',
'ඝෟ':'ඝ්ඖ',
'ඝෳ':'ඝ්ඖ',
'ඝෙ':'ඝ්එ',
'ඝේ':'ඝ්ඒ',
'ඝෛ':'ඝ්ඓ',
'ඝො':'ඝ්ඔ',
'ඝෝ':'ඝ්ඕ',
'ඝෞ':'ඝ්ඖ',
'ඝං':'ඝ්අං',
'ඝඃ':'ඝ්අඃ',
'ර්‍ඝ':'ර්ඝ්',
'ඝ්‍ර':'ඝ්ර',
'ඝ්‍ය':'ඝ්ය',
'ඞ්':'ඞ්',
'ඞ':'ඞ්අ',
'ඞා':'ඞ්ආ',
'ඞැ':'ඞ්ඇ',
'ඞෑ':'ඞ්ඈ',
'ඞි':'ඞ්ඉ',
'ඞී':'ඞ්ඊ',
'ඞු':'ඞ්උ',
'ඞූ':'ඞ්ඌ',
'ඞෘ':'ඞ්ර්උ',
'ඞෲ':'ඞ්ර්ඌ',
'ඞෟ':'ඞ්ඖ',
'ඞෳ':'ඞ්ඖ',
'ඞෙ':'ඞ්එ',
'ඞේ':'ඞ්ඒ',
'ඞෛ':'ඞ්ඓ',
'ඞො':'ඞ්ඔ',
'ඞෝ':'ඞ්ඕ',
'ඞෞ':'ඞ්ඖ',
'ඞං':'ඞ්අං',
'ඞඃ':'ඞ්අඃ',
'ර්‍ඞ':'ර්ඞ්',
'ඞ්‍ර':'ඞ්ර',
'ඞ්‍ය':'ඞ්ය',
'ඟ්':'ඟ්',
'ඟ':'ඟ්අ',
'ඟා':'ඟ්ආ',
'ඟැ':'ඟ්ඇ',
'ඟෑ':'ඟ්ඈ',
'ඟි':'ඟ්ඉ',
'ඟී':'ඟ්ඊ',
'ඟු':'ඟ්උ',
'ඟූ':'ඟ්ඌ',
'ඟෘ':'ඟ්ර්උ',
'ඟෲ':'ඟ්ර්ඌ',
'ඟෟ':'ඟ්ඖ',
'ඟෳ':'ඟ්ඖ',
'ඟෙ':'ඟ්එ',
'ඟේ':'ඟ්ඒ',
'ඟෛ':'ඟ්ඓ',
'ඟො':'ඟ්ඔ',
'ඟෝ':'ඟ්ඕ',
'ඟෞ':'ඟ්ඖ',
'ඟං':'ඟ්අං',
'ඟඃ':'ඟ්අඃ',
'ර්‍ඟ':'ර්ඟ්',
'ඟ්‍ර':'ඟ්ර',
'ඟ්‍ය':'ඟ්ය',
'ච්':'ච්',
'ච':'ච්අ',
'චා':'ච්ආ',
'චැ':'ච්ඇ',
'චෑ':'ච්ඈ',
'චි':'ච්ඉ',
'චී':'ච්ඊ',
'චු':'ච්උ',
'චූ':'ච්ඌ',
'චෘ':'ච්ර්උ',
'චෲ':'ච්ර්ඌ',
'චෟ':'ච්ඖ',
'චෳ':'ච්ඖ',
'චෙ':'ච්එ',
'චේ':'ච්ඒ',
'චෛ':'ච්ඓ',
'චො':'ච්ඔ',
'චෝ':'ච්ඕ',
'චෞ':'ච්ඖ',
'චං':'ච්අං',
'චඃ':'ච්අඃ',
'ර්‍ච':'ර්ච්',
'ච්‍ර':'ච්ර',
'ච්‍ය':'ච්ය',
'ඡ්':'ඡ්',
'ඡ':'ඡ්අ',
'ඡා':'ඡ්ආ',
'ඡැ':'ඡ්ඇ',
'ඡෑ':'ඡ්ඈ',
'ඡි':'ඡ්ඉ',
'ඡී':'ඡ්ඊ',
'ඡු':'ඡ්උ',
'ඡූ':'ඡ්ඌ',
'ඡෘ':'ඡ්ර්උ',
'ඡෲ':'ඡ්ර්ඌ',
'ඡෟ':'ඡ්ඖ',
'ඡෳ':'ඡ්ඖ',
'ඡෙ':'ඡ්එ',
'ඡේ':'ඡ්ඒ',
'ඡෛ':'ඡ්ඓ',
'ඡො':'ඡ්ඔ',
'ඡෝ':'ඡ්ඕ',
'ඡෞ':'ඡ්ඖ',
'ඡං':'ඡ්අං',
'ඡඃ':'ඡ්අඃ',
'ර්‍ඡ':'ර්ඡ්',
'ඡ්‍ර':'ඡ්ර',
'ඡ්‍ය':'ඡ්ය',
'ජ්':'ජ්',
'ජ':'ජ්අ',
'ජා':'ජ්ආ',
'ජැ':'ජ්ඇ',
'ජෑ':'ජ්ඈ',
'ජි':'ජ්ඉ',
'ජී':'ජ්ඊ',
'ජු':'ජ්උ',
'ජූ':'ජ්ඌ',
'ජෘ':'ජ්ර්උ',
'ජෲ':'ජ්ර්ඌ',
'ජෟ':'ජ්ඖ',
'ජෳ':'ජ්ඖ',
'ජෙ':'ජ්එ',
'ජේ':'ජ්ඒ',
'ජෛ':'ජ්ඓ',
'ජො':'ජ්ඔ',
'ජෝ':'ජ්ඕ',
'ජෞ':'ජ්ඖ',
'ජං':'ජ්අං',
'ජඃ':'ජ්අඃ',
'ර්‍ජ':'ර්ජ්',
'ජ්‍ර':'ජ්ර',
'ජ්‍ය':'ජ්ය',
'ඣ්':'ඣ්',
'ඣ':'ඣ්අ',
'ඣා':'ඣ්ආ',
'ඣැ':'ඣ්ඇ',
'ඣෑ':'ඣ්ඈ',
'ඣි':'ඣ්ඉ',
'ඣී':'ඣ්ඊ',
'ඣු':'ඣ්උ',
'ඣූ':'ඣ්ඌ',
'ඣෘ':'ඣ්ර්උ',
'ඣෲ':'ඣ්ර්ඌ',
'ඣෟ':'ඣ්ඖ',
'ඣෳ':'ඣ්ඖ',
'ඣෙ':'ඣ්එ',
'ඣේ':'ඣ්ඒ',
'ඣෛ':'ඣ්ඓ',
'ඣො':'ඣ්ඔ',
'ඣෝ':'ඣ්ඕ',
'ඣෞ':'ඣ්ඖ',
'ඣං':'ඣ්අං',
'ඣඃ':'ඣ්අඃ',
'ර්‍ඣ':'ර්ඣ්',
'ඣ්‍ර':'ඣ්ර',
'ඣ්‍ය':'ඣ්ය',
'ඤ්':'ඤ්',
'ඤ':'ඤ්අ',
'ඤා':'ඤ්ආ',
'ඤැ':'ඤ්ඇ',
'ඤෑ':'ඤ්ඈ',
'ඤි':'ඤ්ඉ',
'ඤී':'ඤ්ඊ',
'ඤු':'ඤ්උ',
'ඤූ':'ඤ්ඌ',
'ඤෘ':'ඤ්ර්උ',
'ඤෲ':'ඤ්ර්ඌ',
'ඤෟ':'ඤ්ඖ',
'ඤෳ':'ඤ්ඖ',
'ඤෙ':'ඤ්එ',
'ඤේ':'ඤ්ඒ',
'ඤෛ':'ඤ්ඓ',
'ඤො':'ඤ්ඔ',
'ඤෝ':'ඤ්ඕ',
'ඤෞ':'ඤ්ඖ',
'ඤං':'ඤ්අං',
'ඤඃ':'ඤ්අඃ',
'ර්‍ඤ':'ර්ඤ්',
'ඤ්‍ර':'ඤ්ර',
'ඤ්‍ය':'ඤ්ය',
'ඥ්':'ඥ්',
'ඥ':'ඥ්අ',
'ඥා':'ඥ්ආ',
'ඥැ':'ඥ්ඇ',
'ඥෑ':'ඥ්ඈ',
'ඥි':'ඥ්ඉ',
'ඥී':'ඥ්ඊ',
'ඥු':'ඥ්උ',
'ඥූ':'ඥ්ඌ',
'ඥෘ':'ඥ්ර්උ',
'ඥෲ':'ඥ්ර්ඌ',
'ඥෟ':'ඥ්ඖ',
'ඥෳ':'ඥ්ඖ',
'ඥෙ':'ඥ්එ',
'ඥේ':'ඥ්ඒ',
'ඥෛ':'ඥ්ඓ',
'ඥො':'ඥ්ඔ',
'ඥෝ':'ඥ්ඕ',
'ඥෞ':'ඥ්ඖ',
'ඥං':'ඥ්අං',
'ඥඃ':'ඥ්අඃ',
'ර්‍ඥ':'ර්ඥ්',
'ඥ්‍ර':'ඥ්ර',
'ඥ්‍ය':'ඥ්ය',
'ඦ්':'ඦ්',
'ඦ':'ඦ්අ',
'ඦා':'ඦ්ආ',
'ඦැ':'ඦ්ඇ',
'ඦෑ':'ඦ්ඈ',
'ඦි':'ඦ්ඉ',
'ඦී':'ඦ්ඊ',
'ඦු':'ඦ්උ',
'ඦූ':'ඦ්ඌ',
'ඦෘ':'ඦ්ර්උ',
'ඦෲ':'ඦ්ර්ඌ',
'ඦෟ':'ඦ්ඖ',
'ඦෳ':'ඦ්ඖ',
'ඦෙ':'ඦ්එ',
'ඦේ':'ඦ්ඒ',
'ඦෛ':'ඦ්ඓ',
'ඦො':'ඦ්ඔ',
'ඦෝ':'ඦ්ඕ',
'ඦෞ':'ඦ්ඖ',
'ඦං':'ඦ්අං',
'ඦඃ':'ඦ්අඃ',
'ර්‍ඦ':'ර්ඦ්',
'ඦ්‍ර':'ඦ්ර',
'ඦ්‍ය':'ඦ්ය',
'ට්':'ට්',
'ට':'ට්අ',
'ටා':'ට්ආ',
'ටැ':'ට්ඇ',
'ටෑ':'ට්ඈ',
'ටි':'ට්ඉ',
'ටී':'ට්ඊ',
'ටු':'ට්උ',
'ටූ':'ට්ඌ',
'ටෘ':'ට්ර්උ',
'ටෲ':'ට්ර්ඌ',
'ටෟ':'ට්ඖ',
'ටෳ':'ට්ඖ',
'ටෙ':'ට්එ',
'ටේ':'ට්ඒ',
'ටෛ':'ට්ඓ',
'ටො':'ට්ඔ',
'ටෝ':'ට්ඕ',
'ටෞ':'ට්ඖ',
'ටං':'ට්අං',
'ටඃ':'ට්අඃ',
'ර්‍ට':'ර්ට්',
'ට්‍ර':'ට්ර',
'ට්‍ය':'ට්ය',
'ඨ්':'ඨ්',
'ඨ':'ඨ්අ',
'ඨා':'ඨ්ආ',
'ඨැ':'ඨ්ඇ',
'ඨෑ':'ඨ්ඈ',
'ඨි':'ඨ්ඉ',
'ඨී':'ඨ්ඊ',
'ඨු':'ඨ්උ',
'ඨූ':'ඨ්ඌ',
'ඨෘ':'ඨ්ර්උ',
'ඨෲ':'ඨ්ර්ඌ',
'ඨෟ':'ඨ්ඖ',
'ඨෳ':'ඨ්ඖ',
'ඨෙ':'ඨ්එ',
'ඨේ':'ඨ්ඒ',
'ඨෛ':'ඨ්ඓ',
'ඨො':'ඨ්ඔ',
'ඨෝ':'ඨ්ඕ',
'ඨෞ':'ඨ්ඖ',
'ඨං':'ඨ්අං',
'ඨඃ':'ඨ්අඃ',
'ර්‍ඨ':'ර්ඨ්',
'ඨ්‍ර':'ඨ්ර',
'ඨ්‍ය':'ඨ්ය',
'ඩ්':'ඩ්',
'ඩ':'ඩ්අ',
'ඩා':'ඩ්ආ',
'ඩැ':'ඩ්ඇ',
'ඩෑ':'ඩ්ඈ',
'ඩි':'ඩ්ඉ',
'ඩී':'ඩ්ඊ',
'ඩු':'ඩ්උ',
'ඩූ':'ඩ්ඌ',
'ඩෘ':'ඩ්ර්උ',
'ඩෲ':'ඩ්ර්ඌ',
'ඩෟ':'ඩ්ඖ',
'ඩෳ':'ඩ්ඖ',
'ඩෙ':'ඩ්එ',
'ඩේ':'ඩ්ඒ',
'ඩෛ':'ඩ්ඓ',
'ඩො':'ඩ්ඔ',
'ඩෝ':'ඩ්ඕ',
'ඩෞ':'ඩ්ඖ',
'ඩං':'ඩ්අං',
'ඩඃ':'ඩ්අඃ',
'ර්‍ඩ':'ර්ඩ්',
'ඩ්‍ර':'ඩ්ර',
'ඩ්‍ය':'ඩ්ය',
'ඪ්':'ඪ්',
'ඪ':'ඪ්අ',
'ඪා':'ඪ්ආ',
'ඪැ':'ඪ්ඇ',
'ඪෑ':'ඪ්ඈ',
'ඪි':'ඪ්ඉ',
'ඪී':'ඪ්ඊ',
'ඪු':'ඪ්උ',
'ඪූ':'ඪ්ඌ',
'ඪෘ':'ඪ්ර්උ',
'ඪෲ':'ඪ්ර්ඌ',
'ඪෟ':'ඪ්ඖ',
'ඪෳ':'ඪ්ඖ',
'ඪෙ':'ඪ්එ',
'ඪේ':'ඪ්ඒ',
'ඪෛ':'ඪ්ඓ',
'ඪො':'ඪ්ඔ',
'ඪෝ':'ඪ්ඕ',
'ඪෞ':'ඪ්ඖ',
'ඪං':'ඪ්අං',
'ඪඃ':'ඪ්අඃ',
'ර්‍ඪ':'ර්ඪ්',
'ඪ්‍ර':'ඪ්ර',
'ඪ්‍ය':'ඪ්ය',
'ණ්':'ණ්',
'ණ':'ණ්අ',
'ණා':'ණ්ආ',
'ණැ':'ණ්ඇ',
'ණෑ':'ණ්ඈ',
'ණි':'ණ්ඉ',
'ණී':'ණ්ඊ',
'ණු':'ණ්උ',
'ණූ':'ණ්ඌ',
'ණෘ':'ණ්ර්උ',
'ණෲ':'ණ්ර්ඌ',
'ණෟ':'ණ්ඖ',
'ණෳ':'ණ්ඖ',
'ණෙ':'ණ්එ',
'ණේ':'ණ්ඒ',
'ණෛ':'ණ්ඓ',
'ණො':'ණ්ඔ',
'ණෝ':'ණ්ඕ',
'ණෞ':'ණ්ඖ',
'ණං':'ණ්අං',
'ණඃ':'ණ්අඃ',
'ර්‍ණ':'ර්ණ්',
'ණ්‍ර':'ණ්ර',
'ණ්‍ය':'ණ්ය',
'ඬ්':'ඬ්',
'ඬ':'ඬ්අ',
'ඬා':'ඬ්ආ',
'ඬැ':'ඬ්ඇ',
'ඬෑ':'ඬ්ඈ',
'ඬි':'ඬ්ඉ',
'ඬී':'ඬ්ඊ',
'ඬු':'ඬ්උ',
'ඬූ':'ඬ්ඌ',
'ඬෘ':'ඬ්ර්උ',
'ඬෲ':'ඬ්ර්ඌ',
'ඬෟ':'ඬ්ඖ',
'ඬෳ':'ඬ්ඖ',
'ඬෙ':'ඬ්එ',
'ඬේ':'ඬ්ඒ',
'ඬෛ':'ඬ්ඓ',
'ඬො':'ඬ්ඔ',
'ඬෝ':'ඬ්ඕ',
'ඬෞ':'ඬ්ඖ',
'ඬං':'ඬ්අං',
'ඬඃ':'ඬ්අඃ',
'ර්‍ඬ':'ර්ඬ්',
'ඬ්‍ර':'ඬ්ර',
'ඬ්‍ය':'ඬ්ය',
'ත්':'ත්',
'ත':'ත්අ',
'තා':'ත්ආ',
'තැ':'ත්ඇ',
'තෑ':'ත්ඈ',
'ති':'ත්ඉ',
'තී':'ත්ඊ',
'තු':'ත්උ',
'තූ':'ත්ඌ',
'තෘ':'ත්ර්උ',
'තෲ':'ත්ර්ඌ',
'තෟ':'ත්ඖ',
'තෳ':'ත්ඖ',
'තෙ':'ත්එ',
'තේ':'ත්ඒ',
'තෛ':'ත්ඓ',
'තො':'ත්ඔ',
'තෝ':'ත්ඕ',
'තෞ':'ත්ඖ',
'තං':'ත්අං',
'තඃ':'ත්අඃ',
'ර්‍ත':'ර්ත්',
'ත්‍ර':'ත්ර',
'ත්‍ය':'ත්ය',
'ථ්':'ථ්',
'ථ':'ථ්අ',
'ථා':'ථ්ආ',
'ථැ':'ථ්ඇ',
'ථෑ':'ථ්ඈ',
'ථි':'ථ්ඉ',
'ථී':'ථ්ඊ',
'ථු':'ථ්උ',
'ථූ':'ථ්ඌ',
'ථෘ':'ථ්ර්උ',
'ථෲ':'ථ්ර්ඌ',
'ථෟ':'ථ්ඖ',
'ථෳ':'ථ්ඖ',
'ථෙ':'ථ්එ',
'ථේ':'ථ්ඒ',
'ථෛ':'ථ්ඓ',
'ථො':'ථ්ඔ',
'ථෝ':'ථ්ඕ',
'ථෞ':'ථ්ඖ',
'ථං':'ථ්අං',
'ථඃ':'ථ්අඃ',
'ර්‍ථ':'ර්ථ්',
'ථ්‍ර':'ථ්ර',
'ථ්‍ය':'ථ්ය',
'ද්':'ද්',
'ද':'ද්අ',
'දා':'ද්ආ',
'දැ':'ද්ඇ',
'දෑ':'ද්ඈ',
'දි':'ද්ඉ',
'දී':'ද්ඊ',
'දු':'ද්උ',
'දූ':'ද්ඌ',
'දෘ':'ද්ර්උ',
'දෲ':'ද්ර්ඌ',
'දෟ':'ද්ඖ',
'දෳ':'ද්ඖ',
'දෙ':'ද්එ',
'දේ':'ද්ඒ',
'දෛ':'ද්ඓ',
'දො':'ද්ඔ',
'දෝ':'ද්ඕ',
'දෞ':'ද්ඖ',
'දං':'ද්අං',
'දඃ':'ද්අඃ',
'ර්‍ද':'ර්ද්',
'ද්‍ර':'ද්ර',
'ද්‍ය':'ද්ය',
'ධ්':'ධ්',
'ධ':'ධ්අ',
'ධා':'ධ්ආ',
'ධැ':'ධ්ඇ',
'ධෑ':'ධ්ඈ',
'ධි':'ධ්ඉ',
'ධී':'ධ්ඊ',
'ධු':'ධ්උ',
'ධූ':'ධ්ඌ',
'ධෘ':'ධ්ර්උ',
'ධෲ':'ධ්ර්ඌ',
'ධෟ':'ධ්ඖ',
'ධෳ':'ධ්ඖ',
'ධෙ':'ධ්එ',
'ධේ':'ධ්ඒ',
'ධෛ':'ධ්ඓ',
'ධො':'ධ්ඔ',
'ධෝ':'ධ්ඕ',
'ධෞ':'ධ්ඖ',
'ධං':'ධ්අං',
'ධඃ':'ධ්අඃ',
'ර්‍ධ':'ර්ධ්',
'ධ්‍ර':'ධ්ර',
'ධ්‍ය':'ධ්ය',
'න්':'න්',
'න':'න්අ',
'නා':'න්ආ',
'නැ':'න්ඇ',
'නෑ':'න්ඈ',
'නි':'න්ඉ',
'නී':'න්ඊ',
'නු':'න්උ',
'නූ':'න්ඌ',
'නෘ':'න්ර්උ',
'නෲ':'න්ර්ඌ',
'නෟ':'න්ඖ',
'නෳ':'න්ඖ',
'නෙ':'න්එ',
'නේ':'න්ඒ',
'නෛ':'න්ඓ',
'නො':'න්ඔ',
'නෝ':'න්ඕ',
'නෞ':'න්ඖ',
'නං':'න්අං',
'නඃ':'න්අඃ',
'ර්‍න':'ර්න්',
'න්‍ර':'න්ර',
'න්‍ය':'න්ය',
'ඳ්':'ඳ්',
'ඳ':'ඳ්අ',
'ඳා':'ඳ්ආ',
'ඳැ':'ඳ්ඇ',
'ඳෑ':'ඳ්ඈ',
'ඳි':'ඳ්ඉ',
'ඳී':'ඳ්ඊ',
'ඳු':'ඳ්උ',
'ඳූ':'ඳ්ඌ',
'ඳෘ':'ඳ්ර්උ',
'ඳෲ':'ඳ්ර්ඌ',
'ඳෟ':'ඳ්ඖ',
'ඳෳ':'ඳ්ඖ',
'ඳෙ':'ඳ්එ',
'ඳේ':'ඳ්ඒ',
'ඳෛ':'ඳ්ඓ',
'ඳො':'ඳ්ඔ',
'ඳෝ':'ඳ්ඕ',
'ඳෞ':'ඳ්ඖ',
'ඳං':'ඳ්අං',
'ඳඃ':'ඳ්අඃ',
'ර්‍ඳ':'ර්ඳ්',
'ඳ්‍ර':'ඳ්ර',
'ඳ්‍ය':'ඳ්ය',
'ප්':'ප්',
'ප':'ප්අ',
'පා':'ප්ආ',
'පැ':'ප්ඇ',
'පෑ':'ප්ඈ',
'පි':'ප්ඉ',
'පී':'ප්ඊ',
'පු':'ප්උ',
'පූ':'ප්ඌ',
'පෘ':'ප්ර්උ',
'පෲ':'ප්ර්ඌ',
'පෟ':'ප්ඖ',
'පෳ':'ප්ඖ',
'පෙ':'ප්එ',
'පේ':'ප්ඒ',
'පෛ':'ප්ඓ',
'පො':'ප්ඔ',
'පෝ':'ප්ඕ',
'පෞ':'ප්ඖ',
'පං':'ප්අං',
'පඃ':'ප්අඃ',
'ර්‍ප':'ර්ප්',
'ප්‍ර':'ප්ර',
'ප්‍ය':'ප්ය',
'ඵ්':'ඵ්',
'ඵ':'ඵ්අ',
'ඵා':'ඵ්ආ',
'ඵැ':'ඵ්ඇ',
'ඵෑ':'ඵ්ඈ',
'ඵි':'ඵ්ඉ',
'ඵී':'ඵ්ඊ',
'ඵු':'ඵ්උ',
'ඵූ':'ඵ්ඌ',
'ඵෘ':'ඵ්ර්උ',
'ඵෲ':'ඵ්ර්ඌ',
'ඵෟ':'ඵ්ඖ',
'ඵෳ':'ඵ්ඖ',
'ඵෙ':'ඵ්එ',
'ඵේ':'ඵ්ඒ',
'ඵෛ':'ඵ්ඓ',
'ඵො':'ඵ්ඔ',
'ඵෝ':'ඵ්ඕ',
'ඵෞ':'ඵ්ඖ',
'ඵං':'ඵ්අං',
'ඵඃ':'ඵ්අඃ',
'ර්‍ඵ':'ර්ඵ්',
'ඵ්‍ර':'ඵ්ර',
'ඵ්‍ය':'ඵ්ය',
'බ්':'බ්',
'බ':'බ්අ',
'බා':'බ්ආ',
'බැ':'බ්ඇ',
'බෑ':'බ්ඈ',
'බි':'බ්ඉ',
'බී':'බ්ඊ',
'බු':'බ්උ',
'බූ':'බ්ඌ',
'බෘ':'බ්ර්උ',
'බෲ':'බ්ර්ඌ',
'බෟ':'බ්ඖ',
'බෳ':'බ්ඖ',
'බෙ':'බ්එ',
'බේ':'බ්ඒ',
'බෛ':'බ්ඓ',
'බො':'බ්ඔ',
'බෝ':'බ්ඕ',
'බෞ':'බ්ඖ',
'බං':'බ්අං',
'බඃ':'බ්අඃ',
'ර්‍බ':'ර්බ්',
'බ්‍ර':'බ්ර',
'බ්‍ය':'බ්ය',
'භ්':'භ්',
'භ':'භ්අ',
'භා':'භ්ආ',
'භැ':'භ්ඇ',
'භෑ':'භ්ඈ',
'භි':'භ්ඉ',
'භී':'භ්ඊ',
'භු':'භ්උ',
'භූ':'භ්ඌ',
'භෘ':'භ්ර්උ',
'භෲ':'භ්ර්ඌ',
'භෟ':'භ්ඖ',
'භෳ':'භ්ඖ',
'භෙ':'භ්එ',
'භේ':'භ්ඒ',
'භෛ':'භ්ඓ',
'භො':'භ්ඔ',
'භෝ':'භ්ඕ',
'භෞ':'භ්ඖ',
'භං':'භ්අං',
'භඃ':'භ්අඃ',
'ර්‍භ':'ර්භ්',
'භ්‍ර':'භ්ර',
'භ්‍ය':'භ්ය',
'ම්':'ම්',
'ම':'ම්අ',
'මා':'ම්ආ',
'මැ':'ම්ඇ',
'මෑ':'ම්ඈ',
'මි':'ම්ඉ',
'මී':'ම්ඊ',
'මු':'ම්උ',
'මූ':'ම්ඌ',
'මෘ':'ම්ර්උ',
'මෲ':'ම්ර්ඌ',
'මෟ':'ම්ඖ',
'මෳ':'ම්ඖ',
'මෙ':'ම්එ',
'මේ':'ම්ඒ',
'මෛ':'ම්ඓ',
'මො':'ම්ඔ',
'මෝ':'ම්ඕ',
'මෞ':'ම්ඖ',
'මං':'ම්අං',
'මඃ':'ම්අඃ',
'ර්‍ම':'ර්ම්',
'ම්‍ර':'ම්ර',
'ම්‍ය':'ම්ය',
'ඹ්':'ඹ්',
'ඹ':'ඹ්අ',
'ඹා':'ඹ්ආ',
'ඹැ':'ඹ්ඇ',
'ඹෑ':'ඹ්ඈ',
'ඹි':'ඹ්ඉ',
'ඹී':'ඹ්ඊ',
'ඹු':'ඹ්උ',
'ඹූ':'ඹ්ඌ',
'ඹෘ':'ඹ්ර්උ',
'ඹෲ':'ඹ්ර්ඌ',
'ඹෟ':'ඹ්ඖ',
'ඹෳ':'ඹ්ඖ',
'ඹෙ':'ඹ්එ',
'ඹේ':'ඹ්ඒ',
'ඹෛ':'ඹ්ඓ',
'ඹො':'ඹ්ඔ',
'ඹෝ':'ඹ්ඕ',
'ඹෞ':'ඹ්ඖ',
'ඹං':'ඹ්අං',
'ඹඃ':'ඹ්අඃ',
'ර්‍ඹ':'ර්ඹ්',
'ඹ්‍ර':'ඹ්ර',
'ඹ්‍ය':'ඹ්ය',
'ය්':'ය්',
'යා':'ය්ආ',
'යැ':'ය්ඇ',
'යෑ':'ය්ඈ',
'යි':'ය්ඉ',
'යී':'ය්ඊ',
'යු':'ය්උ',
'යූ':'ය්ඌ',
'යෘ':'ය්ර්උ',
'යෲ':'ය්ර්ඌ',
'යෟ':'ය්ඖ',
'යෳ':'ය්ඖ',
'යෙ':'ය්එ',
'යේ':'ය්ඒ',
'යෛ':'ය්ඓ',
'යො':'ය්ඔ',
'යෝ':'ය්ඕ',
'යෞ':'ය්ඖ',
'යං':'ය්අං',
'යඃ':'ය්අඃ',
'ර්‍ය':'ර්ය',
'ය්‍ර':'ය්ර',
'ය්‍ය':'ය්ය',
'රා':'ර්ආ',
'රැ':'ර්ඇ',
'රෑ':'ර්ඈ',
'රි':'ර්ඉ',
'රී':'ර්ඊ',
'රු':'ර්උ',
'රූ':'ර්ඌ',
'රෘ':'ර්ර්උ',
'රෲ':'ර්ර්ඌ',
'රෟ':'ර්ඖ',
'රෳ':'ර්ඖ',
'රෙ':'ර්එ',
'රේ':'ර්ඒ',
'රෛ':'ර්ඓ',
'රො':'ර්ඔ',
'රෝ':'ර්ඕ',
'රෞ':'ර්ඖ',
'රං':'ර්අං',
'රඃ':'ර්අඃ',
'ර්‍ර':'ර්ර',
'ල්':'ල්',
'ල':'ල්අ',
'ලා':'ල්ආ',
'ලැ':'ල්ඇ',
'ලෑ':'ල්ඈ',
'ලි':'ල්ඉ',
'ලී':'ල්ඊ',
'ලු':'ල්උ',
'ලූ':'ල්ඌ',
'ලෘ':'ල්ර්උ',
'ලෲ':'ල්ර්ඌ',
'ලෟ':'ල්ඖ',
'ලෳ':'ල්ඖ',
'ලෙ':'ල්එ',
'ලේ':'ල්ඒ',
'ලෛ':'ල්ඓ',
'ලො':'ල්ඔ',
'ලෝ':'ල්ඕ',
'ලෞ':'ල්ඖ',
'ලං':'ල්අං',
'ලඃ':'ල්අඃ',
'ර්‍ල':'ර්ල්',
'ල්‍ර':'ල්ර',
'ල්‍ය':'ල්ය',
'ව්':'ව්',
'ව':'ව්අ',
'වා':'ව්ආ',
'වැ':'ව්ඇ',
'වෑ':'ව්ඈ',
'වි':'ව්ඉ',
'වී':'ව්ඊ',
'වු':'ව්උ',
'වූ':'ව්ඌ',
'වෘ':'ව්ර්උ',
'වෲ':'ව්ර්ඌ',
'වෟ':'ව්ඖ',
'වෳ':'ව්ඖ',
'වෙ':'ව්එ',
'වේ':'ව්ඒ',
'වෛ':'ව්ඓ',
'වො':'ව්ඔ',
'වෝ':'ව්ඕ',
'වෞ':'ව්ඖ',
'වං':'ව්අං',
'වඃ':'ව්අඃ',
'ර්‍ව':'ර්ව්',
'ව්‍ර':'ව්ර',
'ව්‍ය':'ව්ය',
'ශ්':'ශ්',
'ශ':'ශ්අ',
'ශා':'ශ්ආ',
'ශැ':'ශ්ඇ',
'ශෑ':'ශ්ඈ',
'ශි':'ශ්ඉ',
'ශී':'ශ්ඊ',
'ශු':'ශ්උ',
'ශූ':'ශ්ඌ',
'ශෘ':'ශ්ර්උ',
'ශෲ':'ශ්ර්ඌ',
'ශෟ':'ශ්ඖ',
'ශෳ':'ශ්ඖ',
'ශෙ':'ශ්එ',
'ශේ':'ශ්ඒ',
'ශෛ':'ශ්ඓ',
'ශො':'ශ්ඔ',
'ශෝ':'ශ්ඕ',
'ශෞ':'ශ්ඖ',
'ශං':'ශ්අං',
'ශඃ':'ශ්අඃ',
'ර්‍ශ':'ර්ශ්',
'ශ්‍ර':'ශ්ර',
'ශ්‍ය':'ශ්ය',
'ෂ්':'ෂ්',
'ෂ':'ෂ්අ',
'ෂා':'ෂ්ආ',
'ෂැ':'ෂ්ඇ',
'ෂෑ':'ෂ්ඈ',
'ෂි':'ෂ්ඉ',
'ෂී':'ෂ්ඊ',
'ෂු':'ෂ්උ',
'ෂූ':'ෂ්ඌ',
'ෂෘ':'ෂ්ර්උ',
'ෂෲ':'ෂ්ර්ඌ',
'ෂෟ':'ෂ්ඖ',
'ෂෳ':'ෂ්ඖ',
'ෂෙ':'ෂ්එ',
'ෂේ':'ෂ්ඒ',
'ෂෛ':'ෂ්ඓ',
'ෂො':'ෂ්ඔ',
'ෂෝ':'ෂ්ඕ',
'ෂෞ':'ෂ්ඖ',
'ෂං':'ෂ්අං',
'ෂඃ':'ෂ්අඃ',
'ර්‍ෂ':'ර්ෂ්',
'ෂ්‍ර':'ෂ්ර',
'ෂ්‍ය':'ෂ්ය',
'ස්':'ස්',
'ස':'ස්අ',
'සා':'ස්ආ',
'සැ':'ස්ඇ',
'සෑ':'ස්ඈ',
'සි':'ස්ඉ',
'සී':'ස්ඊ',
'සු':'ස්උ',
'සූ':'ස්ඌ',
'සෘ':'ස්ර්උ',
'සෲ':'ස්ර්ඌ',
'සෟ':'ස්ඖ',
'සෳ':'ස්ඖ',
'සෙ':'ස්එ',
'සේ':'ස්ඒ',
'සෛ':'ස්ඓ',
'සො':'ස්ඔ',
'සෝ':'ස්ඕ',
'සෞ':'ස්ඖ',
'සං':'ස්අං',
'සඃ':'ස්අඃ',
'ර්‍ස':'ර්ස්',
'ස්‍ර':'ස්ර',
'ස්‍ය':'ස්ය',
'හ්':'හ්',
'හ':'හ්අ',
'හා':'හ්ආ',
'හැ':'හ්ඇ',
'හෑ':'හ්ඈ',
'හි':'හ්ඉ',
'හී':'හ්ඊ',
'හු':'හ්උ',
'හූ':'හ්ඌ',
'හෘ':'හ්ර්උ',
'හෲ':'හ්ර්ඌ',
'හෟ':'හ්ඖ',
'හෳ':'හ්ඖ',
'හෙ':'හ්එ',
'හේ':'හ්ඒ',
'හෛ':'හ්ඓ',
'හො':'හ්ඔ',
'හෝ':'හ්ඕ',
'හෞ':'හ්ඖ',
'හං':'හ්අං',
'හඃ':'හ්අඃ',
'ර්‍හ':'ර්හ්',
'හ්‍ර':'හ්ර',
'හ්‍ය':'හ්ය',
'ළ්':'ළ්',
'ළ':'ළ්අ',
'ළා':'ළ්ආ',
'ළැ':'ළ්ඇ',
'ළෑ':'ළ්ඈ',
'ළි':'ළ්ඉ',
'ළී':'ළ්ඊ',
'ළු':'ළ්උ',
'ළූ':'ළ්ඌ',
'ළෘ':'ළ්ර්උ',
'ළෲ':'ළ්ර්ඌ',
'ළෟ':'ළ්ඖ',
'ළෳ':'ළ්ඖ',
'ළෙ':'ළ්එ',
'ළේ':'ළ්ඒ',
'ළෛ':'ළ්ඓ',
'ළො':'ළ්ඔ',
'ළෝ':'ළ්ඕ',
'ළෞ':'ළ්ඖ',
'ළං':'ළ්අං',
'ළඃ':'ළ්අඃ',
'ර්‍ළ':'ර්ළ්',
'ළ්‍ර':'ළ්ර',
'ළ්‍ය':'ළ්ය',
'ෆ්':'ෆ්',
'ෆ':'ෆ්අ',
'ෆා':'ෆ්ආ',
'ෆැ':'ෆ්ඇ',
'ෆෑ':'ෆ්ඈ',
'ෆි':'ෆ්ඉ',
'ෆී':'ෆ්ඊ',
'ෆු':'ෆ්උ',
'ෆූ':'ෆ්ඌ',
'ෆෘ':'ෆ්ර්උ',
'ෆෲ':'ෆ්ර්ඌ',
'ෆෟ':'ෆ්ඖ',
'ෆෳ':'ෆ්ඖ',
'ෆෙ':'ෆ්එ',
'ෆේ':'ෆ්ඒ',
'ෆෛ':'ෆ්ඓ',
'ෆො':'ෆ්ඔ',
'ෆෝ':'ෆ්ඕ',
'ෆෞ':'ෆ්ඖ',
'ෆං':'ෆ්අං',
'ෆඃ':'ෆ්අඃ',
'ර්‍ෆ':'ර්ෆ්',
'ෆ්‍ර':'ෆ්ර',
'ෆ්‍ය':'ෆ්ය',
}

suffixes_raw = """අණු
අණි 
ආණ
ඉණ 
ඉණි 
උණු 
උණ 
අකු 
අක් 
අක 
අත් 
ආක් 
ආය 
ආහ 
උන් 
එකු 
එක් 
එන් 
එමි 
එමු 
ඒ 
ඒය 
ඔත් 
ඕය 
න
අ
අක්
ආ 
ක්
එක් 
ඕ 
අන්
ය 
ආ 
තත් 
ති 
තොත් 
ද්දි 
නවා 
නු 
න්නේ 
මි 
මින් 
මු 
යි 
අත් 
ඊය 
ඌ 
ඒ 
ඔත් 
ඉලි
ඊම් 
උම් 
එන් 
නවා 
එහි 
ඉ 
ති 
මි 
මු 
වල් 
වල 
ට 
ව 
ගේ 
ගෙන් 
ඉන් 
තොත් 
මින් 
ද්දී 
තත් 
න්ට 
එමි 
එමු 
ඒය 
ඊය 
ආය 
බර 
අනුකූල 
ජනක 
ගරුක 
දායක 
දායී
ආගේ
එකුගේ
අකගේ
අන්ගේ
ආට
අකට
අන්ට
අට
වලින්
එමි
එමු
ඔත්
තොත්
වතුන්
වතෙක්
වතා
බද
මය
සහගත
සම්පන්න
දායක
කළු
කර
ආත්ම්ක
ආත්මක
නීය
මුවා
තම
ඉති
අටු
බ
තා
අටි
මය
තර
ඊම
ඊමක්
ඊමෙන්
ඊමේ
වලට"""

# encoder
key_list = list(vowels_mapper.keys())
# changes the order to increase the accuracy (lengthy latters should map first)
key_list_rev = list(reversed(key_list))

def si_vowels_encoder(vowels_mapper,key_list_rev,word):
    for letter in key_list_rev:
        vowel = vowels_mapper[letter]
        word = word.replace(letter, vowel)
        word = word.replace('අ්','')
    return word
# decoder
vowels_mapper_inversed = {}
for key,value in vowels_mapper.items():
    vowels_mapper_inversed[value] = key

key_list_inversed = list(vowels_mapper_inversed.keys())
# changes the order to increase the accuracy (lengthy latters should map first)
key_list_rev_inversed = list(reversed(key_list_inversed))

def si_vowels_decoder(vowels_mapper_inversed,key_list_rev_inversed,base_word_encoded):
    for letter in key_list_rev_inversed:
        vowel = vowels_mapper_inversed[letter]
        if letter in base_word_encoded:
            base_word_encoded = base_word_encoded.replace(letter, vowel)
            # base_word_encoded = base_word_encoded.replace('අ්','')
    return base_word_encoded

# suffixes
suffixes_unique = suffixes_raw.split('\n')
suffixes_unique = list(set([letter_processed.strip() for letter_processed in suffixes_unique]))

suffixes_processed = [si_vowels_encoder(vowels_mapper,key_list_rev,word) for word in suffixes_unique]

def si_stemmer_sentence_custom(word):
    res = []
    result = ""
    # Initialising string
    ini_string = si_vowels_encoder(vowels_mapper,key_list_rev,word)
    for suffix in suffixes_processed:
        if ini_string.endswith(suffix):
            res.append(ini_string[:-(len(suffix))])
        
        # printing result
    if len(res) > 0:
        result = min(res, key=len)
    else:
        result = word
    # decode base word
    result = si_vowels_decoder(vowels_mapper_inversed,key_list_rev_inversed,result)
    return result

# def si_stemmer_sentence(text):
#     tokenization = si_tokenizer.tokenize(text)
#     si_stemmed=""
#     for w in tokenization:
#         #only base word
#         si_stemmed += " "+si_stemmer.stem(w)[0]
#     return si_stemmed


def en_stemmer_sentence(text):
    tokenization = nltk.word_tokenize(text)
    en_stemmed=""
    for w in tokenization:
        en_stemmed += " "+en_stemmer.stem(w)
    return en_stemmed

def base_form_convetor(selection):
    text = selection.translate(str.maketrans('', '', string.punctuation))
    en_stemmed = en_stemmer_sentence(text)
    si_stemmed = si_stemmer_sentence_custom(en_stemmed)
    return si_stemmed.strip()


def SIENA_reverse_stemming():
    return True

# Similarity Algorithms
alphabet = "A a B b C c D d E e F f G g H h I i J j K k L l M m N n O o P p Q q R r S s T t U u V v W w X x Y y Z z"
en_alphabet = alphabet.split()
si_alphabet = key_list
vecSpace = tuple(si_alphabet+en_alphabet)


def cosing_sim(word1,word2):
    words = [word1,word2]
    #counting chars
    result = []
    for word in words:
        wordVec = []
        for letter in vecSpace:
            wordVec.append(word.count(letter))
        squares=list(map(lambda x:pow(x,2),wordVec))
        sum_of_sq = sum(squares)
        norm = math.sqrt(sum_of_sq)
        norm_vec = [i/norm for i in wordVec]
        result.append(norm_vec)

    result = np.array(result)
    df = pd.DataFrame()
    i = 0
    for singleVec_R in result:
        col = []
        for singleVec_C in result:
            col.append(np.sum(singleVec_R*singleVec_C))
        df[i] =col
        i += 1
    return (df[0][1])

def generate_ngrams(s, n):    
    tokens = list(s)
    ngrams = zip(*[tokens[i:] for i in range(n)])
    return ["".join(ngram) for ngram in ngrams]

def generate_ngrams_sent(sentence, n):
    sentence_splitted = sentence.split(" ")
    tokens = list(sentence_splitted)
    ngrams = zip(*[tokens[i:] for i in range(n)])
    return [" ".join(ngram) for ngram in ngrams]

def n_gram_similarity(word1,word2):
    word_1 = generate_ngrams(word1, 2)
    word_2 = generate_ngrams(word2, 2)
    long_word = ""
    short_word = ""
    count = 0
    ans = 0
    if len(word_1) > len(word_2):
        long_word = word_1
        short_word = word_2
    else:
        long_word = word_2
        short_word = word_1
    try:
        for element in short_word:
            if element in long_word:
                count+=1
        ans = count/(len(long_word))
    except Exception as e:
        pass

    return ans

def similarity(word1,word2):
    # TODO : defime weights
    result = (n_gram_similarity(word1,word2) + cosing_sim(word1,word2))/2
    return result