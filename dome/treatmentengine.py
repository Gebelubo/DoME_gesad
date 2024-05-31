import tests.tests


class TreatmentEngine:
    def __init__(self, parser):
        self.__MP = parser
        self.__AIE = self.__MP.get_ai_engine()
        self.entity = self.__MP.entity_class
        self.user_msg = self.__MP.user_msg
        self.tokens = self.__MP.tokens
        self.__TM = TreatmentManager(ResponseChecker(self), ResponseFixer(self))
        self.model_used = 0

    def treat(self, key, value, processed_attributes):
        new_response = self.__TM.manage(key, value, processed_attributes)
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
        # if not work try to find anyway
        new_value = self.__RF.string_treatment(key)
        if self.__RC.check(key, new_value, processed_attributes):
            return new_value

        return value

    def manage_prompt(self, key, value, processed_attributes):
        prompts = ["simplified_all", "simplified_question", "invalid_and", "invalid_comma"]
        for prompt in prompts:
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
    def __init__(self, treatment_engine):
        self.__TE = treatment_engine
        self.entity = self.__TE.entity
        self.tokens = self.__TE.tokens
        self.methods = [self.key_test, self.and_test, self.entity_test, self.attributes_test, self.pronoun_test,
                        self.ignoring_test, self.float_test]

    def check(self, key, value, processed_attributes):
        for method in self.methods:
            if method(key, value, processed_attributes) == False:  # args[0], args[1], args[2]
                return False
        return True

    def key_test(self, *args):
        if args[0] in args[1]:  # if the attribute value is equal to the name
            tests.tests.add_treaments('key_error')
            return False
        return True

    def and_test(self, *args):
        if " and " in args[1]:  # if there is "and" in the answer
            tests.tests.add_treaments('and_error')
            return False
        return True

    def entity_test(self, *args):
        if self.entity in args[1]:  # if the entity name is in the attribute value
            tests.tests.add_treaments('entity_error')
            return False
        return True

    def attributes_test(self, *args):
        if args[2] is not None:  # if some other attribute name is in the attribute value
            for keys in list(args[2].keys()):
                if keys in args[1]:
                    tests.tests.add_treaments('attribute_error')
                    return False
        return True

    def pronoun_test(self, *args):
        tokens = self.__TE.tokenize(args[1])
        propn = False
        for token in tokens:  # if there is a pronoun followed by a comma
            if propn == True and token['entity'] == 'PUNCT':
                tests.tests.add_treaments('pronoun_error')
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
            tests.tests.add_treaments('ignoring_error')
            return False
        return True

    def float_test(self, *args):
        float_find = None
        j = 0
        while j < len(self.tokens):
            if self.tokens[j]['entity'] == 'PUNCT' and j > 0:
                if self.tokens[j + 1]['entity'] == 'NUM' and self.tokens[j - 1]['entity'] == 'NUM':
                    # exists a float number in the original mensage
                    float_find = self.tokens[j - 1]['word']
            j += 1

        if float_find is None:
            return True

        if float_find in args[1] and (',' not in args[1] and '.' not in args[1]):
            tests.tests.add_treaments('float_error')
            return False

        return True


class ResponseFixer:
    def __init__(self, treatment_engine):
        self.__TE = treatment_engine
        self.entity = self.__TE.entity
        self.user_msg = self.__TE.user_msg

    def prompt_treatment(self, key, prompt):

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
            tests.tests.add_treaments('simplified_prompt_treatment')
        elif prompt == "simplified_question":  # simplifying the question and enhancing the context
            question = "What is the '" + key + "' in the sentence fragment?"
            fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
            context = "\nThis is the user command: '" + self.user_msg + "'."
            context += 'The answer is a substring of "' + fragment_short + '".'
            tests.tests.add_treaments('simplified_question_prompt_treatment')
        elif prompt == "invalid_and":  # case the answer is returning a word after an 'and'
            fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
            fragment_short = fragment_short.split('and')[0]
            context = 'The answer is a substring of "' + fragment_short + '".'
            tests.tests.add_treaments('and_prompt_treatment')
        elif prompt == "invalid_comma":  # case the answer is returning a word after an invalid ','
            fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
            fragment_short = fragment_short.split(',')[0]
            context = 'The answer is a substring of "' + fragment_short + '".'
            tests.tests.add_treaments('comma_prompt_treatment')
        else:
            context = ''
            fragment_short = ''

        response = self.__TE.question_answerer_remote(question, context)
        if response['answer'] is not None and response['answer'] != 'None':
            return response
        else:
            return {'answer': fragment_short}

    def string_treatment(self, key):
        # getting everything after the attribute key and before an addition marker
        fragment_short = self.user_msg[self.user_msg.find(key) + len(key):]
        fragment_short = fragment_short.split('and')[0]
        tests.tests.add_treaments('and_comma_string_treatment')
        return fragment_short
