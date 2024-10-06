import os
import ast
from box import Box
from copy import deepcopy
from time import time
import requests


def find_all_py_files(directory):
    '''
    Returns a list of paths of all py files in a directory and all its subdirectories
    '''
    py_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    
    return py_files

def extract_functions_docstrings(pyfile_path):
    '''
    Provided the path to a py file, returns a dictionary where the keys are the names of the defined functions in that py file, and the values are their corresponding docstring
    '''

    functions_info = {}

    with open(pyfile_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
        tree = ast.parse(file_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                docstring = ast.get_docstring(node)
                functions_info[func_name] = {'docstring': docstring, 'path': pyfile_path}
    
    return Box(functions_info)

def is_function_used(function_name, file_path):
    '''
    Check if a function is used within a given py file.
    '''
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            return function_name in content
    except FileNotFoundError:
        print(f"The file {file_path} does not exist.")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    
def remove_functions_used_within(functions_info):
    '''
    Removes functions that are used within the same file where they are defined
    '''
    functions_info_ = deepcopy(functions_info)
    functions_to_remove = [key for key, value in functions_info_.items() if is_function_used(key, value.path)]
    for key in functions_to_remove:
        del functions_info_[key]
    return  functions_info_

def remove_internal_functions(functions_info):
    '''
    Removes internal functions from the functions_info dictionary/box returned by extract_functions_docstring
    '''
    functions_info_ = deepcopy(functions_info)
    functions_to_remove = [key for key in functions_info_.keys() if key.startswith('_')]
    for key in functions_to_remove:
        del functions_info_[key]
    return functions_info_


def remove_referenced_docstrings(functions_info):
    '''
    Given functions_info returned by remove_internal_functions, returns the functions and their docstring if ":ref:" is not already in the docstring
    '''
    functions_info_ = deepcopy(functions_info)

    functions_to_remove = []

    for key, value in functions_info.items():
        if (isinstance(value.docstring, str) and ':ref:`sphx_glr_auto_examples_' in value.docstring) or value.docstring is None: 
            functions_to_remove.append(key)

    for key in functions_to_remove:
        del functions_info_[key]

    return functions_info_


def is_function_defined(file_path, function_name):
    '''
    Returns True if the function is defined in the py file, False otherwise
    '''
    with open(file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()
        tree = ast.parse(file_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                return True
    return False

def find_files_using_function(directory, function_name):
    '''
    Looks through the directory and all its subdirectories, returning a list of the paths of the py files which use a given function, "function_name"
    '''
    files_using_function = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    tree = ast.parse(file_content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call) and hasattr(node.func, 'id') and node.func.id == function_name and not is_function_defined(file_path, function_name):
                            files_using_function.append(file_path)
                            break
    return files_using_function

def find_files_using_functions(functions_info, directory):
    '''
    Performs find_files_using_function, provided functions_info, updating functions_info subdicts with a new key
    '''

    functions_info_ = deepcopy(functions_info)

    for key in functions_info_.keys():

        filenames = find_files_using_function(directory, key)
        functions_info_[key]['example_files'] = filenames 

    return functions_info_

def remove_unused_functions(functions_info):
    '''
    Removes functions from functions_info which do not have associated usage py files
    '''

    functions_info_ = deepcopy(functions_info)

    functions_to_remove = []

    for key, value in functions_info_.items():
        if len(value.example_files) == 0:
            functions_to_remove.append(key)

    for key in functions_to_remove:
        del functions_info_[key]

    return functions_info_

def count_mentions_from_url(target_string, url="https://github.com/scikit-learn/scikit-learn/issues/26927"):
    '''
    Given a URL, counts the occurrences of the target_string on the webpage
    '''
    response = requests.get(url)
    content = response.text
    occurrences = content.count(target_string)
    return occurrences

if __name__ == "__main__":
    directory = './scikit-learn/sklearn'

    py_files = find_all_py_files(directory)

    functions_info = dict()

    for file in py_files:

        info = extract_functions_docstrings(file)
        info = remove_internal_functions(info)
        info = remove_referenced_docstrings(info)
        info = find_files_using_functions(info, directory)
        info = remove_unused_functions(info)

        functions_info.update(info)

    dict(functions_info)