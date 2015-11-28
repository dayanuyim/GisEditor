#!/usr/bin/env python3

import tkinter as tk
import platform

class EditBoard(tk.Toplevel):
    @property
    def is_changed(self):
        return self._is_changed

    def __init__(self, master, elems, init_elem=None, alter_handler=None):
        super().__init__(master)

        if elems is None or len(elems) == 0:
            raise ValueError('elems is null or empty')
        if init_elem is not None and init_elem not in elems:
            raise ValueError('init_elem is not in elems')

        self._curr = None  #only set the variable by setCurrWpt()
        self._elems = elems

        #conf
        self._font = 'Arialuni 12'
        self._bold_font = 'Arialuni 12 bold'
        #self._title_name = "Name"
        #self._title_pos = "TWD67/TM2"
        #self._title_ele = "Elevation"
        #self._title_time = "Time"
        #self._title_focus = "Focus"
        self._altered_handlers = []
        self._is_changed = False


        #focus
        self._var_focus = tk.BooleanVar()
        self._var_focus.trace('w', self.onFocusChanged)

        #init_elem name
        self._var_name = tk.StringVar()
        self._var_name.trace('w', self.onNameChanged)

        if alter_handler is not None:
            addAlteredHandler(alter_handler)

        #board
        self.geometry('+0+0')
        self.protocol('WM_DELETE_WINDOW', lambda: self.onClosed(None))
        self.bind('<Escape>', self.onClosed)
        self.bind('<Shift-Delete>', lambda e: self.onDeleted(e, prompt=False))
        self.bind('<Delete>', lambda e: self.onDeleted(e, prompt=True))

        #silent update
        self.withdraw()  #hidden
        self._visible = tk.BooleanVar(value=False)
        self.update()  #update window size

    def show(self);
        #UI
        self.transient(self.master)  #remove max/min buttons
        self.focus_set()  #prevent key-press sent back to parent
        
        self.deiconify() #show
        self._visible.set(True)

        self.grab_set()   #disalbe interact of parent
        parent.wait_variable(self._visible)

    def onClosed(self, e):
        if self.master is not None:
            self.master.focus_set()
        self.grab_release()

        self.destroy()
        #self.withdraw()
        self._visible.set(False)

    #def show(self):
        #self.wait_window(self)

    def _hasPicWpt(self):
        for wpt in self._elems:
            if isinstance(wpt, PicDocument):
                return True
        return False

    def _getNextWpt(self):
        sz = len(self._elems)
        if sz == 1:
            return None
        idx = self._elems.index(self._curr)
        idx += 1 if idx != sz-1 else -1
        return self._elems[idx]

    def addAlteredHandler(self, h):
        self._altered_handlers.append(h)

    def removeAlteredHandler(self, h):
        self._altered_handlers.remove(h)

    def onAltered(self, alter):
        self.master.setAlter(alter)   #hard code fist!!!
        #for handler in self._altered_handlers:
            #handler()
        
    def onClosed(self, e=None):
        #reset or restore map
        self.master.resetMap() if self.is_changed else self.master.restore()
        self.master.focus_set()
        self.destroy()

    def onDeleted(self, e, prompt=True):
        if not self.master.onWptDeleted(self._curr, prompt):
            return

        self._is_changed = True

        next_wpt = self._getNextWpt()
        self._elems.remove(self._curr)
        if next_wpt == None:
            self.onClosed()
        else:
            self.setCurrWpt(next_wpt)

    def onNameChanged(self, *args):
        #print('change to', self._var_name.get())
        name = self._var_name.get()
        if self._curr.name != name:
            self._curr.name = name
            self._curr.sym = conf.getSymbol(name)
            self._is_changed = True
            self.showWptIcon(self._curr)

            self.onAltered('wpt')
            self.highlightWpt(self._curr)

    def onFocusChanged(self, *args):
        self.highlightWpt(self._curr)

    def onEditSymRule(self):
        SymRuleBoard(self)
    
    def highlightWpt(self, wpt):
        #focus
        if self._var_focus.get():
            self.master.resetMap(wpt)

        #highlight the current wpt
        self.master.highlightWpt(wpt)

    def unhighlightWpt(self, wpt):
        self.master.resetMap() if self.is_changed else self.master.restore()

    def showWptIcon(self, wpt):
        pass

    def setCurrWpt(self, wpt):
        pass

class ListEditBoard(EditBoard):
    def __init__(self, master, elems, wpt=None):
        super().__init__(master, elems, wpt)

        self.__widgets = {}  #wpt: widgets 
        self.__focused_wpt = None
        self.__bg_color = self.cget('bg')
        self.__bg_hl_color = 'lightblue'
        self.init()
                
        #set wpt
        if wpt is not None:
            self.setCurrWpt(wpt)

        #wait
        self.wait_window(self)

    def init(self):
        self.sf = pmw.ScrolledFrame(self, usehullsize = 1, hull_width = 300, hull_height = 600)
        self.sf.pack(fill = 'both', expand = 1)


        frame = self.sf.interior()
        font = self._font
        bfont = self._bold_font

        row = 0
        tk.Label(frame, text=self._title_name, font=bfont).grid(row=row, column=1)
        tk.Label(frame, text=self._title_pos,  font=bfont).grid(row=row, column=2)
        tk.Label(frame, text=self._title_ele,  font=bfont).grid(row=row, column=3)
        tk.Label(frame, text=self._title_time, font=bfont).grid(row=row, column=4)

        for w in self._elems:
            row += 1
            on_motion = lambda e: self.onMotion(e)

            #icon
            icon = ImageTk.PhotoImage(conf.getIcon(w.sym))
            icon_label = tk.Label(frame, image=icon, anchor='e')
            icon_label.image=icon
            icon_label.bind('<Motion>', on_motion)
            icon_label.grid(row=row, column=0, sticky='news')

            name_label = tk.Label(frame, text=w.name, font=font, anchor='w')
            name_label.bind('<Motion>', on_motion)
            name_label.grid(row=row, column=1, sticky='news')

            pos_txt = conf.getPtPosText(w, fmt='%.3f\n%.3f')
            pos_label = tk.Label(frame, text=pos_txt, font=font)
            pos_label.bind('<Motion>', on_motion)
            pos_label.grid(row=row, column=2, sticky='news')

            ele_label = tk.Label(frame, text=conf.getPtEleText(w), font=font)
            ele_label.bind('<Motion>', on_motion)
            ele_label.grid(row=row, column=3, sticky='news')

            time_label = tk.Label(frame, text=conf.getPtTimeText(w), font=font)
            time_label.bind('<Motion>', on_motion)
            time_label.grid(row=row, column=4, sticky='news')

            #save
            self.__widgets[w] = (
                    icon_label,
                    name_label,
                    pos_label,
                    ele_label,
                    time_label
            )

    def getWptOfWidget(self, w):
        for wpt, widgets in self.__widgets.items():
            if w in widgets:
                return wpt
        return None

    def onMotion(self, e):
        prev_wpt = self.__focused_wpt
        curr_wpt = self.getWptOfWidget(e.widget)

        #highligt/unhighlight
        if prev_wpt != curr_wpt:
            if prev_wpt is not None:
                self.unhighlightWpt(prev_wpt)
            if curr_wpt is not None:
                self.highlightWpt(curr_wpt)
                
        #rec
        self.__focused_wpt = curr_wpt

    #override
    def highlightWpt(self, wpt, is_focus=False):
        for w in self.__widgets[wpt]:
            w.config(bg=self.__bg_hl_color)
        super().highlightWpt(wpt)

    #override
    def unhighlightWpt(self, wpt):
        for w in self.__widgets[wpt]:
            w.config(bg=self.__bg_color)
        #super().unhighlightWpt(wpt)  #can skip, deu to followed by highlight

    #override
    def showWptIcon(self, wpt):
        pass

    #override
    def setCurrWpt(self, wpt):
        self._curr = wpt

class SingleEditBoard(EditBoard):
    def __init__(self, master, elems, wpt=None):
        super().__init__(master, elems, wpt)

        #change buttons
        self.__left_btn = tk.Button(self, text="<<", command=lambda:self.onWptSelected(-1), disabledforeground='gray')
        self.__left_btn.pack(side='left', anchor='w', expand=0, fill='y')
        self.__right_btn = tk.Button(self, text=">>", command=lambda:self.onWptSelected(1), disabledforeground='gray')
        self.__right_btn.pack(side='right', anchor='e', expand=0, fill='y')

        #info
        self.info_frame = self.getInfoFrame()
        self.info_frame.pack(side='bottom', anchor='sw', expand=0, fill='x')

        #image
        self.__img_label = None
        self.__img_sz = (img_w, img_h) = (600, 450)
        if self._hasPicWpt():
            #bd=0: let widget size align image size; set width/height to disable auto resizing
            self.__img_label = tk.Label(self, bg='black', bd=0, width=img_w, height=img_h)
            self.__img_label.pack(side='top', anchor='nw', expand=1, fill='both', padx=0, pady=0)
            self.__img_label.bind('<Configure>', self.onImageResize)

        #set wpt
        if wpt is None:
            wpt = elems[0]
        self.setCurrWpt(wpt)

        #wait
        self.wait_window(self)

    def onImageResize(self, e):
        if hasattr(self.__img_label, 'image'):
            img_w = self.__img_label.image.width()
            img_h = self.__img_label.image.height()
            #print('event: %d, %d; winfo: %d, %d; label: %d, %d; img: %d, %d' % (e.width, e.height, self.__img_label.winfo_width(), self.__img_label.winfo_height(), self.__img_label['width'], self.__img_label['height'], img_w, img_h))
            if e.width < img_w or e.height < img_h or (e.width > img_w and e.height > img_h):
                #print('need to zomm image')
                self.setWptImg(self._curr)

    def onWptSelected(self, inc):
        idx = self._elems.index(self._curr) + inc
        if idx >= 0 and idx < len(self._elems):
            self.setCurrWpt(self._elems[idx])

    def getInfoFrame(self):
        font = self._font
        bold_font = self._bold_font

        frame = tk.Frame(self)#, bg='blue')

        row = 0
        #set sym rule
        tk.Button(frame, text="Rule...", font=font, relief='groove', overrelief='ridge', command=self.onEditSymRule).grid(row=row, column=0, sticky='w')
        #wpt icon
        self.__icon_label = tk.Label(frame)
        self.__icon_label.grid(row=row, column=1, sticky='e')
        self.__icon_label.bind('<Button-1>', self.onSymClick)

        #wpt name
        name_entry = tk.Entry(frame, textvariable=self._var_name, font=font)
        name_entry.bind('<Return>', lambda e: self.onWptSelected(1))
        name_entry.grid(row=row, column=2, sticky='w')

        row += 1
        #focus
        tk.Checkbutton(frame, text=self._title_focus, variable=self._var_focus).grid(row=row, column=0, sticky='w')
        #wpt positoin
        tk.Label(frame, text=self._title_pos, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_pos = tk.StringVar()
        tk.Label(frame, font=font, textvariable=self._var_pos).grid(row=row, column=2, sticky='w')

        row +=1
        #ele
        tk.Label(frame, text=self._title_ele, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_ele = tk.StringVar()
        tk.Label(frame, font=font, textvariable=self._var_ele).grid(row=row, column=2, sticky='w')

        row +=1
        #time
        tk.Label(frame, text=self._title_time, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_time = tk.StringVar()
        tk.Label(frame, textvariable=self._var_time, font=font).grid(row=row, column=2, sticky='w')

        return frame

    def onSymClick(self, e):
        wpt = self._curr
        sym = askSym(self, pos=(e.x_root, e.y_root), init_sym=wpt.sym)

        if sym is not None and sym != wpt.sym:
            wpt.sym = sym
            self._is_changed = True
            self.showWptIcon(wpt)

            #update map
            self.onAltered('wpt')
            self.highlightWpt(wpt)

    def showWptIcon(self, wpt):
        icon = ImageTk.PhotoImage(conf.getIcon(wpt.sym))
        self.__icon_label.image = icon
        self.__icon_label.config(image=icon, text=wpt.sym, compound='right')

    def setWptImg(self, wpt):
        img_w = self.__img_label

        if img_w is None:
            return
        size = self.__img_sz if not hasattr(img_w, 'image') else (img_w.winfo_width(), img_w.winfo_height())
        img = getAspectResize(wpt.img, size) if isinstance(wpt, PicDocument) else getTextImag("(No Pic)", size)
        img = ImageTk.PhotoImage(img)
        img_w.config(image=img)
        img_w.image = img #keep a ref

    def setCurrWpt(self, wpt):
        if self._curr != wpt:
            self.unhighlightWpt(self._curr)
            self.highlightWpt(wpt)

        self._curr = wpt

        #title
        self.title(wpt.name)

        #set imgae
        self.setWptImg(wpt)

        #info
        self.showWptIcon(wpt)
        self._var_name.set(wpt.name)   #this have side effect to set symbol icon
        self._var_pos.set(conf.getPtPosText(wpt))
        self._var_ele.set(conf.getPtEleText(wpt))
        self._var_time.set(conf.getPtTimeText(wpt))

        #button state
        if self._elems is not None:
            idx = self._elems.index(wpt)
            sz = len(self._elems)
            self.__left_btn.config(state=('disabled' if idx == 0 else 'normal'))
            self.__right_btn.config(state=('disabled' if idx == sz-1 else 'normal'))

