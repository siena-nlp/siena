from siena.core.actions import (
allowed_file_nlu,
allowed_file_knowledge,
)
from siena.core.similarity import(
    si_stemmer_sentence_custom
)

def test_yaml_file_ext():  
    assert allowed_file_nlu("test.yaml") == True, "It should be True"
    assert allowed_file_nlu("test.exe") == False, "It should be False"

def test_csv_file_ext():  
    assert allowed_file_knowledge("sample.csv") == True, "It should be True"
    assert allowed_file_knowledge("sample.ccv") == False, "It should be False"

def test_stem_word():
    assert si_stemmer_sentence_custom("අශ්වයන්ට") == "අශ්වය්", "It should be අශ්වය්"