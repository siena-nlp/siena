import logging
import math
import os
import string
import nltk
import numpy as np
import pandas as pd
from nltk.stem.porter import *
from ruamel.yaml import YAML

from siena.shared.constants import (
    SUFFIXES_RAW,
    VOWELS_MAPPER,
    COLUMN_NAME_BASE_WORD,
    COLUMN_NAME_COUNT,
    COLUMN_NAME_ENTITY,
    SIENA_KNOWLEDGE_BASE_PATH,
    FilePermission,
    Encoding,
    SIENA_TEMP_KNOWLEDGE_BASE_PATH,
    NEW_LINE_TAG,
    NLTK_WORDNET,
    NLTK_PUNKT,
    EN_ALPHABET,
)
logger = logging.getLogger(__name__)
en_stemmer = PorterStemmer()
nltk.download(NLTK_WORDNET, quiet=True)
nltk.download(NLTK_PUNKT, quiet=True)
yml = YAML()
yml.indent(mapping=2, sequence=4, offset=2)
yml.preserve_quotes = True
yml.explicit_start = False

vowels_mapper = VOWELS_MAPPER
suffixes_raw = SUFFIXES_RAW
# encoder
key_list = list(vowels_mapper.keys())
# changes the order to increase the accuracy (lengthy letters should map first)
key_list_rev = list(reversed(key_list))


def si_vowels_encoder(vowels_mapper_, key_list_rev_, word):
    for letter in key_list_rev_:
        vowel = vowels_mapper_[letter]
        word = word.replace(letter, vowel)
        word = word.replace('අ්', '')
    return word


# decoder
vowels_mapper_inversed = {}
for key, value in vowels_mapper.items():
    vowels_mapper_inversed[value] = key

key_list_inversed = list(vowels_mapper_inversed.keys())
# changes the order to increase the accuracy (lengthy letters should map first)
key_list_rev_inversed = list(reversed(key_list_inversed))


def si_vowels_decoder(vowels_mapper_inversed_, key_list_rev_inversed_, base_word_encoded):
    for letter in key_list_rev_inversed_:
        vowel = vowels_mapper_inversed_[letter]
        if letter in base_word_encoded:
            base_word_encoded = base_word_encoded.replace(letter, vowel)
            # base_word_encoded = base_word_encoded.replace('අ්','')
    return base_word_encoded


# suffixes
suffixes_unique = suffixes_raw.split(NEW_LINE_TAG)
suffixes_unique = list(set([letter_processed.strip() for letter_processed in suffixes_unique]))

suffixes_processed = [si_vowels_encoder(vowels_mapper, key_list_rev, word) for word in suffixes_unique]


def si_stemmer_sentence_custom(word: str) -> str:
    res = []
    # Initialising string
    ini_string = si_vowels_encoder(vowels_mapper, key_list_rev, word)
    for suffix in suffixes_processed:
        if ini_string.endswith(suffix):
            res.append(ini_string[:-(len(suffix))])

        # printing result
    if len(res) > 0:
        result = min(res, key=len)
    else:
        result = word
    # decode base word
    result = si_vowels_decoder(vowels_mapper_inversed, key_list_rev_inversed, result)
    return result


def en_stemmer_sentence(text: str) -> str:
    tokenization = nltk.word_tokenize(text)
    en_stemmed = ""
    for w in tokenization:
        en_stemmed += " " + en_stemmer.stem(w)
    return en_stemmed


def base_form_convetor(selection: str) -> str:
    text = selection.translate(str.maketrans('', '', string.punctuation))
    en_stemmed = en_stemmer_sentence(text)
    si_stemmed = si_stemmer_sentence_custom(en_stemmed)
    return si_stemmed.strip()


# Similarity Algorithms 
alphabet = EN_ALPHABET
en_alphabet = alphabet.split()
si_alphabet = key_list
vecSpace = tuple(si_alphabet + en_alphabet)


def cosing_sim(word1: str, word2: str) -> float:
    words = [word1, word2]
    # counting chars
    result = []
    for word in words:
        word_vec = []
        for letter in vecSpace:
            word_vec.append(word.count(letter))
        squares = list(map(lambda x: pow(x, 2), word_vec))
        sum_of_sq = sum(squares)
        norm = math.sqrt(sum_of_sq)
        norm_vec = [i / norm for i in word_vec]
        result.append(norm_vec)

    result = np.array(result)
    df = pd.DataFrame()
    i = 0
    for singleVec_R in result:
        col = []
        for singleVec_C in result:
            col.append(np.sum(singleVec_R * singleVec_C))
        df[i] = col
        i += 1
    return float(df[0][1])


def generate_ngrams(s, n):
    tokens = list(s)
    ngrams = zip(*[tokens[i:] for i in range(n)])
    return ["".join(ngram) for ngram in ngrams]


def generate_ngrams_sent(sentence, n):
    sentence_split = sentence.split(" ")
    tokens = list(sentence_split)
    ngrams = zip(*[tokens[i:] for i in range(n)])
    return [" ".join(ngram) for ngram in ngrams]


def n_gram_similarity(word1, word2):
    word_1 = generate_ngrams(word1, 2)
    word_2 = generate_ngrams(word2, 2)
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
                count += 1
        ans = count / (len(long_word))
    except Exception as e:
        logger.exception(f"Exception occurred. {e}")

    return ans


def similarity(word1, word2):
    result = (n_gram_similarity(word1, word2) + cosing_sim(word1, word2)) / 2
    return result

