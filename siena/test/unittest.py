from siena.test.functions import (
    test_yaml_file_ext,
    test_csv_file_ext,
    test_stem_word,
)


if __name__ == "__main__":  
    test_yaml_file_ext()
    test_csv_file_ext()
    test_stem_word()
    print("Everything passed")  