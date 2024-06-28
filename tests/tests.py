import json
import os

class Test:
    def __init__(self, input_file, output_file):
        self.output_file = output_file
        self.input_file = input_file
        self.input = self.read()
        self.output = self.input
        self.generated_query = ""
        self.generated_response = ""
        self.treatment_flow = []
        self.treatments = []
    
    def read(self):
        data = os.path.abspath(os.path.join(os.path.dirname(__file__), self.input_file))
        with open(data, 'r') as file:
            return json.load(file)

    def write(self):
        output_file = os.path.abspath(os.path.join(os.path.dirname(__file__), self.output_file))
        with open(output_file, 'w') as file:
            json.dump(self.output, file, indent=4)

    def add_treatment_flow(self, treatment_flow):
        self.treatment_flow.append(treatment_flow)

    def add_treatment(self, treatment):
        self.treatments.append(treatment)

    def insert_data(self, index):
        self.output[index]['generated_query'] = self.generated_query
        self.output[index]['generated_result'] = self.generated_response
        self.output[index]['treatment_flow'] = self.treatment_flow
        self.output[index]['treatments'] = self.treatments
        self.generated_query = ""
        self.generated_response = ""
        self.treatment_flow = []
        self.treatments = []