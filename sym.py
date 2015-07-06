#!/usr/bin/env python3

import re
import os
import codecs
from PIL import Image

class SymRuleType:
    UNKNOWN = 0
    CONTAIN = 1
    BEGIN_WITH = 2
    END_WITH = 3
    EQUAL = 4
    REGEX = 5

    @classmethod
    def toType(cls, s):
        for t in [cls.CONTAIN, cls.BEGIN_WITH, cls.END_WITH, cls.EQUAL, cls.REGEX]:
            if s == cls.toStr(t):
                return t
        return cls.UNKNOWN

    @classmethod
    def toStr(cls, t):
        if t == cls.CONTAIN:
            return 'Contain'
        elif t ==cls.BEGIN_WITH:
            return  'BeginWith'
        elif t ==cls.END_WITH:
            return  'EndWith'
        elif t ==cls.EQUAL:
            return  'Equal'
        elif t ==cls.REGEX:
            return  'Regex'
        else:
            return 'Unknown'
    
class SymbolRules:
    def __init__(self, path):
        self.__path = path
        self.__rules = []
        self.load()
    
    def __iter__(self):
        return iter(self.__rules)

    def __len__(self):
        return len(self.__rules)

    def load(self):
        path = self.__path

        #get all line
        with codecs.open(path, 'r', encoding='utf8') as f:
            lines = []
            for line in f:
                line = line.rstrip()
                if len(line) == 0:
                    rule = self.createRule(lines)
                    self.__rules.append(rule)
                    lines.clear()
                else:
                    lines.append(line)

        #print('get', len(self), 'rules')
        #i = 0
        #for rule in self:
        #    print(i, ':', rule.enabled, SymRuleType.toStr(rule.type), rule.text, rule.symbol)
        #    i += 1

    def createRule(self, lines):
        rule = SymRule()

        for line in lines:
            k, v = line.split('=')

            if k == "Enabled":
                rule.enabled = (v == "True")
            elif k == "Type":
                rule.type = SymRuleType.toType(v)
            elif k == "Text":
                rule.text = v
            elif k == "Symbol":
                rule.symbol = v
            else:
                raise ValueError("Unknown key of SymbolRule")

        return rule

    def save(self, path=None):
        if path is None:
            path = self.__path

        with codecs.open(path, 'w', encoding='utf8') as f:
            for rule in self:
                f.write("Enabled=" + str(rule.enabled) + '\n')
                f.write("Type=" + SymRuleType.toStr(rule.type) + '\n')
                f.write("Text=" + rule.text + '\n')
                f.write("Symbol=" + rule.symbol + '\n')
                f.write('\n')

    
    def getMatchRule(self, name):
        for rule in self:
            if rule.isMatch(name):
                return rule
        return None

class SymRule:
    #{{ static
    __icons = {}
    ICON_SIZE = 24
    DEF_SYMBOL = "Waypoint"
    #}}

    def __init__(self):
        self.enabled = True
        self.type = SymRuleType.CONTAIN
        self.text = ""
        self.symbol = self.DEF_SYMBOL

    def isMatch(self, wpt_name):
        if not self.enabled:
            return False

        if self.type == SymRuleType.CONTAIN:
            return self.text in wpt_name
        elif self.type == SymRuleType.BEGIN_WITH:
            return wpt_name.startswith(self.text)
        elif self.type == SymRuleType.BEGIN_WITH:
            return wpt_name.startswith(self.text)
        elif self.type == SymRuleType.EQUAL:
            return wpt_name == self.text
        elif self.type == SymRuleType.REGEX:
            return re.match(self.text, wpt_name)
        else:
            return False

    @classmethod
    def getIcon(cls, name):
        name = name.lower()
        icon = cls.__icons.get(name)
        if icon is None:
            path = os.path.join("./icon", name + ".png")
            if not os.path.exists(path) and name != cls.DEF_SYMBOL:
                return cls.getIcon(cls.DEF_SYMBOL)
            icon = Image.open(path)
            icon = icon.resize((cls.ICON_SIZE, cls.ICON_SIZE))
            cls.__icons[name] = icon
        return icon


if __name__ == '__main__':
    rules = SymbolRules('./sym_rule.conf')
    rules.save('./sym_rule.conf.out')
    print(rules.getMatchRule('-').symbol)
    print(rules.getMatchRule('2.2k').symbol)
