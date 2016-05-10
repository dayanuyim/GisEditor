#!/usr/bin/env python3

import re
import os
import codecs
import tkinter as tk
import Pmw as pmw
from PIL import Image, ImageTk
from math import ceil
#my
import src.conf as conf
import src.util as util

# symbol icon ======================================
def __getSymIcons(icon_dir):
    sym_icons = {}
    try:
        for f in os.listdir(icon_dir):
            p = os.path.join(icon_dir, f)
            if os.path.isfile(p):
                name, ext = os.path.splitext(f)
                sym = conf._tosymkey(name)
                sym_icons[sym] = (p, None)
    except Exception as ex:
        logging.error('read icons error: ' + str(ex))
    return sym_icons

#sym->icon_path, icon_image
__sym_icons = __getSymIcons(conf.ICON_DIR)

def getAllSymbols():
    return __sym_icons.keys()

def getIcon(sym, def_sym=conf.DEF_SYMBOL):
    sym = conf._tosymkey(sym)
    icon = __getIcon(sym)
    if not icon and sym != def_sym:
        return __getIcon(def_sym) #return default
    return icon

def __getIcon(sym):
    icon = __sym_icons.get(sym)
    if not icon:
        return None
    path, img = icon
    if img is None:
        img = __readIcon(path, conf.ICON_SIZE)
        if img:
            __sym_icons[sym] = (path, img)
    return img

def __readIcon(path, sz):
    if path is None:
        return None
    icon = Image.open(path)
    icon = icon.resize((sz, sz))
    return icon

#symbol board ======================================
class SymBoard(tk.Toplevel):
    @property
    def sym(self): return self.__sym

    @sym.setter
    def sym(self, val):
        self.__sym = val
        if val is None:
            self.selectSymWidget(None)
        else:
            val = conf._tosymkey(val)
            w = self.__widgets.get(val)
            self.selectSymWidget(w)

    @property
    def pos(self): return self.__pos

    @pos.setter
    def pos(self, val):
        val = (0,0) if not val else util.getPrefCornerPos(self, val)
        self.geometry('+%d+%d' % val)
        self.__pos = val

    def __init__(self, master=None):
        super().__init__(master)

        self.__parent = None #for show/onClosed
        self.__col_sz = 20
        self.__bg_color = self.cget('bg')
        self.__ext_bg_color = 'gray'
        self.__hl_bg_color = 'lightblue'
        self.__filter_bg_color = 'red'
        self.__sym = None
        self.__curr_widget = None
        self.__widgets = {}
        self.__pos = (0, 0)

        #board
        self.title('')
        self.resizable(0, 0)
        self.bind('<Escape>', self.onClosed)
        self.protocol('WM_DELETE_WINDOW', lambda: self.onClosed(None))

        #init
        all_syms = getAllSymbols()
        self.__app_syms = conf.APP_SYMS;
        self.__ext_syms = util.listdiff(all_syms, self.__app_syms)

        sn = 0
        for sym in self.__app_syms:
            self.showSym(sym, sn, self.__bg_color)
            sn += 1

        sn = self.getNextRowSn(sn)
        for sym in self.__ext_syms:
            self.showSym(sym, sn, self.__ext_bg_color)
            sn += 1

        span = max(1, int(self.__col_sz/3))
        row, col = self.toRowCol(self.getNextRowSn(sn))
        self.__var_filter = tk.StringVar()
        self.__var_filter.trace('w', self.onFilterSym)
        filter_entry = tk.Entry(self, textvariable=self.__var_filter)
        filter_entry.grid(row=row, column=col+self.__col_sz-span, columnspan=span, sticky='news')

        #hidden
        self.withdraw()  #for silent update
        self.visible = tk.BooleanVar(value=False)

        #update window size
        self.update()  

    def show(self, parent):
        self.__parent = parent #rec

        #UI
        self.transient(parent)  #remove max/min buttons
        self.focus_set()  #prevent key-press sent back to parent
        
        self.deiconify() #show
        self.visible.set(True)

        self.grab_set()   #disalbe interact of parent
        parent.wait_variable(self.visible)

    def onClosed(self, e):
        if self.__parent is not None:
            self.__parent.focus_set()
        self.grab_release()

        #self.destroy()
        self.withdraw()
        self.visible.set(False)

    def toRowCol(self, sn):
        return int(sn/self.__col_sz), sn%self.__col_sz

    def getNextRowSn(self, sn):
        return ceil(sn/self.__col_sz) * self.__col_sz

    def showSym(self, sym, sn, bg_color):

        txt = ""
        icon = ImageTk.PhotoImage(getIcon(sym))

        disp = tk.Label(self)
        disp.config(image=icon, text=txt, compound='left', anchor='w', bg=bg_color)
        disp.image=icon

        row, col = self.toRowCol(sn)
        disp.grid(row=row, column=col, sticky='we')
        disp.bind('<Motion>', self.onMotion)
        disp.bind('<Button-1>', self.onClick)

        #save
        disp.sym = sym
        self.__widgets[sym] = disp

    def onMotion(self, e):
        self.selectSymWidget(e.widget)

    def onFilterSym(self, *args):
        #reet 
        self.sym = None

        f = self.__var_filter.get().lower()
        for w in self.children.values():
            if hasattr(w, 'sym'):
                sym = w.sym.lower()
                w['bg'] = self.__filter_bg_color if f and f in sym else self.getWidgetsBgColor(w)

    def getWidgetsBgColor(self, widget):
        return self.__bg_color if widget.sym in self.__app_syms else self.__ext_bg_color

    #careful: widget could be None
    def selectSymWidget(self, widget):
        if self.__curr_widget != widget:
            self.unhighlight(self.__curr_widget)
            self.highlight(widget)
        self.__curr_widget = widget

    def unhighlight(self, widget):
        if widget is not None:
            if widget['bg'] != self.__filter_bg_color:
                widget['bg'] = self.getWidgetsBgColor(widget)

    def highlight(self, widget):
        if widget is not None:
            if widget['bg'] != self.__filter_bg_color:
                widget['bg'] = self.__hl_bg_color
            self.title(widget.sym)
        else:
            self.title("")

    def onClick(self, e):
        self.__sym = e.widget.sym
        self.onClosed(None)

    #}}

# symbol rules =====================================
class SymRuleType:
    UNKNOWN = 0
    CONTAIN = 1
    BEGIN_WITH = 2
    END_WITH = 3
    EQUAL = 4
    REGEX = 5

    @classmethod
    def types(cls):
        return [cls.CONTAIN, cls.BEGIN_WITH, cls.END_WITH, cls.EQUAL, cls.REGEX]

    @classmethod
    def toType(cls, s):
        for t in cls.types():
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
    
class SymRule:
    def __init__(self):
        self.enabled = True
        self.type = SymRuleType.CONTAIN
        self.text = ""
        self.symbol = conf.DEF_SYMBOL

    def isMatch(self, wpt_name):
        if not self.enabled:
            return False

        if self.type == SymRuleType.CONTAIN:
            return self.text in wpt_name
        elif self.type == SymRuleType.BEGIN_WITH:
            return wpt_name.startswith(self.text)
        elif self.type == SymRuleType.END_WITH:
            return wpt_name.endswith(self.text)
        elif self.type == SymRuleType.EQUAL:
            return wpt_name == self.text
        elif self.type == SymRuleType.REGEX:
            return re.match(self.text, wpt_name)
        else:
            return False

    def clone(self):
        rule = SymRule()
        rule.enabled = self.enabled
        rule.type = self.type
        rule.text = self.text
        rule.symbol = self.symbol
        return rule

class SymbolRules:
    def __init__(self, path):
        self.__path = path
        self.__rules = []
        self.load()
    
    def __iter__(self):
        return iter(self.__rules)

    def __len__(self):
        return len(self.__rules)

    def __getitem__(self, idx):
        return self.__rules[idx]

    def __setitem__(self, idx, val):
        self.__rules[idx] = value

    def __delitem__(self, idx):
        del self.__rules[idx]

    def append(self, item):
        self.__rules.append(item)

    def remove(self, item):
        self.__rules.remove(item)

    def index(self, item):
        return self.__rules.index(item)

    def insert(self, idx, item):
        self.__rules.insert(idx, item)

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

class SymRuleBoard(tk.Toplevel):
    @property
    def pos(self): return self.__pos

    @pos.setter
    def pos(self, val):
        val = (0,0) if not val else getPrefCornerPos(self, val)
        self.geometry('+%d+%d' % val)
        self.__pos = val

    def __init__(self, master, rules):
        super().__init__(master)

        self.__parent = None
        self.__bg_color = self.cget('bg')
        self.__hl_bg_color = 'lightblue'
        self.__focused_rule = None
        self.__widgets = {}
        self.__var_widgets = {}
        self.__rules = rules
        if not hasattr(self.__rules, 'is_altered'):
            self.__rules.is_altered = tk.BooleanVar(value=False)
        self.__font = 'Arialuni 12'
        self.__bfont = 'Arialuni 12 bold'
        self.__pos = (0,0)

        #board
        self.title('Symbol Rules')
        self.bind('<Escape>', self.onClosed)
        self.protocol('WM_DELETE_WINDOW', lambda: self.onClosed(None))

        self.init()
        self.initRightMenu()
        self.initTypeMenu()

        #hidden and silent update
        self.withdraw()  #hidden
        self.visible = tk.BooleanVar(value=False)
        self.update()  

    def show(self, parent):
        self.__parent = parent #rec

        #UI
        self.transient(parent)  #remove max/min buttons
        self.focus_set()  #prevent key-press sent back to parent
        
        self.deiconify() #show
        self.visible.set(True)

        self.grab_set()   #disalbe interact of parent
        parent.wait_variable(self.visible)

    def onClosed(self, e):
        if self.__parent:
            self.__parent.focus_set()
        self.grab_release()

        #self.destroy()
        self.withdraw()
        self.visible.set(False)

    def init(self):
        self.sf = pmw.ScrolledFrame(self, usehullsize = 1, hull_width = 450, hull_height = 600)
        self.sf.pack(side='bottom', anchor='nw', fill = 'both', expand = 1)

        self.__dec_btn = tk.Button(self, text='↑', state='disabled', command=lambda: self.onPriorityMove(-1))
        self.__dec_btn.pack(side='right', anchor='ne')

        self.__inc_btn = tk.Button(self, text='↓', state='disabled', command=lambda: self.onPriorityMove(1))
        self.__inc_btn.pack(side='right', anchor='ne')

        self.__save_btn = tk.Button(self, text='Save', command=lambda: self.onSave())
        self.__save_btn.pack(side='left', anchor='nw')
        self.__rules.is_altered.trace('w', self.setSaveButtonState)
        self.setSaveButtonState() #init invoke

        frame = self.sf.interior()
        bfont = self.__bfont

        row = 0
        #tk.Label(frame, text='Enabled', font=bfont).grid(row=row, column=0)
        tk.Label(frame, text='Type',  font=bfont, anchor='w').grid(row=row, column=1, sticky='news')
        tk.Label(frame, text='Text',  font=bfont, anchor='w').grid(row=row, column=2, sticky='news')
        tk.Label(frame, text='Symbol', font=bfont, anchor='w').grid(row=row, column=3, sticky='news')

        for rule in self.__rules:
            row += 1
            self.genRuleWidgets(rule, row)  #view
            self.setRuleWidgets(rule)      #data

    def setSaveButtonState(self, *args):
        self.__save_btn['state'] = 'normal' if self.__rules.is_altered.get() else 'disabled' 

    def genRuleWidgets(self, rule, row):
        bfont = self.__bfont
        font = self.__font

        #config
        frame = self.sf.interior()
        en_label = tk.Label(frame, font=bfont, anchor='e')
        self.setWidgetCommon(en_label, row, 0)

        type_label = tk.Label(frame, font=font, anchor='w')
        self.setWidgetCommon(type_label, row, 1)

        #text_label = tk.Label(frame, font=font)
        text_label = tk.Entry(frame, font=font, relief='flat', \
                state='disabled', disabledforeground='black',disabledbackground=self.__bg_color)
        self.setWidgetEditable(text_label, self.onTextWrite)
        self.setWidgetCommon(text_label, row, 2)

        sym_label = tk.Label(frame, font=font, compound='left', anchor='w')
        self.setWidgetCommon(sym_label, row, 3)

        #save
        self.__widgets[rule] = (
                en_label,
                type_label,
                text_label,
                sym_label
        )

    def onSave(self):
        self.__rules.save()
        self.__rules.is_altered.set(False)

    def getWidgetsRow(self, rule):
        w = self.__widgets[rule]
        row = w[0].grid_info()['row']
        return row

    def resetWidgetsRow(self, widgets, row):
        col = 0
        for w in widgets:
            w.grid(row=row, column=col, sticky='news')
            col += 1

    def shiftWidgetsRow(self, rule, inc):
        widgets = self.__widgets[rule]
        row = self.getWidgetsRow(rule)

        for w in widgets: w.grid_forget()
        self.resetWidgetsRow(widgets, row+inc)

    def swapWidgetsRow(self, rule1, rule2):
        w1 = self.__widgets[rule1]
        w2 = self.__widgets[rule2]

        r1 = self.getWidgetsRow(rule1)
        r2 = self.getWidgetsRow(rule2)

        for w in w1: w.grid_forget()
        for w in w2: w.grid_forget()

        self.resetWidgetsRow(w1, r2)
        self.resetWidgetsRow(w2, r1)

    def onPriorityMove(self, inc):
        rule1 = self.__focused_rule
        idx1 = self.__rules.index(rule1)
        idx2 = idx1+inc
        rule2 = self.__rules[idx2]

        #view
        self.swapWidgetsRow(rule1, rule2)

        #data
        self.__rules.remove(rule1)
        self.__rules.insert(idx2, rule1)
        self.__rules.is_altered.set(True)

    def setRuleWidgets(self, rule):
        en_w, type_w, txt_w, sym_w = self.__widgets[rule]

        en_text = 'v' if rule.enabled else 'x'
        en_color = 'green' if rule.enabled else 'red'
        en_w.config(text=en_text, fg=en_color)

        type_txt = SymRuleType.toStr(rule.type)
        type_w.config(text=type_txt)

        #txt_w.config(text=rule.text)
        txt_w.variable.set(rule.text)

        icon = ImageTk.PhotoImage(getIcon(rule.symbol))
        sym_w.config(image=icon, text=rule.symbol)
        sym_w.image=icon

    def setWidgetCommon(self, w, row, col):
        w.bind('<Motion>', self.onMotion)
        w.bind('<Button-1>', self.onClick)
        w.bind('<Button-3>', self.onRightClick)
        w.grid(row=row, column=col, sticky='news')

    def getRuleOfWidget(self, widget):
        for rule, widgets in self.__widgets.items():
            if widget in widgets:
                return rule
        return None

    def onMotion(self, e):
        prev = self.__focused_rule
        curr = self.getRuleOfWidget(e.widget)

        #highligt/unhighlight
        if prev != curr:
            self.setRuleBgColor(prev, self.__bg_color)
            self.setRuleBgColor(curr, self.__hl_bg_color)
                
        #rec
        self.__focused_rule = curr
        self.__dec_btn.config(state=('disabled' if curr == self.__rules[0] else 'normal'))
        self.__inc_btn.config(state=('disabled' if curr == self.__rules[-1] else 'normal'))

    def setRuleBgColor(self, rule, color):
        if rule is not None:
            for w in self.__widgets[rule]:
                if w.cget('state') == 'disabled':
                    w.config(disabledbackground=color)
                else:
                    w.config(bg=color)

    def setWidgetEditable(self, w, cb):
        var = tk.StringVar()
        w.config(textvariable=var)
        w.variable = var  #keep ref: widget->var
        self.__var_widgets[str(var)] = w  #keep ref: var->widget

        def onEnterEdit(e):
            e.widget.config(state='normal')
            e.widget.focus_set()

        def onLeaveEdit(e):
            if e.widget.cget('state') == 'normal':
                e.widget.config(state='disabled')

        def onEditWrite(*args):
            var_name = args[0]
            widget = self.__var_widgets.get(var_name)
            cb(widget)

        w.bind('<Double-Button-1>', onEnterEdit)
        w.bind('<Leave>', onLeaveEdit)
        w.bind('<Return>', onLeaveEdit)
        w.variable.trace_variable('w', onEditWrite)

    def initTypeMenu(self):
        menu = tk.Menu(self, tearoff=0)
        #for t in SymRuleType.types():
        #    txt = SymRuleType.toStr(t)
        #    menu.add_command(label=txt, command=lambda:self.onTypeWrite(t))

        menu.add_command(label='Contain', command=lambda: self.onTypeWrite(SymRuleType.CONTAIN))
        menu.add_command(label='BeginWith', command=lambda: self.onTypeWrite(SymRuleType.BEGIN_WITH))
        menu.add_command(label='EndWith', command=lambda: self.onTypeWrite(SymRuleType.END_WITH))
        menu.add_command(label='Equal', command=lambda: self.onTypeWrite(SymRuleType.EQUAL))
        menu.add_command(label='Regex', command=lambda: self.onTypeWrite(SymRuleType.REGEX))

        self.__type_menu = menu

    def onClick(self, e):
        rule = self.getRuleOfWidget(e.widget)
        en_w, type_w, txt_w, sym_w = self.__widgets[rule]
        pos = (e.x_root, e.y_root)

        #edit
        if e.widget == en_w:
            rule.enabled = not rule.enabled
            self.setRuleWidgets(rule)
            self.__rules.is_altered.set(True)
        elif e.widget == type_w:
            self.__type_menu.post(e.x_root, e.y_root)
        elif e.widget == txt_w:
            pass
        elif e.widget == sym_w:
            sym = askSym(self, pos, rule.symbol)
            if sym is not None and rule.symbol != sym:
                rule.symbol = sym
                self.setRuleWidgets(rule)
                self.__rules.is_altered.set(True)

    def onTextWrite(self, widget):
        var = widget.variable
        rule = self.getRuleOfWidget(widget)
        if rule.text != var.get():
            #print('rule change text from ', rule.text, 'to', var.get() )
            rule.text = var.get()
            self.__rules.is_altered.set(True)

    def onTypeWrite(self, t):
        #print('set type to ', str(t))
        rule = self.__focused_rule
        if rule.type != t:
            rule.type = t
            self.setRuleWidgets(rule)
            self.__rules.is_altered.set(True)

    #{{ add/dup rule

    def onRightClick(self, e):
        self.__add_menu.post(e.x_root, e.y_root)

    def initRightMenu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label='Insert a rule', command=self.onAddRule)
        menu.add_command(label='Duplicate the rule', command=lambda: self.onAddRule(dup=1))
        menu.add_separator()
        menu.add_command(label='Remove the rule', command=self.onRemoveRule)
        self.__add_menu = menu

    def onAddRule(self, dup=0):
        rule = self.__focused_rule
        idx = self.__rules.index(rule)
        row = self.getWidgetsRow(rule)
        new_rule = rule.clone() if dup == 1 else SymRule()

        #data
        self.__rules.insert(idx, new_rule)

        #view, to shift
        for i in range(len(self.__rules)-1, idx , -1):
            rule = self.__rules[i]
            self.shiftWidgetsRow(rule, 1)

        #view, to insert new
        self.genRuleWidgets(new_rule, row)
        self.setRuleWidgets(new_rule)
        self.__rules.is_altered.set(True)

    def onRemoveRule(self):
        rule = self.__focused_rule
        widgets = self.__widgets[rule]

        #data
        self.__rules.remove(rule)
        self.__widgets.pop(rule, None)

        #view
        for w in widgets:
            w.grid_forget()

        self.__focused_rule = None
        self.__rules.is_altered.set(True)

# symbol util ======================================
__sym_board = None
def askSym(parent, pos=None, init_sym=None):
    #sym_board = SymBoard(master, pos, init_sym)
    #return sym_board.sym

    global __sym_board
    if __sym_board is None:
        __sym_board = SymBoard()

    __sym_board.pos = pos
    __sym_board.sym = init_sym
    __sym_board.show(parent)
    return __sym_board.sym

# symbol rule util ======================================
__sym_rules = SymbolRules(conf.SYM_RULE_CONF)

def toSymbol(name):
    rule = __sym_rules.getMatchRule(name)
    sym = rule.symbol if rule is not None else conf.DEF_SYMBOL
    return sym

__rule_board = None
def showRule(parent, pos=None):
    global __rule_board
    if not __rule_board:
        __rule_board = SymRuleBoard(master=None, rules=__sym_rules)
    __rule_board.pos = pos
    __rule_board.show(parent)

if __name__ == '__main__':
    rules = SymbolRules('./sym_rule.conf')
    rules.save('./sym_rule.conf.out')
    print(rules.getMatchRule('-').symbol)
    print(rules.getMatchRule('2.2k').symbol)
