import json
import os

def read():
    data = os.path.abspath(os.path.join(os.path.dirname(__file__), 'input.json'))
    with open(data, 'r') as file:
        return json.load(file)


def write():
    output_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'output.json'))
    output_line=0
    input_line=0
    with open(output_file, 'w') as file:
        json.dump(output, file, indent=4)


def initialize_line():
    global output_line
    if 'expected_query' in input_list[output_line] and 'expected_result' in input_list[output_line]:
        input_value = input_list[output_line]['input']
        expected_query = input_list[output_line]['expected_query']
        expected_result = input_list[output_line]['expected_result']
        content = {'input': input_value,
                   'expected_query': expected_query,
                   'expected_result': expected_result}
        output.append(content)


def add(key, value):
    output[output_line][key] = value


def add_output_line():
    global output_line, treatments
    if treatments:
        output[output_line]['treatments'] = treatments
        treatments = []
    else:
        output[output_line]['treatments'] = "No treatment"
    output_line += 1
    initialize_line()


def add_input_line():
    global input_line
    input_line += 1


def return_data():
    return input_list[input_line]


def add_treaments(report):
    treatments.append(report)


input_list = read()
input_line = 0
output = []
output_line = 0
treatments = []
initialize_line()
