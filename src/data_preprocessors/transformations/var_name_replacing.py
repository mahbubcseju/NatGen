import math
import random
import re
from typing import Union, Tuple
import os

from src.data_preprocessors.language_processors import (
    JavaAndCPPProcessor,
    CSharpProcessor,
    PythonProcessor,
    JavascriptProcessor,
    PhpProcessor,
)
from src.data_preprocessors.language_processors.go_processor import GoProcessor
from src.data_preprocessors.language_processors.ruby_processor import RubyProcessor
from src.data_preprocessors.language_processors.utils import get_tokens
from src.data_preprocessors.transformations import TransformationBase
import os

processor_function = {
    "java": JavaAndCPPProcessor,
    "c": JavaAndCPPProcessor,
    "cpp": JavaAndCPPProcessor,
    "c_sharp": CSharpProcessor,
    "python": PythonProcessor,
    "javascript": JavascriptProcessor,
    "go": GoProcessor,
    "php": PhpProcessor,
    "ruby": RubyProcessor,
}

tokenizer_function = {
    "java": get_tokens,
    "c": get_tokens,
    "cpp": get_tokens,
    "c_sharp": get_tokens,
    "python": PythonProcessor.get_tokens,
    "javascript": JavascriptProcessor.get_tokens,
    "go": get_tokens,
    "php": PhpProcessor.get_tokens,
    "ruby": get_tokens,
}


class VarRenaming(TransformationBase):
    def __init__(
            self,
            parser_path: str,
            language: str,
            var_file_path: str,
            rename_ratio: float,
    ):
        super(VarRenaming, self).__init__(
            parser_path=parser_path,
            language=language,
        )
        self.language = language
        self.processor = processor_function[self.language]
        self.tokenizer_function = tokenizer_function[self.language]
        self.var_file_path = var_file_path
        self.rename_ratio = rename_ratio
        # self.read_variable_names()
        # C/CPP: function_declarator
        # Java: class_declaration, method_declaration
        # python: function_definition, call
        # js: function_declaration
        self.not_var_ptype = ["function_declarator", "class_declaration", "method_declaration", "function_definition",
                              "function_declaration", "call", "local_function_statement"]

    def extract_var_names(self, root, code_string):
        var_names = []
        queue = [root]
        restricted = {}
        while len(queue) > 0:
            current_node = queue[0]
            queue = queue[1:]

            try:
                if current_node.type.startswith("call"):
                    name = self.tokenizer_function(code_string, current_node)[0]
                    restricted[name] = 1
            except Exception as E:
                pass
            
            if (current_node.type == "identifier" or current_node.type == "variable_name") and str(
                    current_node.parent.type) not in self.not_var_ptype:
                name = self.tokenizer_function(code_string, current_node)[0]
                var_names.append(name)

            for child in current_node.children:
                queue.append(child)
        return [name for name in var_names if name not in restricted]

    def var_renaming(self, source_code_string, des_code_string):
        source_root = self.parse_code(source_code_string)
        source_original_code = self.tokenizer_function(source_code_string, source_root)
        source_var_names = self.extract_var_names(source_root, source_code_string)
        source_var_names = list(set(source_var_names))

        des_root = self.parse_code(des_code_string)
        des_original_code = self.tokenizer_function(des_code_string, des_root)
        des_var_names = self.extract_var_names(des_root, des_code_string)
        des_var_names = list(set(des_var_names))

        # print(source_var_names, des_var_names)

        num_to_rename = min(math.ceil(self.rename_ratio * len(des_var_names)), len(source_var_names))
        random.shuffle(des_var_names)
        var_names = des_var_names[:num_to_rename]
        var_map = {}
        target_vars = random.sample(source_var_names, num_to_rename)
        for idx, v in enumerate(var_names):
            var_map[v] = target_vars[idx]
        modified_code = []
        for t in des_original_code:
            if t in var_names:
                modified_code.append(var_map[t])
            else:
                modified_code.append(t)

        modified_code_string = " ".join(modified_code)
        if modified_code != des_original_code:
            modified_root = self.parse_code(modified_code_string)
            return modified_root, modified_code_string, True
        else:
            return des_root, des_code_string, False

    def transform_code(
            self,
            source_code: Union[str, bytes],
            des_code: Union[str, bytes], 
    ) -> Tuple[str, object]:
        root, code, success = self.var_renaming(source_code, des_code)
        code = re.sub("[ \n\t]+", " ", code)
        return code, {
            "success": success
        }


if __name__ == '__main__':
    java_code = """
    class A{
        int foo(int n){
            int res = 0;
            for(int i = 0; i < n; i++) {
                int j = 0;
                while (j < i){
                    res += j; 
                }
            }
            return res;
        }
    }
    """
    python_code = """def foo(n):
    res = 0
    for i in range(0, 19, 2):
        res += i
    i = 0
    while i in range(n):
        res += i
        i += 1
    return res
    """
    c_code = """
        int foo(int n){
            int res = 0;
            for(int i = 0; i < n; i++) {
                int j = 0;
                while (j < i){
                    res += j; 
                }
            }
            return res;
        }
    """
    cs_code = """
    int foo(int n){
            int res = 0, i = 0;
            while(i < n) {
                int j = 0;
                while (j < i){
                    res += j; 
                }
            }
            return res;
        }
    """
    js_code = """function foo(n) {
        let res = '';
        for(let i = 0; i < 10; i++){
            res += i.toString();
            res += '<br>';
        } 
        while ( i < 10 ; ) { 
            res += 'bk'; 
        }
        return res;
    }
    """
    ruby_code = """
        for i in 0..5 do
           puts "Value of local variable is #{i}"
           if false then
                puts "False printed"
                while i == 10 do
                    print i;
                end
                i = u + 8
            end
        end
        """
    go_code = """
        func main() {
            sum := 0;
            i := 0;
            for ; i < 10;  {
                sum += i;
            }
            i++;
            fmt.Println(sum);
        }
        """
    php_code = """
    <?php 
    for ($x = 0; $x <= 10; $x++) {
        echo "The number is: $x <br>";
    }
    $x = 0 ; 
    while ( $x <= 10 ) { 
        echo "The number is:  $x  <br> "; 
        $x++; 
    } 
    ?> 
    """
    input_map = {
        "java": ("java", java_code),
        "c": ("c", c_code),
        "cpp": ("cpp", c_code),
        "cs": ("c_sharp", cs_code),
        "js": ("javascript", js_code),
        "python": ("python", python_code),
        "php": ("php", php_code),
        "ruby": ("ruby", ruby_code),
        "go": ("go", go_code),
    }
    code_directory = os.path.realpath(os.path.join(os.path.realpath(__file__), '../../../..'))
    parser_path = os.path.join(code_directory, "parser/languages.so")
    for lang in ["c", "cpp", "java", "python", "php", "ruby", "js", "go", "cs"]:
        lang, code = input_map[lang]
        var_renamer = VarRenamer(
            parser_path, lang
        )
        print(lang)
        code, meta = var_renamer.transform_code(code)
        print(re.sub("[ \t\n]+", " ", code))
        print(meta)
        print("=" * 150)
