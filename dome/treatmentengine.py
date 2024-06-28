import tests.tests
import re


class TreatmentEngine:
    def __init__(self, parser, test):
        self.__MP = parser
        self.__Test = test
        self.__AIE = self.__MP.get_ai_engine()
        self.entity = self.__MP.entity_class
        self.user_msg = self.__MP.user_msg
        self.tokens = self.__MP.tokens
        self.__TM = TreatmentManager(ResponseChecker(self, test), ResponseFixer(self, test))
        self.model_used = 0

    def treat(self, key, value, processed_attributes):
        new_response = self.__TM.manage(key, value, processed_attributes)
        new_response = re.sub(r'^\s+|\s+$', '', new_response)
        new_response = new_response.replace('=', '').replace("'", '').replace('"', '').replace('\\', '').replace('/','')
        if not self.response_validate({key: new_response}):
            self.change_model()
            new_response = self.__TM.manage(key, value, processed_attributes)
        return new_response

    def tokenize(self, msg):
        return self.__AIE.posTagMsg(msg)

    def question_answerer_remote(self, question, context):
        return self.__AIE.question_answerer_remote(question, context, '', False, self.model_used)

    def response_validate(self, response):
        if self.__TM.response_validate(response):
            return True
        return False

    def change_model(self):
        if self.model_used == 0:
            self.model_used = 1
        else:
            self.model_used = 0


class TreatmentManager:
    def __init__(self, checker_obj, fixer_obj):
        self.__RC = checker_obj
        self.__RF = fixer_obj

    def manage(self, key, value, processed_attributes):

        valid = self.__RC.check(key, value, processed_attributes)

        if valid:
            return value

        new_value = value

        # first we will try to change the prompt to treat
        new_value = self.manage_prompt(key, new_value, processed_attributes)
        if new_value is not None:
            return new_value
        
        new_value = self.__RF.searching_treatment(key, value)
        if self.__RC.check(key, new_value, processed_attributes):
            return new_value
        
        # if not work try to find anyway
        new_value = self.__RF.string_and_treatment(key)
        if self.__RC.check(key, new_value, processed_attributes):
            return new_value
        
        new_value = self.__RF.string_noise_treatment(key)
        if self.__RC.check(key, new_value, processed_attributes):
            return new_value

        return value

    def manage_prompt(self, key, value, processed_attributes):
        prompts = ["simplified_all", "simplified_question", "invalid_and", "invalid_comma", "simplified_max"]
        for prompt in prompts:
            print(prompt)
            print(key)
            new_value = self.__RF.prompt_treatment(key, prompt)['answer']
            if self.__RC.check(key, new_value, processed_attributes):
                return new_value
        return None

    def response_validate(self, response):
        keys = list(response.keys())

        for key in keys:
            if self.__RC.check(key, response[key], response):
                return True

        return False


class ResponseChecker:
    def __init__(self, treatment_engine, test):
        self.__TE = treatment_engine
        self.__Test = test
        self.entity = self.__TE.entity
        self.tokens = self.__TE.tokens
        self.methods = [self.key_test, self.and_test, self.entity_test, self.attributes_test, self.pronoun_test,
                        self.ignoring_test, self.float_test, self.character_test]

    def check(self, key, value, processed_attributes):
        for method in self.methods:
            if method(key, value, processed_attributes) == False:  # args[0], args[1], args[2]
                return False
        return True

    def key_test(self, *args):
        if args[0] in args[1]:  # if the attribute value is equal to the name
            self.__Test.add_treatment_flow("key_test")
            return False
        return True

    def and_test(self, *args):
        if " and " in args[1]:  # if there is "and" in the answer
            self.__Test.add_treatment_flow("and_test")
            return False
        return True

    def entity_test(self, *args):
        if self.entity in args[1]:  # if the entity name is in the attribute value
            self.__Test.add_treatment_flow("entity_test")
            return False
        return True

    def attributes_test(self, *args):
        if args[2] is not None:  # if some other attribute name is in the attribute value
            for keys in list(args[2].keys()):
                if keys in args[1]:
                    self.__Test.add_treatment_flow("attributes_test")
                    return False
        return True

    def pronoun_test(self, *args):
        tokens = self.__TE.tokenize(args[1])
        propn = False
        for token in tokens:  # if there is a pronoun followed by a comma
            if propn == True and token['entity'] == 'PUNCT':
                self.__Test.add_treatment_flow("pronoun_test")
                return False
            if token['entity'] == 'PROPN':
                propn = True
        return True

    def ignoring_test(self, *args):
        key_find = False
        tokens_entity = list()
        for token in self.tokens:  # discovering if it is ignoring relevant attributes
            if token['word'] is not None:
                if token['word'] == args[0] and key_find == False:
                    key_find = True
                    continue
                if key_find:
                    if token['word'] in args[1].lower():
                        break
                    tokens_entity.append(token['entity'])

        if 'PROPN' in tokens_entity or 'NUM' in tokens_entity:
            self.__Test.add_treatment_flow("ignoring test")
            return False
        return True

    def float_test(self, *args):
        float_find = None
        j = 0
        while j < len(self.tokens):
            if self.tokens[j]['entity'] == 'PUNCT' and j > 0:
                if j+1<len(self.tokens):
                    if self.tokens[j + 1]['entity'] == 'NUM' and self.tokens[j - 1]['entity'] == 'NUM':
                        # exists a float number in the original mensage
                        float_find = self.tokens[j - 1]['word']
            j += 1

        if float_find is None:
            return True

        if float_find in args[1] and (',' not in args[1] and '.' not in args[1]):
            self.__Test.add_treatment_flow("float_test")
            return False

        return True

    def character_test(self, *args):
        tokens = self.__TE.tokenize(args[1])
        potential_value = False
        for token in tokens:  # if there is some "noise character" on the final answer
            if potential_value == True and token['entity'] == 'SYM':
                self.__Test.add_treatment_flow("character_test")
                return False
            if token['entity'] == 'PROPN' or token['entity'] == 'NUM':
                potential_value = True
        return True


class ResponseFixer:
    def __init__(self, treatment_engine, test):
        self.__TE = treatment_engine
        self.__Test = test
        self.entity = self.__TE.entity
        self.user_msg = self.__TE.user_msg

    def prompt_treatment(self, key, prompt):

        self.__Test.add_treatment_flow("attribute: " + key)

        if key is None:
            # error
            return None

        question = "What is the '" + key + "' in the sentence fragment?"
        context = ''

        question += "\nThis is the user command: '" + self.user_msg + "'."
        question += "\nThe entity class is '" + str(self.entity) + "'."

        if prompt == "simplified_all":  # simplifying the prompt
            fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
            context = 'The answer is a substring of "' + fragment_short + '".'
            self.__Test.add_treatment_flow("simplified_all_treatment")
            self.__Test.add_treatment("simplified_all_treatment")
        elif prompt == "simplified_question":  # simplifying the question and enhancing the context
            question = "What is the '" + key + "' in the sentence fragment?"
            fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
            context = "\nThis is the user command: '" + self.user_msg + "'."
            context += 'The answer is a substring of "' + fragment_short + '".'
            self.__Test.add_treatment_flow("simplified_question_treatment")
            self.__Test.add_treatment("simplified_question_treatment")
        elif prompt == "invalid_and":  # case the answer is returning a word after an 'and'
            fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
            fragment_short = fragment_short.split('and')[0]
            context = 'The answer is a substring of "' + fragment_short + '".'
            self.__Test.add_treatment_flow("invalid and_treatment")
            self.__Test.add_treatment("invalid_and_treatment")
        elif prompt == "invalid_comma":  # case the answer is returning a word after an invalid ','
            fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
            fragment_short = fragment_short.split(',')[0]
            context = 'The answer is a substring of "' + fragment_short + '".'
            self.__Test.add_treatment_flow("invalid_comma_treatment")
            self.__Test.add_treatment("invalid_comma_treatment")
        elif prompt == "simplified_max":
            question = (
    f"Identify the value assigned to '{key}' in the following user command. Return only the value. "
    f"value mentioned in the user command. Return only the value. \n\nUser command: '{self.user_msg}' "
    f"\nValue of '{key}': "
            )   
            self.__Test.add_treatment_flow("simplified_max_treatment")
            self.__Test.add_treatment("simplified_max_treatment")
        else:
            context = ''
            fragment_short = ''

        response = self.__TE.question_answerer_remote(question, context)
        print(response)
        self.__Test.add_treatment_flow("output: " + response['answer'])
        if response['answer'] is not None and response['answer'] != 'None':
            return response
        else:
            return {'answer': fragment_short}

    def searching_treatment(self, key, value):
        print("searching")
        print(value)
        self.__Test.add_treatment_flow("attribute: " + key)
        self.__Test.add_treatment_flow("searching_treatment")
        self.__Test.add_treatment_flow("searching_treatment")
        list_value = value.replace('\n', ' ')
        list_value = value.split()
        answer = ''
        print(list_value)
        fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
        for word in list_value:
            print(word)
            if word.isalnum():
                if word in fragment_short:
                    print("vai retornar")
                    print(word)
                    answer = word
                    break
        if not answer:
            print("retornou value")
            answer = value
        answer = answer.replace('=', '').replace("'", '').replace('"', '').replace('\\', '').replace('/','')
        self.__Test.add_treatment_flow("output: " + answer)
        return answer

    def string_and_treatment(self, key):
        # getting everything after the attribute key and before an addition marker
        fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
        fragment_short = fragment_short.split('and')[0]
        self.__Test.add_treatment_flow("attribute: " + key)
        self.__Test.add_treatment_flow("string_and_treatment")
        self.__Test.add_treatment("string_and_treatment")
        return fragment_short
    
    def string_noise_treatment(self, key):
        fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
        fragment_short = fragment_short.replace('=', '').replace("'", '').replace('"', '')
        self.__Test.add_treatment_flow("output: " + key)
        self.__Test.add_treatment_flow("string_noise_treatment")
        self.__Test.add_treatment_flow("string_noise_treatment")
        return fragment_short
    
